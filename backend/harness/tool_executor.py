# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from backend.harness.runtime import HOOK_MANAGER, PERMISSION_POLICY


class ToolExecutor:
    """Agent 的统一工具行动边界，负责权限、Hook、计时和错误隔离。"""

    def __init__(self, resolver: Callable[[str, dict], Any]):
        self.resolver = resolver

    def execute(self, name: str, state: dict) -> Any:
        started = time.perf_counter()
        permission = PERMISSION_POLICY.check(name, state)
        if not permission["allowed"]:
            return {
                "ok": False,
                "tool": name,
                "error": permission["reason"],
                "error_type": "PermissionDenied",
                "permission": permission["level"],
                "retryable": permission["level"] == "confirm",
                "latency_ms": 0,
            }
        envelope = HOOK_MANAGER.emit("pre_tool", {"tool": name, "state": state})
        effective_state = envelope.get("state", state)
        try:
            data = self.resolver(name, effective_state)
            if isinstance(data, dict) and data.get("ok") is False:
                result = data
            else:
                result = {
                    "ok": True,
                    "tool": name,
                    "data": data,
                    "permission": permission["level"],
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            return HOOK_MANAGER.emit("post_tool", {"tool": name, "result": result}).get("result", result)
        except Exception as error:
            result = {
                "ok": False,
                "tool": name,
                "error": str(error),
                "error_type": type(error).__name__,
                "permission": permission["level"],
                "retryable": isinstance(error, (OSError, TimeoutError)),
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            return HOOK_MANAGER.emit("tool_error", {"tool": name, "result": result}).get("result", result)
