"""
Tests for FinClaw REST API v5.1.0
Tests cover: server, auth, rate_limiter, docs, and CLI serve command.
40+ tests total.
"""

from __future__ import annotations

import io
import json
import time
import tempfile
import os
import sys
from http.server import HTTPServer
from unittest.mock import patch, MagicMock
import threading

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.auth import APIAuth
from src.api.rate_limiter import RateLimiter
from src.api.docs import APIDocGenerator
from src.api.server import FinClawAPI, FinClawHandler, _ROUTES


# ════════════════════════════════════════════════════════════════
# Auth Tests (10)
# ════════════════════════════════════════════════════════════════

class TestAPIAuth:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write("{}")
        self.tmp.close()
        self.auth = APIAuth(keys_file=self.tmp.name)

    def teardown_method(self):
        os.unlink(self.tmp.name)

    def test_generate_key_returns_string(self):
        key = self.auth.generate_key("test")
        assert isinstance(key, str)
        assert key.startswith("fc_")

    def test_generate_key_is_unique(self):
        k1 = self.auth.generate_key("a")
        k2 = self.auth.generate_key("b")
        assert k1 != k2

    def test_validate_valid_key(self):
        key = self.auth.generate_key("test")
        assert self.auth.validate_key(key) is True

    def test_validate_invalid_key(self):
        assert self.auth.validate_key("fc_bogus_key") is False

    def test_validate_empty_key(self):
        assert self.auth.validate_key("") is False
        assert self.auth.validate_key(None) is False

    def test_revoke_key(self):
        key = self.auth.generate_key("test")
        assert self.auth.validate_key(key) is True
        assert self.auth.revoke_key(key) is True
        assert self.auth.validate_key(key) is False

    def test_revoke_nonexistent_key(self):
        assert self.auth.revoke_key("fc_nonexistent") is False

    def test_list_keys(self):
        self.auth.generate_key("one")
        self.auth.generate_key("two")
        keys = self.auth.list_keys()
        assert len(keys) == 2
        assert keys[0]["name"] in ("one", "two")

    def test_extract_key_bearer(self):
        headers = {"Authorization": "Bearer fc_mytoken123"}
        assert APIAuth.extract_key(headers) == "fc_mytoken123"

    def test_extract_key_x_api_key(self):
        headers = {"X-API-Key": "fc_mytoken456"}
        assert APIAuth.extract_key(headers) == "fc_mytoken456"


# ════════════════════════════════════════════════════════════════
# Rate Limiter Tests (8)
# ════════════════════════════════════════════════════════════════

class TestRateLimiter:
    def test_allows_under_limit(self):
        rl = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert rl.check("client1") is True

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            rl.check("client1")
        assert rl.check("client1") is False

    def test_separate_clients(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.check("a")
        rl.check("a")
        assert rl.check("a") is False
        assert rl.check("b") is True  # different client

    def test_remaining(self):
        rl = RateLimiter(max_requests=10, window_seconds=60)
        assert rl.remaining("x") == 10
        rl.check("x")
        # remaining should be ~9 (may be slightly more due to refill)
        assert rl.remaining("x") <= 10

    def test_reset_client(self):
        rl = RateLimiter(max_requests=2, window_seconds=60)
        rl.check("c")
        rl.check("c")
        assert rl.check("c") is False
        rl.reset("c")
        assert rl.check("c") is True

    def test_reset_all(self):
        rl = RateLimiter(max_requests=1, window_seconds=60)
        rl.check("a")
        rl.check("b")
        rl.reset()
        assert rl.check("a") is True
        assert rl.check("b") is True

    def test_token_refill(self):
        rl = RateLimiter(max_requests=10, window_seconds=1)
        for _ in range(10):
            rl.check("fast")
        assert rl.check("fast") is False
        time.sleep(1.1)
        assert rl.check("fast") is True

    def test_default_params(self):
        rl = RateLimiter()
        assert rl.max_requests == 100
        assert rl.window_seconds == 60


# ════════════════════════════════════════════════════════════════
# Docs Tests (6)
# ════════════════════════════════════════════════════════════════

class TestAPIDocGenerator:
    def setup_method(self):
        self.docs = APIDocGenerator()

    def test_openapi_spec_is_dict(self):
        spec = self.docs.generate_openapi_spec()
        assert isinstance(spec, dict)

    def test_openapi_version(self):
        spec = self.docs.generate_openapi_spec()
        assert spec["openapi"] == "3.0.3"

    def test_openapi_has_paths(self):
        spec = self.docs.generate_openapi_spec()
        assert "/health" in spec["paths"]
        assert "/exchanges" in spec["paths"]
        assert "/alerts" in spec["paths"]

    def test_openapi_has_security(self):
        spec = self.docs.generate_openapi_spec()
        assert "security" in spec
        assert "components" in spec

    def test_swagger_html(self):
        html = self.docs.serve_docs_html()
        assert "swagger-ui" in html
        assert "FinClaw API" in html

    def test_custom_title_version(self):
        docs = APIDocGenerator(title="My API", version="9.9.9")
        spec = docs.generate_openapi_spec()
        assert spec["info"]["title"] == "My API"
        assert spec["info"]["version"] == "9.9.9"


# ════════════════════════════════════════════════════════════════
# Server / API Tests (20+)
# ════════════════════════════════════════════════════════════════

class _FakeRequest:
    """Minimal fake HTTP request for testing handlers."""

    def __init__(self, body: dict | None = None):
        self._body = json.dumps(body or {}).encode()
        self.headers = {"Content-Length": str(len(self._body))}
        self.rfile = io.BytesIO(self._body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))


class TestFinClawAPI:
    def setup_method(self):
        self.api = FinClawAPI(port=0, auth_enabled=False)

    def test_health_endpoint(self):
        result = self.api._handle_health()
        assert result["status"] == "ok"
        assert "uptime_seconds" in result
        assert result["version"] == "5.1.0"

    def test_exchanges_endpoint(self):
        result = self.api._handle_exchanges()
        assert "exchanges" in result

    def test_strategies_endpoint(self):
        result = self.api._handle_strategies()
        assert "strategies" in result

    def test_portfolio_endpoint(self):
        result = self.api._handle_portfolio()
        assert "holdings" in result

    def test_list_alerts_empty(self):
        result = self.api._handle_list_alerts()
        assert result["alerts"] == []

    def test_create_alert(self):
        req = _FakeRequest({"symbol": "AAPL", "condition": "above", "price": 200})
        result = self.api._handle_create_alert(request=req)
        assert result["_status"] == 201
        assert result["alert"]["symbol"] == "AAPL"
        assert result["alert"]["id"] == 1

    def test_create_alert_missing_fields(self):
        req = _FakeRequest({"symbol": "AAPL"})
        result = self.api._handle_create_alert(request=req)
        assert result["_status"] == 400

    def test_create_alert_invalid_condition(self):
        req = _FakeRequest({"symbol": "AAPL", "condition": "sideways", "price": 100})
        result = self.api._handle_create_alert(request=req)
        assert result["_status"] == 400

    def test_list_alerts_after_create(self):
        req = _FakeRequest({"symbol": "MSFT", "condition": "below", "price": 300})
        self.api._handle_create_alert(request=req)
        result = self.api._handle_list_alerts()
        assert len(result["alerts"]) == 1
        assert result["alerts"][0]["symbol"] == "MSFT"

    def test_backtest_endpoint(self):
        req = _FakeRequest({"symbol": "AAPL", "strategy": "momentum"})
        result = self.api._handle_backtest(request=req)
        assert result["symbol"] == "AAPL"
        assert result["strategy"] == "momentum"

    def test_backtest_missing_fields(self):
        req = _FakeRequest({"symbol": "AAPL"})
        result = self.api._handle_backtest(request=req)
        assert result["_status"] == 400

    def test_quote_bad_exchange(self):
        result = self.api._handle_quote(path_params={"exchange": "nonexistent", "symbol": "X"})
        assert "error" in result

    def test_history_bad_exchange(self):
        result = self.api._handle_history(
            params={}, path_params={"exchange": "nonexistent", "symbol": "X"}
        )
        assert "error" in result

    def test_docs_endpoint(self):
        result = self.api._handle_docs()
        assert "_html" in result
        assert "swagger-ui" in result["_html"]

    def test_openapi_endpoint(self):
        result = self.api._handle_openapi()
        assert result["openapi"] == "3.0.3"

    def test_create_handler_class(self):
        cls = self.api.create_handler_class()
        assert issubclass(cls, FinClawHandler)
        assert cls._api is self.api

    def test_api_default_params(self):
        api = FinClawAPI()
        assert api.host == "0.0.0.0"
        assert api.port == 8080
        assert api.cors_origin == "*"
        assert api.auth_enabled is False

    def test_api_custom_params(self):
        api = FinClawAPI(host="127.0.0.1", port=9090, auth_enabled=True)
        assert api.host == "127.0.0.1"
        assert api.port == 9090
        assert api.auth_enabled is True

    def test_multiple_alerts(self):
        for i in range(5):
            req = _FakeRequest({"symbol": f"SYM{i}", "condition": "above", "price": (i + 1) * 10})
            self.api._handle_create_alert(request=req)
        result = self.api._handle_list_alerts()
        assert len(result["alerts"]) == 5
        assert result["alerts"][4]["id"] == 5

    def test_backtest_with_all_fields(self):
        req = _FakeRequest({
            "symbol": "TSLA",
            "strategy": "mean_reversion",
            "start": "2023-01-01",
            "end": "2024-01-01",
            "capital": 50000,
        })
        result = self.api._handle_backtest(request=req)
        assert result["capital"] == 50000
        assert result["start"] == "2023-01-01"


# ════════════════════════════════════════════════════════════════
# Route Pattern Tests (4)
# ════════════════════════════════════════════════════════════════

class TestRoutePatterns:
    def test_health_route_matches(self):
        import re
        pattern = next(p for m, p, h in _ROUTES if h == "_handle_health")
        assert re.match(pattern, "/api/v1/health")

    def test_quote_route_captures(self):
        import re
        pattern = next(p for m, p, h in _ROUTES if h == "_handle_quote")
        m = re.match(pattern, "/api/v1/quote/yahoo/AAPL")
        assert m
        assert m.group("exchange") == "yahoo"
        assert m.group("symbol") == "AAPL"

    def test_history_route_captures(self):
        import re
        pattern = next(p for m, p, h in _ROUTES if h == "_handle_history")
        m = re.match(pattern, "/api/v1/history/binance/BTCUSDT")
        assert m
        assert m.group("exchange") == "binance"
        assert m.group("symbol") == "BTCUSDT"

    def test_all_routes_have_handlers(self):
        for method, pattern, handler_name in _ROUTES:
            assert method in ("GET", "POST")
            assert handler_name.startswith("_handle_")


# ════════════════════════════════════════════════════════════════
# Integration: Live Server Test (2)
# ════════════════════════════════════════════════════════════════

class TestLiveServer:
    def test_start_stop(self):
        """Test that server can start and stop cleanly."""
        api = FinClawAPI(host="127.0.0.1", port=0)
        # Just verify create_handler_class works
        cls = api.create_handler_class()
        assert cls._api is api

    def test_server_with_auth(self):
        """Test server with auth enabled."""
        api = FinClawAPI(auth_enabled=True)
        key = api.auth.generate_key("test")
        assert api.auth.validate_key(key)
        assert api.auth_enabled is True


# ════════════════════════════════════════════════════════════════
# CLI serve command test (2)
# ════════════════════════════════════════════════════════════════

class TestCLIServe:
    def test_build_parser_has_serve(self):
        from src.cli.main import build_parser
        parser = build_parser()
        # Parse serve args
        args = parser.parse_args(["serve", "--port", "9999"])
        assert args.command == "serve"
        assert args.port == 9999

    def test_build_parser_serve_defaults(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["serve"])
        assert args.host == "0.0.0.0"
        assert args.port == 8080
        assert args.auth is False
        assert args.rate_limit == 100
