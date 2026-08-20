# © 2026 BUPT_Mint-Green
# All rights reserved.

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.agents.poetry_agent import PoetryAgent
from backend.analytics import dataset_analytics
from backend.config import FRONTEND_DIR, LIVE_ENABLED
from backend.data_loader import dataset_summary
from backend.realtime.realtime_voice_bridge import RealtimeBridge

agent: Optional[PoetryAgent] = None
live_bridge = RealtimeBridge()
running_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """在服务生命周期内复用数据索引、模型客户端和持久化连接入口。"""
    global agent
    agent = PoetryAgent()
    yield
    for task in running_tasks.values():
        task.cancel()


app = FastAPI(title="诗承智能诗词教学 Agent", version="0.5.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class AgentRequest(BaseModel):
    task: str = Field(default="chat", pattern="^(chat|generate|review|appreciate|recite|compare|expand)$")
    query: str = ""
    poem: str = ""
    form: str = "不限"
    genre_group: str = "不限"
    emotion: str = ""
    emotion_group: str = "不限"
    themes: list[str] = Field(default_factory=list)
    theme_group: str = "不限"
    dynasty: str = "不限"
    grade: str = "中学生"
    session_id: str = "default"
    request_id: int = 0
    live: bool = True
    self_rag: bool = True
    followup: bool = False
    content: str = ""
    conversation_id: str = ""
    branch_id: str = ""


class BranchRequest(BaseModel):
    conversation_id: str
    source_branch_id: str
    name: str = "新分支"
    fork_message_id: int | None = None

class RollbackRequest(BaseModel):
    conversation_id: str
    branch_id: str
    message_id: int

class MemoryRequest(BaseModel):
    session_id: str
    content: str
    kind: str = "preference"
    task: str = ""

class ClearHistoryRequest(BaseModel):
    task: str = Field(default="chat", pattern="^(chat|generate|review|appreciate|recite|compare|expand)$")

class FeedbackRequest(BaseModel):
    run_id: str
    category: str
    helpful: bool
    comment: str = ""


@app.get("/api/health")
def health() -> dict:
    live = live_bridge.status()
    live["transcription"] = {"configured": live["enabled"], "input_format": "pcm", "model": "qwen3-asr-flash-realtime"}
    return {"status": "ok", "datasets": dataset_summary(), "model": bool(agent and agent.client), "rag": agent.vector.status() if agent else {}, "live": live, "evolving": agent.store.stats() if agent else {}}


@app.get("/api/analytics")
def analytics() -> dict:
    return dataset_analytics()


@app.post("/api/agent")
async def invoke_agent(request: AgentRequest) -> dict:
    if agent is None:
        return JSONResponse({"answer": "Agent 尚未初始化"}, status_code=503)
    result = await agent.run(**request.model_dump())
    return JSONResponse(result)


@app.get("/api/workspace/{session_id}")
def workspace(session_id: str, task: str = "chat") -> dict:
    if not agent:
        return {}
    conversation_id = f"conv-{session_id}-{task}"
    branch_id = f"branch-{conversation_id}-main"
    ids = agent.store.ensure_workspace(session_id, conversation_id, branch_id)
    try:
        trace = agent.store.workspace_trace(ids["branch_id"])
    except Exception:
        trace = []
    try:
        versions = agent.store.versions(ids["conversation_id"])
    except Exception:
        versions = []
    try:
        memories = agent.store.memories(session_id)
    except Exception:
        memories = []
    history = agent.store.branch_history(ids["branch_id"], 100)
    branches = agent.store.conversation_branches(ids["conversation_id"])
    return {**ids, "trace": trace, "versions": versions, "memories": memories, "history": history, "branches": branches, "work_state": agent.store.work_state(ids["branch_id"])}

@app.post("/api/workspace/{session_id}/clear")
def clear_workspace(session_id: str, request: ClearHistoryRequest) -> dict:
    if not agent:
        return JSONResponse({"ok": False, "message": "Agent 尚未初始化"}, status_code=503)
    conversation_id = f"conv-{session_id}-{request.task}"
    agent.store.clear_conversation(conversation_id)
    workspace_ids = agent.store.ensure_workspace(session_id, conversation_id, f"branch-{conversation_id}-main")
    return {
        "ok": True,
        "workspace": {
            **workspace_ids,
            "trace": [],
            "versions": [],
            "history": [],
            "branches": agent.store.conversation_branches(conversation_id),
            "memories": agent.store.memories(session_id),
            "work_state": {},
        },
    }

@app.post("/api/branches")
def create_branch(request: BranchRequest) -> dict:
    return agent.store.fork(request.conversation_id, request.source_branch_id, request.name, request.fork_message_id) if agent else {}

@app.post("/api/branches/rollback")
def rollback_branch(request: RollbackRequest) -> dict:
    return agent.store.rollback(request.conversation_id, request.branch_id, request.message_id) if agent else {}

@app.get("/api/memories/{session_id}")
def list_memories(session_id: str) -> list[dict]:
    return agent.store.memories(session_id) if agent else []

@app.post("/api/memories")
def add_memory(request: MemoryRequest) -> dict:
    return agent.store.remember(request.session_id, request.content, request.kind, request.task) if agent else {}

@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: int) -> dict:
    if agent: agent.store.forget(memory_id)
    return {"ok": bool(agent)}

@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict:
    if agent is None:
        return {"ok": False}
    return {"ok": True, "evolution": agent.store.add_feedback(request.run_id, request.category, request.helpful, request.comment)}


@app.get("/api/evolving")
def evolving() -> dict:
    return agent.store.stats() if agent else {}


@app.websocket("/ws/agent/{session_id}")
async def websocket_agent(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connection_id = uuid.uuid4().hex
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") == "cancel":
                task = running_tasks.pop(connection_id, None)
                if task:
                    task.cancel()
                await websocket.send_json({"type": "cancelled"})
                continue
            if agent is None:
                await websocket.send_json({"type": "error", "message": "Agent 尚未初始化"})
                continue

            async def send_event(event: dict):
                if event.get("type") == "node":
                    await websocket.send_json({"type": "node", "node": event.get("node", ""), "message": event.get("message", ""), "data": event.get("data", {})})
                elif event.get("type") == "token":
                    await websocket.send_json({"type": "token", "content": event.get("content", ""), "native": bool(event.get("native", False)), "provider": event.get("provider", "")})
                elif event.get("type") == "status":
                    await websocket.send_json({"type": "status", "stage": event.get("stage", "") , "detail": event.get("detail", "")})
                else:
                    await websocket.send_json(event)

            request = {key: value for key, value in payload.items() if key != "type"}
            request["session_id"] = session_id
            request["live"] = bool(payload.get("live", True))
            request["self_rag"] = bool(payload.get("self_rag", True))
            request["followup"] = bool(payload.get("followup", False))
            request["content"] = payload.get("content", "")
            await websocket.send_json({"type": "start", "data": {"session_id": session_id, "live": request["live"], "self_rag": request["self_rag"], "followup": request["followup"]}})
            task = asyncio.create_task(agent.run(event_callback=send_event, **request))
            running_tasks[connection_id] = task
            try:
                result = await task
                answer = result.get("answer", "")
                if not answer:
                    await websocket.send_json({"type": "token", "content": "抱歉，当前未生成有效回答。", "native": False})
                elif not agent.client:
                    for start in range(0, len(answer), 6):
                        await websocket.send_json({"type": "token", "content": answer[start:start + 6], "native": False})
                        await asyncio.sleep(0.015)
                await websocket.send_json({"type": "complete", "data": {key: value for key, value in result.items() if key != "answer"}})
            except asyncio.CancelledError:
                await websocket.send_json({"type": "cancelled"})
            except Exception as error:
                await websocket.send_json({"type": "error", "message": str(error)})
            finally:
                running_tasks.pop(connection_id, None)
    except WebSocketDisconnect:
        task = running_tasks.pop(connection_id, None)
        if task:
            task.cancel()


@app.websocket("/ws/live")
async def realtime_live(websocket: WebSocket):
    await live_bridge.handle(websocket)


if FRONTEND_DIR.exists():
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
