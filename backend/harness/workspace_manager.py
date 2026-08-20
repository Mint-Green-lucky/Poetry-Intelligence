# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from backend.persistence.agent_store import AgentStore


class WorkspaceManager:
    def __init__(self, store: AgentStore):
        self.store = store

    def ensure(self, session_id: str, conversation_id: str = "", branch_id: str = "") -> dict:
        return self.store.ensure_workspace(session_id, conversation_id, branch_id)

    def snapshot(self, session_id: str, conversation_id: str = "", branch_id: str = "") -> dict:
        workspace = self.ensure(session_id, conversation_id, branch_id)
        return {
            **workspace,
            "history": self.store.branch_history(workspace["branch_id"], 100),
            "branches": self.store.conversation_branches(workspace["conversation_id"]),
            "work_state": self.store.work_state(workspace["branch_id"]), 
            "trace": self.store.workspace_trace(workspace["branch_id"]),
            "versions": self.store.versions(workspace["conversation_id"]),
            "memories": self.store.memories(session_id),
        }

