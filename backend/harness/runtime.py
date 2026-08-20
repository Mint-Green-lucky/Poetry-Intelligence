# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

PermissionLevel = Literal["allow", "confirm", "deny"]
Hook = Callable[[dict[str, Any]], dict[str, Any] | None]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    permission: PermissionLevel = "allow"
    read_only: bool = True


class ToolRegistry:
    def __init__(self, definitions: tuple[ToolDefinition, ...]):
        self._definitions = {definition.name: definition for definition in definitions}

    def get(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def catalog(self, names: list[str] | tuple[str, ...]) -> dict[str, dict[str, Any]]:
        result = {}
        for name in names:
            definition = self.get(name)
            if definition:
                result[name] = {
                    "description": definition.description,
                    "permission": definition.permission,
                    "read_only": definition.read_only,
                }
        return result


class PermissionPolicy:
    """工具执行前的服务端权限边界；客户端不能覆盖此策略。"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def check(self, name: str, state: dict) -> dict[str, Any]:
        definition = self.registry.get(name)
        if definition is None:
            return {"allowed": False, "level": "deny", "reason": "工具未注册"}
        if definition.permission == "deny":
            return {"allowed": False, "level": "deny", "reason": "工具被策略禁止"}
        if definition.permission == "confirm" and not state.get("approved_tools", {}).get(name):
            return {"allowed": False, "level": "confirm", "reason": "工具需要用户批准"}
        return {"allowed": True, "level": definition.permission, "reason": "符合当前 Agent 权限策略"}


class HookManager:
    """围绕核心循环提供扩展点，Hook 不直接改写 Agent Loop。"""

    EVENTS = ("pre_tool", "post_tool", "tool_error", "pre_response", "post_response")

    def __init__(self):
        self._hooks: dict[str, list[Hook]] = {event: [] for event in self.EVENTS}

    def register(self, event: str, hook: Hook) -> None:
        if event not in self._hooks:
            raise ValueError(f"不支持的 Hook 事件：{event}")
        self._hooks[event].append(hook)

    def emit(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        current = payload
        for hook in self._hooks.get(event, []):
            updated = hook(current)
            if updated is not None:
                current = updated
        return current


class PromptBuilder:
    """按稳定分区组装 Prompt，避免身份、上下文和工具规则散落拼接。"""

    @staticmethod
    def build(sections: list[tuple[str, Any]]) -> str:
        blocks = []
        for title, value in sections:
            if value in (None, "", [], {}):
                value = "无"
            blocks.append(f"【{title}】\n{value}")
        return "\n\n".join(blocks)


TOOL_REGISTRY = ToolRegistry((
    ToolDefinition("hybrid_retrieval", "融合关键词与语义检索，寻找相关诗词证据"),
    ToolDefinition("keyword_retrieval", "按题名、作者、诗句关键词查找候选原文"),
    ToolDefinition("reranker", "对候选证据按当前问题重新排序"),
    ToolDefinition("original_verifier", "核验篇名、作者与原文是否匹配"),
    ToolDefinition("rhythm_checker", "检查句数、字数、平仄与押韵"),
    ToolDefinition("quality_scorer", "评估语言流畅度与文笔质量"),
    ToolDefinition("sentiment_matcher", "判断文本情感并核对情感约束"),
    ToolDefinition("form_constraint", "读取所选体裁的硬性创作约束"),
    ToolDefinition("weakness_memory", "读取与当前训练相关的学习弱项"),
    ToolDefinition("version_writer", "声明校验通过后提交作品版本", read_only=False),
))
PERMISSION_POLICY = PermissionPolicy(TOOL_REGISTRY)
HOOK_MANAGER = HookManager()
PROMPT_BUILDER = PromptBuilder()
