# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from backend.persistence.agent_store import AgentStore


class MemoryManager:
    """提取并召回结构化长期记忆。

    记忆保存在 SQLite 中，按 session、task 和置信度精确召回；这里没有使用
    Embedding 或向量相似度。Chroma 仅承担诗词知识库 RAG，两类存储相互独立。
    """

    MARKERS = ("我喜欢", "我偏好", "更喜欢", "偏爱", "请保留", "保留这个", "不要使用", 
    "不要写", "避免", "以后", "下次", "我不喜欢", "不喜欢", "容易错", "总是错", "不擅长", 
    "我改成", "我改过", "改为", "我希望", "希望回答", "请记住", "记住")

    def __init__(self, store: AgentStore):
        self.store = store

    def recall(self, session_id: str, task: str) -> list[dict]:
        return self.store.memories(session_id, task)

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
            self.store.remember(session_id, sentence, kind, task, .88)

            
