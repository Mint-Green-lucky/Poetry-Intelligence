# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from backend.persistence.agent_store import AgentStore


class ContextManager:
    def __init__(self, store: AgentStore, max_history: int, max_history_chars: int = 6000):
        self.store = store
        self.max_history = max_history
        self.max_history_chars = max_history_chars

    def hydrate(self, state: dict, branch_id: str) -> dict:
        raw_history = self.store.branch_history(branch_id, self.max_history)
        history = self._fit_history_budget(raw_history)
        return {
            **state,
            "history_session": branch_id,
            "history": history,
            "followup": bool(state.get("followup") or raw_history),
            "work_state": self.store.work_state(branch_id),
            "context_meta": {
                "history_messages_loaded": len(raw_history),
                "history_messages_injected": len(history),
                "history_chars": sum(len(item.get("content", "")) for item in history),
                "compacted": len(history) < len(raw_history),
            },
        }

    def _fit_history_budget(self, history: list[dict]) -> list[dict]:
        selected: list[dict] = []
        used = 0
        for item in reversed(history):
            content = str(item.get("content", ""))
            remaining = self.max_history_chars - used
            if remaining <= 0:
                break
            if len(content) > remaining:
                content = content[-remaining:]
            selected.append({**item, "content": content})
            used += len(content)
        return list(reversed(selected))

