"""
Tests for FinClaw A2A (Agent-to-Agent) Protocol Support — v5.13.0

35+ tests covering agent card, task handler, server, skill routing, and CLI.
"""

from __future__ import annotations

import asyncio
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.a2a.agent_card import FinClawAgentCard, FINCLAW_VERSION
from src.a2a.handler import (
    A2ATaskHandler,
    Task,
    TaskState,
    route_skill,
    _extract_symbols,
)
from src.a2a.server import A2AServer, _jsonrpc_result, _jsonrpc_error


# ═══════════════════════════════════════════════════════════════════
# Agent Card Tests
# ═══════════════════════════════════════════════════════════════════


class TestAgentCard:
    def test_generate_returns_dict(self):
        card = FinClawAgentCard()
        result = card.generate()
        assert isinstance(result, dict)

    def test_card_name(self):
        card = FinClawAgentCard()
        assert card.generate()["name"] == "FinClaw"

    def test_card_version(self):
        card = FinClawAgentCard()
        assert card.generate()["version"] == FINCLAW_VERSION

    def test_card_custom_url(self):
        card = FinClawAgentCard(url="https://api.finclaw.ai")
        assert card.generate()["url"] == "https://api.finclaw.ai"

    def test_card_strips_trailing_slash(self):
        card = FinClawAgentCard(url="http://localhost:8081/")
        assert card.generate()["url"] == "http://localhost:8081"

    def test_card_capabilities(self):
        caps = FinClawAgentCard().generate()["capabilities"]
        assert caps["streaming"] is True
        assert caps["pushNotifications"] is False

    def test_card_has_six_skills(self):
        skills = FinClawAgentCard().generate()["skills"]
        assert len(skills) == 6

    def test_card_skill_ids(self):
        skills = FinClawAgentCard().generate()["skills"]
        ids = {s["id"] for s in skills}
        assert ids == {"quote", "backtest", "screen", "analyze", "sentiment", "predict"}

    def test_card_skills_have_required_fields(self):
        for skill in FinClawAgentCard().generate()["skills"]:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill

    def test_card_authentication(self):
        auth = FinClawAgentCard().generate()["authentication"]
        assert "bearer" in auth["schemes"]

    def test_card_custom_auth(self):
        card = FinClawAgentCard(auth_schemes=["apiKey"])
        assert card.generate()["authentication"]["schemes"] == ["apiKey"]

    def test_card_provider(self):
        provider = FinClawAgentCard().generate()["provider"]
        assert "organization" in provider
        assert "url" in provider

    def test_card_to_json(self):
        card = FinClawAgentCard()
        j = card.to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "FinClaw"

    def test_card_default_modes(self):
        card = FinClawAgentCard().generate()
        assert card["defaultInputModes"] == ["text"]
        assert card["defaultOutputModes"] == ["text"]


# ═══════════════════════════════════════════════════════════════════
# Skill Routing Tests
# ═══════════════════════════════════════════════════════════════════


class TestSkillRouting:
    def test_route_quote(self):
        assert route_skill("What's the price of AAPL?") == "quote"

    def test_route_quote_trading(self):
        assert route_skill("How much is TSLA trading at?") == "quote"

    def test_route_backtest(self):
        assert route_skill("Backtest RSI strategy on BTC") == "backtest"

    def test_route_screen(self):
        assert route_skill("Find oversold tech stocks") == "screen"

    def test_route_screen_filter(self):
        assert route_skill("Filter stocks with high volume") == "screen"

    def test_route_analyze(self):
        assert route_skill("Analyze AAPL technicals") == "analyze"

    def test_route_analyze_indicators(self):
        assert route_skill("What does the RSI say about NVDA?") == "analyze"

    def test_route_sentiment(self):
        assert route_skill("What's the sentiment on TSLA?") == "sentiment"

    def test_route_predict(self):
        assert route_skill("Predict where AAPL goes next week") == "predict"

    def test_route_ml(self):
        assert route_skill("ML forecast for Bitcoin") == "predict"

    def test_route_unknown(self):
        assert route_skill("Hello world") is None


class TestExtractSymbols:
    def test_single_ticker(self):
        assert "AAPL" in _extract_symbols("What's the price of AAPL?")

    def test_multiple_tickers(self):
        syms = _extract_symbols("Compare AAPL MSFT GOOG")
        assert "AAPL" in syms
        assert "MSFT" in syms
        assert "GOOG" in syms

    def test_filters_stopwords(self):
        syms = _extract_symbols("GET THE price FOR AAPL")
        assert "AAPL" in syms
        assert "GET" not in syms
        assert "THE" not in syms
        assert "FOR" not in syms

    def test_crypto(self):
        assert "BTC" in _extract_symbols("Backtest RSI on BTC")


# ═══════════════════════════════════════════════════════════════════
# Task Handler Tests
# ═══════════════════════════════════════════════════════════════════


class TestTaskHandler:
    def _make_message(self, text: str) -> dict:
        return {"message": {"parts": [{"type": "text", "text": text}]}}

    def test_task_send_creates_task(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Price of AAPL"))
        assert "id" in result
        assert result["status"]["state"] in ("completed", "failed")

    def test_task_send_with_custom_id(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send({"id": "test-123", **self._make_message("Price of AAPL")})
        assert result["id"] == "test-123"

    def test_task_send_completed(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("What's the price of AAPL?"))
        assert result["status"]["state"] == "completed"

    def test_task_send_has_artifacts(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Quote for TSLA"))
        assert len(result["artifacts"]) > 0
        assert result["artifacts"][0]["parts"][0]["type"] == "text"

    def test_task_send_no_text(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send({"message": {"parts": []}})
        assert result["status"]["state"] == "failed"

    def test_task_send_unknown_skill(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Hello world"))
        assert result["status"]["state"] == "failed"

    def test_task_get_existing(self):
        handler = A2ATaskHandler()
        sent = handler.handle_task_send({"id": "t1", **self._make_message("Price of MSFT")})
        got = handler.handle_task_get("t1")
        assert got is not None
        assert got["id"] == "t1"

    def test_task_get_nonexistent(self):
        handler = A2ATaskHandler()
        assert handler.handle_task_get("nonexistent") is None

    def test_task_cancel(self):
        handler = A2ATaskHandler()
        # Send task (completes synchronously)
        handler.handle_task_send({"id": "t2", **self._make_message("Price of GOOG")})
        result = handler.handle_task_cancel("t2")
        assert result is not None
        # Already completed, so stays completed
        assert result["status"]["state"] == "completed"

    def test_task_cancel_nonexistent(self):
        handler = A2ATaskHandler()
        assert handler.handle_task_cancel("nope") is None

    def test_task_count(self):
        handler = A2ATaskHandler()
        assert handler.task_count == 0
        handler.handle_task_send({"id": "a", **self._make_message("Price of AAPL")})
        handler.handle_task_send({"id": "b", **self._make_message("Backtest RSI on BTC")})
        assert handler.task_count == 2

    def test_backtest_routing(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Backtest momentum on AAPL"))
        assert result["status"]["state"] == "completed"
        text = result["artifacts"][0]["parts"][0]["text"]
        assert "backtest" in text.lower() or "AAPL" in text

    def test_screen_routing(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Screen for oversold stocks"))
        assert result["status"]["state"] == "completed"

    def test_analyze_routing(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Analyze NVDA technicals"))
        assert result["status"]["state"] == "completed"

    def test_sentiment_routing(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Sentiment on TSLA"))
        assert result["status"]["state"] == "completed"

    def test_predict_routing(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send(self._make_message("Predict AAPL next week"))
        assert result["status"]["state"] == "completed"

    def test_message_with_direct_text(self):
        handler = A2ATaskHandler()
        result = handler.handle_task_send({"message": {"text": "Price of AAPL"}})
        assert result["status"]["state"] == "completed"


# ═══════════════════════════════════════════════════════════════════
# Task Model Tests
# ═══════════════════════════════════════════════════════════════════


class TestTaskModel:
    def test_task_creation(self):
        t = Task("t1", {"parts": [{"type": "text", "text": "hello"}]})
        assert t.id == "t1"
        assert t.state == TaskState.SUBMITTED

    def test_task_to_dict(self):
        t = Task("t2", {"parts": []})
        d = t.to_dict()
        assert d["id"] == "t2"
        assert d["status"]["state"] == "submitted"
        assert isinstance(d["artifacts"], list)

    def test_task_state_values(self):
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.CANCELED.value == "canceled"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.WORKING.value == "working"


# ═══════════════════════════════════════════════════════════════════
# Server Tests (unit, no network)
# ═══════════════════════════════════════════════════════════════════


class TestA2AServer:
    def test_server_creates_app(self):
        server = A2AServer()
        app = server.create_app()
        assert app is not None

    def test_server_default_port(self):
        server = A2AServer()
        assert server.port == 8081

    def test_server_custom_port(self):
        server = A2AServer(port=9090)
        assert server.port == 9090

    def test_server_has_handler(self):
        server = A2AServer()
        assert isinstance(server.handler, A2ATaskHandler)

    def test_server_has_card(self):
        server = A2AServer()
        assert isinstance(server.card, FinClawAgentCard)


class TestJsonRpcHelpers:
    def test_jsonrpc_result(self):
        r = _jsonrpc_result(1, {"foo": "bar"})
        assert r["jsonrpc"] == "2.0"
        assert r["id"] == 1
        assert r["result"] == {"foo": "bar"}

    def test_jsonrpc_error(self):
        r = _jsonrpc_error(2, -32600, "Invalid Request")
        assert r["jsonrpc"] == "2.0"
        assert r["id"] == 2
        assert r["error"]["code"] == -32600
        assert r["error"]["message"] == "Invalid Request"

    def test_jsonrpc_error_with_data(self):
        r = _jsonrpc_error(3, -32000, "Custom", data={"detail": "x"})
        assert r["error"]["data"]["detail"] == "x"

    def test_jsonrpc_error_no_data(self):
        r = _jsonrpc_error(4, -32601, "Not found")
        assert "data" not in r["error"]


# ═══════════════════════════════════════════════════════════════════
# Integration Tests (aiohttp test client)
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture
def a2a_client(aiohttp_client):
    """Create test client for A2A server."""
    server = A2AServer()
    app = server.create_app()
    return aiohttp_client(app)


class TestA2AIntegration:
    @pytest.mark.asyncio
    async def test_agent_card_endpoint(self, a2a_client):
        client = await a2a_client
        resp = await client.get("/.well-known/agent.json")
        assert resp.status == 200
        data = await resp.json()
        assert data["name"] == "FinClaw"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, a2a_client):
        client = await a2a_client
        resp = await client.get("/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_jsonrpc_tasks_send(self, a2a_client):
        client = await a2a_client
        resp = await client.post("/", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "id": "integration-1",
                "message": {"parts": [{"type": "text", "text": "Price of AAPL"}]},
            },
        })
        assert resp.status == 200
        data = await resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["result"]["id"] == "integration-1"

    @pytest.mark.asyncio
    async def test_jsonrpc_tasks_get(self, a2a_client):
        client = await a2a_client
        # First send
        await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"id": "ig-1", "message": {"parts": [{"type": "text", "text": "Quote MSFT"}]}},
        })
        # Then get
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 2, "method": "tasks/get",
            "params": {"id": "ig-1"},
        })
        data = await resp.json()
        assert data["result"]["id"] == "ig-1"

    @pytest.mark.asyncio
    async def test_jsonrpc_tasks_cancel(self, a2a_client):
        client = await a2a_client
        await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"id": "ic-1", "message": {"parts": [{"type": "text", "text": "Quote GOOG"}]}},
        })
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 2, "method": "tasks/cancel",
            "params": {"id": "ic-1"},
        })
        data = await resp.json()
        assert "result" in data

    @pytest.mark.asyncio
    async def test_jsonrpc_method_not_found(self, a2a_client):
        client = await a2a_client
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "nonexistent",
        })
        data = await resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_jsonrpc_invalid_request(self, a2a_client):
        client = await a2a_client
        resp = await client.post("/", json={"not": "jsonrpc"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_jsonrpc_parse_error(self, a2a_client):
        client = await a2a_client
        resp = await client.post("/", data=b"not json", headers={"Content-Type": "application/json"})
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_task_not_found(self, a2a_client):
        client = await a2a_client
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "tasks/get",
            "params": {"id": "nonexistent"},
        })
        data = await resp.json()
        assert data["error"]["code"] == -32001

    @pytest.mark.asyncio
    async def test_auth_required(self, aiohttp_client):
        server = A2AServer(auth_token="secret123")
        app = server.create_app()
        client = await aiohttp_client(app)
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"message": {"parts": [{"type": "text", "text": "Price AAPL"}]}},
        })
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_auth_passes(self, aiohttp_client):
        server = A2AServer(auth_token="secret123")
        app = server.create_app()
        client = await aiohttp_client(app)
        resp = await client.post("/", json={
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"message": {"parts": [{"type": "text", "text": "Price AAPL"}]}},
        }, headers={"Authorization": "Bearer secret123"})
        assert resp.status == 200
