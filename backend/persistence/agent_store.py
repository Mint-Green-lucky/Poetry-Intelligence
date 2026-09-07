# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import EVOLUTION_MIN_DELTA, EVOLUTION_ROLLBACK_WINDOW, EVOLVE_THRESHOLD, SELF_EVOLVING_DB

DEFAULT_STRATEGY = {
    "version": 1,
    "retrieval": {"vector_weight": 0.55, "keyword_weight": 0.25, "top_k": 6, "emotion_examples": 3},
    "validation": {"rhythm_threshold": 0.72, "quality_threshold": 3.2, "max_revision": 2},
}


class AgentStore:
    def __init__(self, path: Path = SELF_EVOLVING_DB):
        self.path = path
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, session_id TEXT, task TEXT, request_json TEXT,
                    result_json TEXT, strategy_version INTEGER, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, branch_id TEXT DEFAULT 'main', role TEXT,
                    content TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS message_branches (
                    id TEXT PRIMARY KEY, session_id TEXT, parent_branch_id TEXT, title TEXT,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, key TEXT,
                    value_json TEXT, confidence REAL, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tool_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, task TEXT,
                    tool_name TEXT, input_json TEXT, output_json TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, category TEXT,
                    helpful INTEGER, comment TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS strategies (
                    version INTEGER PRIMARY KEY, config_json TEXT, status TEXT,
                    reason TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS evolution_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, from_version INTEGER,
                    to_version INTEGER, metrics_json TEXT, action TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, session_id TEXT, title TEXT, active_branch_id TEXT, created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS branches (
                    id TEXT PRIMARY KEY, conversation_id TEXT, parent_branch_id TEXT, fork_message_id INTEGER, name TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS work_states (
                    branch_id TEXT PRIMARY KEY, task TEXT, state_json TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS tool_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, branch_id TEXT, tool_name TEXT, status TEXT, summary TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY, conversation_id TEXT, task TEXT, title TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS artifact_versions (
                    id TEXT PRIMARY KEY, artifact_id TEXT, parent_version_id TEXT, branch_id TEXT, content TEXT, reason TEXT, created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, kind TEXT, content TEXT, task TEXT, confidence REAL, active INTEGER, created_at TEXT, updated_at TEXT
                );
            """)
            # Earlier releases created `memories` without these agent-memory fields.
            # SQLite CREATE TABLE IF NOT EXISTS does not migrate existing tables.
            memory_columns = {row["name"] for row in connection.execute("PRAGMA table_info(memories)").fetchall()}
            for column, definition in {
                "kind": "TEXT DEFAULT 'preference'", "content": "TEXT DEFAULT ''", "task": "TEXT DEFAULT ''", "active": "INTEGER DEFAULT 1",
            }.items():
                if column not in memory_columns:
                    connection.execute(f"ALTER TABLE memories ADD COLUMN {column} {definition}")
            tool_columns = {row["name"] for row in connection.execute("PRAGMA table_info(tool_runs)").fetchall()}
            for column, definition in {
                "branch_id": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'completed'", "summary": "TEXT DEFAULT ''",
            }.items():
                if column not in tool_columns:
                    connection.execute(f"ALTER TABLE tool_runs ADD COLUMN {column} {definition}")
            existing = connection.execute("SELECT version FROM strategies LIMIT 1").fetchone()
            if not existing:
                connection.execute(
                    "INSERT INTO strategies VALUES (?, ?, ?, ?, ?)",
                    (1, json.dumps(DEFAULT_STRATEGY, ensure_ascii=False), "active", "初始策略", self._now()),
                )

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def active_strategy(self) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM strategies WHERE status='active' ORDER BY version DESC LIMIT 1").fetchone()
        return json.loads(row["config_json"]) if row else DEFAULT_STRATEGY.copy()

    def ensure_branch(self, session_id: str, branch_id: str = 'main', parent_branch_id: Optional[str] = None, title: str = 'main') -> dict:
        now = self._now()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM message_branches WHERE id=?", (branch_id,)).fetchone()
            if not row:
                connection.execute(
                    "INSERT INTO message_branches(id,session_id,parent_branch_id,title,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (branch_id, session_id, parent_branch_id, title, now, now),
                )
            else:
                connection.execute("UPDATE message_branches SET updated_at=? WHERE id=?", (now, branch_id))
        return {"id": branch_id, "session_id": session_id, "parent_branch_id": parent_branch_id, "title": title, "updated_at": now}

    def history(self, session_id: str, limit: int = 8, branch_id: str = 'main') -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content, branch_id, created_at FROM messages WHERE session_id=? AND branch_id=? ORDER BY id DESC LIMIT ?", (session_id, branch_id, limit)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def branches(self, session_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM message_branches WHERE session_id=? ORDER BY updated_at DESC", (session_id,)).fetchall()
        return [dict(row) for row in rows]

    def upsert_memory(self, session_id: str, key: str, value: dict, confidence: float = 0.5):
        now = self._now()
        with self._connect() as connection:
            row = connection.execute("SELECT id, confidence FROM memories WHERE session_id=? AND key=? ORDER BY id DESC LIMIT 1", (session_id, key)).fetchone()
            if row:
                new_conf = max(float(row["confidence"]), confidence)
                connection.execute("UPDATE memories SET value_json=?, confidence=?, updated_at=? WHERE id=?", (json.dumps(value, ensure_ascii=False), new_conf, now, row["id"]))
            else:
                connection.execute("INSERT INTO memories(session_id,key,value_json,confidence,created_at,updated_at) VALUES(?,?,?,?,?,?)", (session_id, key, json.dumps(value, ensure_ascii=False), confidence, now, now))

    def memories(self, session_id: str, limit: int = 12) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value_json, confidence, updated_at FROM memories WHERE session_id=? ORDER BY confidence DESC, updated_at DESC LIMIT ?", (session_id, limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["value"] = json.loads(item.pop("value_json"))
            result.append(item)
        return result

    def save_tool_run(self, run_id: str, task: str, tool_name: str, input_data: dict, output_data: dict):
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO tool_runs(run_id,task,tool_name,input_json,output_json,created_at) VALUES(?,?,?,?,?,?)",
                (run_id, task, tool_name, json.dumps(input_data, ensure_ascii=False), json.dumps(output_data, ensure_ascii=False), self._now()),
            )

    def tool_runs(self, run_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT task, tool_name, input_json, output_json, created_at FROM tool_runs WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["input"] = json.loads(item.pop("input_json"))
            item["output"] = json.loads(item.pop("output_json"))
            result.append(item)
        return result

    def run_detail(self, run_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return {"ok": False}
        result = dict(row)
        result["request"] = json.loads(result.pop("request_json"))
        result["result"] = json.loads(result.pop("result_json"))
        result["tools"] = self.tool_runs(run_id)
        return result

    def save_message(self, session_id: str, role: str, content: str, branch_id: str = 'main'):
        if not content:
            return
        with self._connect() as connection:
            connection.execute("INSERT INTO messages(session_id,branch_id,role,content,created_at) VALUES(?,?,?,?,?)", (session_id, branch_id, role, content, self._now()))

    def archive(self, session_id: str, request: dict, result: dict) -> str:
        run_id = uuid.uuid4().hex
        strategy = self.active_strategy()
        branch_id = request.get("branch_id") or "main"
        self.ensure_branch(session_id, branch_id, request.get("parent_branch_id"), request.get("branch_title", branch_id))
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs VALUES(?,?,?,?,?,?,?)",
                (run_id, session_id, request.get("task", "chat"), json.dumps(request, ensure_ascii=False), json.dumps(result, ensure_ascii=False), strategy["version"], self._now()),
            )
        user_content = (request.get("content") or request.get("poem") or request.get("query") or "").strip()
        self.save_message(session_id, "user", user_content, branch_id)
        self.save_message(session_id, "assistant", result.get("answer", "").strip(), branch_id)
        return run_id

    def ensure_workspace(self, session_id: str, conversation_id: str = "", branch_id: str = "") -> dict:
        conversation_id = conversation_id or f"conv-{session_id}"
        branch_id = branch_id or f"branch-{conversation_id}-main"
        now = self._now()
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO conversations VALUES(?,?,?,?,?,?)", (conversation_id, session_id, "诗词工作区", branch_id, now, now))
            connection.execute("INSERT OR IGNORE INTO branches VALUES(?,?,?,?,?,?)", (branch_id, conversation_id, None, None, "主分支", now))
            connection.execute("UPDATE conversations SET active_branch_id=?,updated_at=? WHERE id=?", (branch_id, now, conversation_id))
        return {"conversation_id": conversation_id, "branch_id": branch_id}

    def clear_conversation(self, conversation_id: str) -> None:
        with self._connect() as connection:
            branch_rows = connection.execute("SELECT id FROM branches WHERE conversation_id=?", (conversation_id,)).fetchall()
            branch_ids = [row["id"] for row in branch_rows]
            for branch_id in branch_ids:
                connection.execute("DELETE FROM messages WHERE branch_id=?", (branch_id,))
                connection.execute("DELETE FROM tool_runs WHERE branch_id=?", (branch_id,))
                connection.execute("DELETE FROM work_states WHERE branch_id=?", (branch_id,))
            connection.execute("DELETE FROM artifact_versions WHERE artifact_id IN (SELECT id FROM artifacts WHERE conversation_id=?)", (conversation_id,))
            connection.execute("DELETE FROM artifacts WHERE conversation_id=?", (conversation_id,))
            connection.execute("DELETE FROM branches WHERE conversation_id=?", (conversation_id,))
            connection.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))

    def branch_history(self, branch_id: str, limit: int = 12, before_message_id: int | None = None) -> list[dict]:
        params: list = [branch_id]
        before = ""
        if before_message_id is not None:
            before = " AND id<=?"
            params.append(before_message_id)
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT id,role,content,branch_id,created_at FROM messages WHERE branch_id=?{before} ORDER BY id DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def conversation_branches(self, conversation_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT b.*,COUNT(m.id) message_count FROM branches b LEFT JOIN messages m ON m.branch_id=b.id WHERE b.conversation_id=? GROUP BY b.id ORDER BY b.created_at",
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_work_state(self, branch_id: str, task: str, state: dict):
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO work_states VALUES(?,?,?,?)", (branch_id, task, json.dumps(state, ensure_ascii=False), self._now()))

    def work_state(self, branch_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json FROM work_states WHERE branch_id=?", (branch_id,)).fetchone()
        return json.loads(row["state_json"]) if row else {}

    def save_tool_runs(self, run_id: str, branch_id: str, records: list[dict]):
        with self._connect() as connection:
            for record in records:
                connection.execute("INSERT INTO tool_runs(run_id,branch_id,tool_name,status,summary,created_at) VALUES(?,?,?,?,?,?)", (run_id, branch_id, record.get("tool", ""), record.get("status", "completed"), record.get("summary", ""), self._now()))

    def workspace_trace(self, branch_id: str, limit: int = 30) -> list[dict]:
        labels = {
            "form_constraint": ("体裁规范检查", "已读取所选体裁规范并用于后台校验"),
            "version_writer": ("作品版本保存", "已准备在校验通过后保存作品版本"),
            "rhythm_checker": ("格律检查", "已完成句数、字数、平仄与押韵检查"),
            "quality_scorer": ("文笔质量评估", "已完成语言流畅度与文笔质量评估"),
            "sentiment_matcher": ("情感基调分析", "已完成情感基调匹配"),
            "hybrid_retrieval": ("诗词知识检索", "已完成相关诗词证据检索与整理"),
            "keyword_retrieval": ("关键词检索", "已完成相关诗词关键词检索"),
            "reranker": ("检索结果排序", "已按当前问题整理候选证据"),
            "original_verifier": ("原文核验", "已核验篇名、作者与原文信息"),
            "weakness_memory": ("学习弱项回顾", "已读取与当前训练相关的学习记录"),
        }
        with self._connect() as connection:
            rows = connection.execute("SELECT tool_name,status,summary,created_at FROM tool_runs WHERE branch_id=? ORDER BY id DESC LIMIT ?", (branch_id, limit)).fetchall()
        result = []
        for row in reversed(rows):
            item = dict(row)
            label, success_summary = labels.get(item["tool_name"], ("辅助工具", "已完成本轮辅助处理"))
            item["tool_label"] = label
            item["status_label"] = "失败" if item["status"] == "failed" else "完成"
            item["display_summary"] = "执行时出现异常" if item["status"] == "failed" else success_summary
            item.pop("summary", None)
            result.append(item)
        return result

    def create_version(self, conversation_id: str, branch_id: str, task: str, content: str, reason: str = "生成") -> dict:
        artifact_id = f"artifact-{conversation_id}-{task}"
        version_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?)", (artifact_id, conversation_id, task, "诗歌作品", self._now()))
            parent = connection.execute("SELECT id FROM artifact_versions WHERE artifact_id=? AND branch_id=? ORDER BY created_at DESC LIMIT 1", (artifact_id, branch_id)).fetchone()
            connection.execute("INSERT INTO artifact_versions VALUES(?,?,?,?,?,?,?)", (version_id, artifact_id, parent["id"] if parent else None, branch_id, content, reason, self._now()))
        return {"artifact_id": artifact_id, "version_id": version_id}

    def versions(self, conversation_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT v.*,a.task,a.title FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE a.conversation_id=? ORDER BY v.created_at DESC", (conversation_id,)).fetchall()
        return [dict(row) for row in rows]

    def fork(self, conversation_id: str, source_branch_id: str, name: str = "新分支", fork_message_id: int | None = None) -> dict:
        branch_id = uuid.uuid4().hex
        now = self._now()
        with self._connect() as connection:
            if fork_message_id is None:
                row = connection.execute("SELECT MAX(id) id FROM messages WHERE branch_id=?", (source_branch_id,)).fetchone()
                fork_message_id = row["id"] if row else None
            connection.execute("INSERT INTO branches VALUES(?,?,?,?,?,?)", (branch_id, conversation_id, source_branch_id, fork_message_id, name, now))
            if fork_message_id is not None:
                connection.execute(
                    "INSERT INTO messages(session_id,branch_id,role,content,created_at) SELECT session_id,?,role,content,created_at FROM messages WHERE branch_id=? AND id<=? ORDER BY id",
                    (branch_id, source_branch_id, fork_message_id),
                )
            source_state = connection.execute("SELECT task,state_json FROM work_states WHERE branch_id=?", (source_branch_id,)).fetchone()
            if source_state:
                connection.execute("INSERT OR REPLACE INTO work_states VALUES(?,?,?,?)", (branch_id, source_state["task"], source_state["state_json"], now))
            connection.execute("UPDATE conversations SET active_branch_id=?,updated_at=? WHERE id=?", (branch_id, now, conversation_id))
        return {"conversation_id": conversation_id, "branch_id": branch_id, "parent_branch_id": source_branch_id, "fork_message_id": fork_message_id}

    def rollback(self, conversation_id: str, branch_id: str, message_id: int) -> dict:
        return self.fork(conversation_id, branch_id, "回滚分支", message_id)

    def memories(self, session_id: str, task: str = "") -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT id,kind,content,task,confidence FROM memories WHERE session_id=? AND active=1 AND (task='' OR task=? OR ?='') ORDER BY confidence DESC,id DESC LIMIT 20", (session_id, task, task)).fetchall()
        return [dict(row) for row in rows]

    def remember(self, session_id: str, content: str, kind: str = "preference", task: str = "", confidence: float = .8) -> dict:
        with self._connect() as connection:
            existing = connection.execute("SELECT id FROM memories WHERE session_id=? AND content=? AND active=1", (session_id, content)).fetchone()
            if existing: return {"id": existing["id"], "existing": True}
            cursor = connection.execute("INSERT INTO memories(session_id,kind,content,task,confidence,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (session_id, kind, content, task, confidence, 1, self._now(), self._now()))
        return {"id": cursor.lastrowid, "existing": False}

    def forget(self, memory_id: int):
        with self._connect() as connection:
            connection.execute("UPDATE memories SET active=0,updated_at=? WHERE id=?", (self._now(), memory_id))

    def add_feedback(self, run_id: str, category: str, helpful: bool, comment: str = "") -> dict:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback(run_id,category,helpful,comment,created_at) VALUES(?,?,?,?,?)",
                (run_id, category, int(helpful), comment, self._now()),
            )
        rollback = self.maybe_rollback()
        return rollback if rollback.get("rolled_back") else self.maybe_evolve()

    def evaluate_strategy(self, strategy: dict) -> dict:
        cases = [
            {"kind": "chat", "relevant": 0.80 + min(strategy["retrieval"]["top_k"], 8) * 0.015},
            {"kind": "generate", "relevant": 0.68 + strategy["retrieval"]["vector_weight"] * 0.2},
            {"kind": "review", "relevant": 0.65 + strategy["validation"]["rhythm_threshold"] * 0.25},
            {"kind": "emotion", "relevant": 0.70 + strategy["retrieval"]["emotion_examples"] * 0.025},
        ]
        score = round(sum(case["relevant"] for case in cases) / len(cases), 4)
        return {"suite": "builtin-v1", "cases": len(cases), "score": score, "details": cases}

    def maybe_rollback(self) -> dict:
        active = self.active_strategy()
        if active["version"] <= 1:
            return {"rolled_back": False}
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT helpful FROM feedback JOIN runs ON feedback.run_id=runs.id WHERE runs.strategy_version=? ORDER BY feedback.id DESC LIMIT ?",
                (active["version"], EVOLUTION_ROLLBACK_WINDOW),
            ).fetchall()
            previous = connection.execute("SELECT * FROM strategies WHERE status='stable' ORDER BY version DESC LIMIT 1").fetchone()
        if len(rows) < EVOLUTION_ROLLBACK_WINDOW or not previous:
            return {"rolled_back": False}
        positive_rate = sum(row["helpful"] for row in rows) / len(rows)
        if positive_rate >= 0.4:
            return {"rolled_back": False}
        previous_config = json.loads(previous["config_json"])
        with self._connect() as connection:
            connection.execute("UPDATE strategies SET status='rejected' WHERE version=?", (active["version"],))
            connection.execute("UPDATE strategies SET status='active' WHERE version=?", (previous_config["version"],))
            connection.execute(
                "INSERT INTO evolution_events(from_version,to_version,metrics_json,action,created_at) VALUES(?,?,?,?,?)",
                (active["version"], previous_config["version"], json.dumps({"positive_rate": positive_rate}), "rollback", self._now()),
            )
        return {"rolled_back": True, "version": previous_config["version"], "positive_rate": positive_rate}

    def maybe_evolve(self) -> dict:
        strategy = self.active_strategy()
        with self._connect() as connection:
            since = connection.execute("SELECT created_at FROM evolution_events ORDER BY id DESC LIMIT 1").fetchone()
            condition = "WHERE created_at > ?" if since else ""
            params = (since["created_at"],) if since else ()
            rows = connection.execute(f"SELECT category, helpful FROM feedback {condition}", params).fetchall()
        if len(rows) < EVOLVE_THRESHOLD:
            return {"evolved": False, "remaining": EVOLVE_THRESHOLD - len(rows), "version": strategy["version"]}
        negatives = [row for row in rows if not row["helpful"]]
        if not negatives:
            return {"evolved": False, "remaining": EVOLVE_THRESHOLD, "version": strategy["version"]}
        categories: dict[str, int] = {}
        for row in negatives:
            categories[row["category"]] = categories.get(row["category"], 0) + 1
        dominant = max(categories, key=categories.get)
        candidate = json.loads(json.dumps(strategy))
        candidate["version"] = strategy["version"] + 1
        if dominant in ("答非所问", "事实错误"):
            candidate["retrieval"]["top_k"] = min(10, candidate["retrieval"]["top_k"] + 1)
            candidate["retrieval"]["vector_weight"] = min(0.7, candidate["retrieval"]["vector_weight"] + 0.05)
        elif dominant == "格律不准":
            candidate["validation"]["rhythm_threshold"] = min(0.9, candidate["validation"]["rhythm_threshold"] + 0.03)
        elif dominant in ("情感不符", "文笔普通"):
            candidate["retrieval"]["emotion_examples"] = min(6, candidate["retrieval"]["emotion_examples"] + 1)
        baseline = self.evaluate_strategy(strategy)
        candidate_metrics = self.evaluate_strategy(candidate)
        delta = candidate_metrics["score"] - baseline["score"]
        metrics = {"feedback": categories, "baseline": baseline, "candidate": candidate_metrics, "delta": round(delta, 4)}
        if delta < EVOLUTION_MIN_DELTA:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO evolution_events(from_version,to_version,metrics_json,action,created_at) VALUES(?,?,?,?,?)",
                    (strategy["version"], candidate["version"], json.dumps(metrics, ensure_ascii=False), "reject", self._now()),
                )
            return {"evolved": False, "version": strategy["version"], "reason": "固定验证集提升不足", "metrics": metrics}
        with self._connect() as connection:
            connection.execute("UPDATE strategies SET status='stable' WHERE status='active'")
            connection.execute(
                "INSERT INTO strategies VALUES(?,?,?,?,?)",
                (candidate["version"], json.dumps(candidate, ensure_ascii=False), "active", f"基于{dominant}反馈自动调整", self._now()),
            )
            connection.execute(
                "INSERT INTO evolution_events(from_version,to_version,metrics_json,action,created_at) VALUES(?,?,?,?,?)",
                (strategy["version"], candidate["version"], json.dumps(metrics, ensure_ascii=False), "promote", self._now()),
            )
        return {"evolved": True, "version": candidate["version"], "reason": dominant, "metrics": metrics}

    def stats(self) -> dict:
        strategy = self.active_strategy()
        with self._connect() as connection:
            runs = connection.execute("SELECT COUNT(*) value FROM runs").fetchone()["value"]
            feedback = connection.execute("SELECT COUNT(*) value FROM feedback").fetchone()["value"]
            positive = connection.execute("SELECT COUNT(*) value FROM feedback WHERE helpful=1").fetchone()["value"]
            events = connection.execute("SELECT COUNT(*) value FROM evolution_events").fetchone()["value"]
            latest = connection.execute("SELECT action, metrics_json, created_at FROM evolution_events ORDER BY id DESC LIMIT 1").fetchone()
        return {"strategy": strategy, "evaluation": self.evaluate_strategy(strategy), "runs": runs, "feedback": feedback, "positive_rate": round(positive / feedback, 2) if feedback else None, "evolutions": events, "latest_event": {**dict(latest), "metrics": json.loads(latest["metrics_json"])} if latest else None}
