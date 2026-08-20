# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph 节点之间传递的工作记忆。

    该状态不是长期记忆本身：``history`` 和 ``memory`` 由持久化层按当前
    session/branch 装载，节点产生的计划、观察、动作和结果则只在本次 Run 中流转。
    ``total=False`` 允许不同专业 Agent 仅写入自己需要的字段。
    """

    task: str
    query: str
    original_query: str
    content: str
    poem: str
    form: str
    emotion: str
    themes: list[str]
    dynasty: str
    grade: str
    session_id: str
    conversation_id: str
    branch_id: str
    history_session: str
    history: list[dict]
    followup: bool
    memory: list[dict]
    work_state: dict
    workspace: dict
    plan: dict
    task_steps: list[dict]
    observations: list[dict]
    actions: list[dict]
    references: list[dict]
    rhythm: dict
    sentiment: dict
    quality: dict
    answer: str
    agent_name: str
    result_schema: tuple[str, ...]
    tool_runs: list[dict]
    tool_context: dict
    lifecycle: list[dict]
    dataset_usage: list[dict]
    retrieval_score: float
    retrieval_attempts: int
    revision_count: int
    validation: dict
    trace: list[dict]
