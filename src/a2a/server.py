"""
FinClaw A2A Server — JSON-RPC 2.0 server implementing Google's A2A protocol.

Serves:
  - POST /  → JSON-RPC 2.0 (tasks/send, tasks/get, tasks/cancel)
  - GET /.well-known/agent.json → Agent Card
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import web

from .agent_card import FinClawAgentCard
from .handler import A2ATaskHandler

logger = logging.getLogger("finclaw.a2a")


class A2AServer:
    """JSON-RPC 2.0 server for the A2A protocol."""

    def __init__(self, host: str = "localhost", port: int = 8081, auth_token: str | None = None):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.card = FinClawAgentCard(url=f"http://{host}:{port}")
        self.handler = A2ATaskHandler()
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    def create_app(self) -> web.Application:
        """Create and configure the aiohttp application."""
        app = web.Application()
        app.router.add_get("/.well-known/agent.json", self._handle_agent_card)
        app.router.add_post("/", self._handle_jsonrpc)
        # Health check
        app.router.add_get("/health", self._handle_health)
        self._app = app
        return app

    async def start(self) -> None:
        """Start the server."""
        app = self.create_app()
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logger.info(f"FinClaw A2A server listening on http://{self.host}:{self.port}")
        logger.info(f"Agent card: http://{self.host}:{self.port}/.well-known/agent.json")

    async def stop(self) -> None:
        """Stop the server."""
        if self._runner:
            await self._runner.cleanup()

    # ── HTTP handlers ─────────────────────────────────────────────

    async def _handle_agent_card(self, request: web.Request) -> web.Response:
        """GET /.well-known/agent.json"""
        return web.json_response(self.card.generate())

    async def _handle_health(self, request: web.Request) -> web.Response:
        """GET /health"""
        return web.json_response({
            "status": "ok",
            "service": "finclaw-a2a",
            "tasks": self.handler.task_count,
        })

    async def _handle_jsonrpc(self, request: web.Request) -> web.Response:
        """POST / — JSON-RPC 2.0 dispatch."""
        # Auth check
        if self.auth_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {self.auth_token}":
                return web.json_response(
                    _jsonrpc_error(None, -32000, "Unauthorized"),
                    status=401,
                )

        try:
            body = await request.json()
        except (json.JSONDecodeError, Exception):
            return web.json_response(
                _jsonrpc_error(None, -32700, "Parse error"),
                status=400,
            )

        # Validate JSON-RPC structure
        if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
            return web.json_response(
                _jsonrpc_error(body.get("id") if isinstance(body, dict) else None, -32600, "Invalid Request"),
                status=400,
            )

        req_id = body.get("id")
        method = body.get("method", "")
        params = body.get("params", {})

        # Dispatch
        if method == "tasks/send":
            result = self.handler.handle_task_send(params)
            return web.json_response(_jsonrpc_result(req_id, result))

        elif method == "tasks/get":
            task_id = params.get("id") or params.get("task_id")
            if not task_id:
                return web.json_response(_jsonrpc_error(req_id, -32602, "Missing task id"))
            result = self.handler.handle_task_get(task_id)
            if result is None:
                return web.json_response(_jsonrpc_error(req_id, -32001, "Task not found"))
            return web.json_response(_jsonrpc_result(req_id, result))

        elif method == "tasks/cancel":
            task_id = params.get("id") or params.get("task_id")
            if not task_id:
                return web.json_response(_jsonrpc_error(req_id, -32602, "Missing task id"))
            result = self.handler.handle_task_cancel(task_id)
            if result is None:
                return web.json_response(_jsonrpc_error(req_id, -32001, "Task not found"))
            return web.json_response(_jsonrpc_result(req_id, result))

        else:
            return web.json_response(
                _jsonrpc_error(req_id, -32601, f"Method not found: {method}"),
            )


# ── JSON-RPC helpers ──────────────────────────────────────────────

def _jsonrpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


async def run_server(host: str = "localhost", port: int = 8081, auth_token: str | None = None) -> None:
    """Run the A2A server (blocking)."""
    server = A2AServer(host=host, port=port, auth_token=auth_token)
    await server.start()
    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        await server.stop()
