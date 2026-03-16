"""
MCP Protocol Handler — JSON-RPC 2.0 over stdio for the Model Context Protocol.
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

from src.mcp.server import FinClawMCPServer


class MCPProtocol:
    """Read JSON-RPC requests from stdin, dispatch to FinClawMCPServer, write responses to stdout."""

    def __init__(self, server: FinClawMCPServer | None = None, *, input_stream: TextIO | None = None, output_stream: TextIO | None = None):
        self.server = server or FinClawMCPServer()
        self._in = input_stream or sys.stdin
        self._out = output_stream or sys.stdout
        self._initialized = False

    def run(self) -> None:
        """Main loop: read stdin line-by-line, handle each JSON-RPC message."""
        for line in self._in:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                self._write_error(None, -32700, f"Parse error: {e}")
                continue
            response = self.handle_request(request)
            if response is not None:
                self._write(response)

    def handle_request(self, request: dict) -> dict | None:
        """Dispatch a single JSON-RPC request. Returns response dict or None for notifications."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # Notifications (no id) — no response needed, but we still process them
        is_notification = req_id is None and "id" not in request

        try:
            result = self._dispatch(method, params)
        except Exception as e:
            if is_notification:
                return None
            return self._make_error(req_id, -32603, f"Internal error: {e}")

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _dispatch(self, method: str, params: dict) -> dict:
        if method == "initialize":
            self._initialized = True
            return self.server.handle_initialize(params)
        elif method == "notifications/initialized":
            return {}
        elif method == "tools/list":
            return self.server.handle_tools_list()
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            return self.server.handle_tools_call(name, arguments)
        elif method == "ping":
            return {}
        else:
            raise ValueError(f"Method not found: {method}")

    def _write(self, response: dict) -> None:
        self._out.write(json.dumps(response, default=str, ensure_ascii=False) + "\n")
        self._out.flush()

    def _write_error(self, req_id, code: int, message: str) -> None:
        self._write(self._make_error(req_id, code, message))

    @staticmethod
    def _make_error(req_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
