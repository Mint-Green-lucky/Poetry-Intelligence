# © 2026 BUPT_Mint-Green
# All rights reserved.

"""极简 MCP（Model Context Protocol）stdio 客户端。

只实现 Agent 真正需要的三步：初始化握手、列出工具、调用工具。协议参照
MCP 2024-11-05 规范——JSON-RPC 2.0、换行分隔文本、通过子进程的
stdin/stdout 通信，不引入官方 `mcp` SDK 依赖，保持与项目里
chromadb/sentence-transformers 一致的"惰性可选、失败即降级"风格。

默认关闭（config.MCP_ENABLED=False 或未配置任何 Server）：此时
MCPToolManager.connections 为空，不会向 TOOL_REGISTRY 新增任何工具，
现有 7 个 Specialist Agent 的工具白名单与调用行为完全不受影响。
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


def load_server_configs(path: Path) -> list[MCPServerConfig]:
    """从 mcp_servers.json 读取 Server 列表；文件不存在或格式错误时返回空列表。"""
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    servers = []
    for item in raw.get("servers", []):
        command = item.get("command")
        if not command:
            continue
        servers.append(MCPServerConfig(
            name=item.get("name", "server"), command=command,
            args=item.get("args", []), env=item.get("env"),
        ))
    return servers


class MCPServerConnection:
    """管理单个 MCP Server 子进程的生命周期与 JSON-RPC 收发。"""

    def __init__(self, config: MCPServerConfig, timeout: float = 15.0):
        self.config = config
        self.timeout = timeout
        self.available = False
        self.reason = "未连接"
        self.tools: list[dict[str, Any]] = []
        self._process: subprocess.Popen | None = None
        self._responses: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._next_id = 1

    def connect(self) -> None:
        try:
            env = {**os.environ, **(self.config.env or {})}
            self._process = subprocess.Popen(
                [self.config.command, *self.config.args],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1, env=env,
            )
            threading.Thread(target=self._read_loop, daemon=True).start()
            self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "poetry-agent", "version": "1.0"},
            })
            self._notify("notifications/initialized", {})
            result = self._request("tools/list", {})
            self.tools = (result or {}).get("tools", [])
            self.available = True
            self.reason = "ready"
        except Exception as error:
            self.available = False
            self.reason = str(error)

    def _read_loop(self) -> None:
        if not (self._process and self._process.stdout):
            return
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "id" in message:
                with self._lock:
                    self._responses[message["id"]] = message

    def _send(self, payload: dict[str, Any]) -> None:
        if not (self._process and self._process.stdin):
            raise RuntimeError("MCP Server 进程未就绪")
        self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._process.stdin.flush()

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            request_id = self._next_id
            self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            with self._lock:
                message = self._responses.pop(request_id, None)
            if message is not None:
                if "error" in message:
                    raise RuntimeError(message["error"].get("message", "MCP 调用失败"))
                return message.get("result", {})
            time.sleep(0.02)
        raise TimeoutError(f"MCP 请求超时：{method}")

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": tool_name, "arguments": arguments})
        content = result.get("content", [])
        texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
        return {"is_error": bool(result.get("isError")), "text": "\n".join(texts) or json.dumps(result, ensure_ascii=False)}

    def close(self) -> None:
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                pass


class MCPToolManager:
    """按需连接配置好的 MCP Server，把发现的工具动态登记进 harness 工具目录。"""

    def __init__(self, registry, servers: list[MCPServerConfig], enabled: bool, timeout: float = 15.0):
        self.registry = registry
        self.connections: dict[str, MCPServerConnection] = {}
        self.enabled = bool(enabled and servers)
        if not self.enabled:
            return
        for server in servers:
            connection = MCPServerConnection(server, timeout=timeout)
            connection.connect()
            if connection.available:
                self.connections[server.name] = connection
                self._register_tools(server.name, connection)

    def _register_tools(self, server_name: str, connection: MCPServerConnection) -> None:
        from backend.harness.runtime import ToolDefinition
        for tool in connection.tools:
            tool_name = tool.get("name", "")
            if not tool_name:
                continue
            qualified = f"mcp__{server_name}__{tool_name}"
            self.registry.register(ToolDefinition(
                qualified, tool.get("description") or f"MCP 工具：{tool_name}",
                permission="confirm", read_only=False,
            ))

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "servers": {
                name: {"available": conn.available, "reason": conn.reason, "tools": [t.get("name") for t in conn.tools]}
                for name, conn in self.connections.items()
            },
        }

    def call(self, qualified_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        parts = qualified_name.split("__", 2)
        if len(parts) != 3:
            return {"is_error": True, "text": f"非法的 MCP 工具名：{qualified_name}"}
        _, server_name, tool_name = parts
        connection = self.connections.get(server_name)
        if connection is None or not connection.available:
            return {"is_error": True, "text": f"MCP Server {server_name} 不可用"}
        try:
            return connection.call_tool(tool_name, arguments)
        except Exception as error:
            return {"is_error": True, "text": str(error)}

    def close(self) -> None:
        for connection in self.connections.values():
            connection.close()
