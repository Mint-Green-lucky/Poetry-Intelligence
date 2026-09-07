# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from typing import Optional

from backend.persistence.agent_store import AgentStore
from backend.retrieval.vector_store import VectorPoetryStore

MEMORY_COLLECTION = "memory"


class MemoryManager:
    """提取并召回结构化长期记忆。

    精确召回（recall）仍然完全走 SQLite，按 session、task 和置信度排序，
    行为与之前一致。`vector_store` 是可选的增量能力：传入后，每条新记忆
    会额外写入 Chroma 的独立 memory 集合（与诗词知识库集合互不相干），
    使得 semantic_recall() 可以在“当前任务没有精确匹配、但历史记忆语义
    相关”时把它们捞出来，作为 recall() 结果的补充而非替代。
    """

    MARKERS = ("我喜欢", "我偏好", "更喜欢", "偏爱", "请保留", "保留这个", "不要使用",
    "不要写", "避免", "以后", "下次", "我不喜欢", "不喜欢", "容易错", "总是错", "不擅长",
    "我改成", "我改过", "改为", "我希望", "希望回答", "请记住", "记住")

    def __init__(self, store: AgentStore, vector_store: Optional[VectorPoetryStore] = None):
        self.store = store
        self.vector_store = vector_store

    def recall(self, session_id: str, task: str) -> list[dict]:
        return self.store.memories(session_id, task)

    def semantic_recall(self, session_id: str, query: str, top_k: int = 5) -> list[dict]:
        """按语义相似度召回同一 session 下的历史记忆，跨 task 也能命中。"""
        if self.vector_store is None or not query or not query.strip():
            return []
        results = self.vector_store.search(MEMORY_COLLECTION, query, top_k, {"session_id": session_id})
        return [
            {
                "id": item.get("memory_id"),
                "kind": item.get("kind", "preference"),
                "content": item.get("content", ""),
                "task": item.get("task", ""),
                "confidence": item.get("confidence", 0),
                "score": item.get("vector_score", 0),
            }
            for item in results
        ]

    @staticmethod
    def merge_recall(primary: list[dict], extra: list[dict], extra_limit: int = 5) -> list[dict]:
        """把语义召回追加在精确召回之后；没有语义结果时与旧行为完全一致。"""
        seen = {item.get("content") for item in primary}
        merged = list(primary)
        added = 0
        for item in extra:
            if added >= extra_limit:
                break
            content = item.get("content")
            if content and content not in seen:
                seen.add(content)
                merged.append(item)
                added += 1
        return merged

    def extract(self, session_id: str, task: str, text: str) -> None:
        for sentence in text.replace("！", "。").replace("？", "。").replace("；", "。").split("。"):
            sentence = sentence.strip()
            if not sentence or not any(marker in sentence for marker in self.MARKERS):
                continue
            if any(marker in sentence for marker in ("容易错", "总是错", "不擅长")):
                kind = "weakness"
            elif any(marker in sentence for marker in ("我改成", "我改过", "改为", "请保留", "保留这个")):
                kind = "revision"
            else:
                kind = "preference"
            record = self.store.remember(session_id, sentence, kind, task, .88)
            if self.vector_store is not None and record.get("id"):
                self.vector_store.upsert(
                    MEMORY_COLLECTION, f"memory-{record['id']}", sentence,
                    {"session_id": session_id, "kind": kind, "task": task, "confidence": .88, "memory_id": record["id"]},
                )

            
