# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, StateGraph

from backend.agents.state import AgentState


def build_poetry_workflow(parse_node: Callable, handlers: dict[str, Callable]):
    """构建当前生产工作流：标准化输入后按显式 task 路由至唯一专业 Agent。

    规划、工具观察和结构修订目前封装在 SpecialistAgent 内；LangGraph 在这里负责
    类型化状态传递、条件路由与统一退出，避免重复意图识别导致业务身份漂移。
    """
    graph = StateGraph(AgentState)
    graph.add_node("parse", parse_node)
    for task, handler in handlers.items():
        graph.add_node(task, handler)
    graph.set_entry_point("parse")
    graph.add_conditional_edges(
        "parse",
        lambda state: state.get("task", "chat"),
        {task: task for task in handlers},
    )
    for task in handlers:
        graph.add_edge(task, END)
    return graph.compile()

