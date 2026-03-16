"""
FinClaw REST API Server
Lightweight HTTP API using built-in http.server — no Flask dependency.
Endpoints:
  GET /api/signal?ticker=AAPL&strategy=momentum
  GET /api/backtest?ticker=AAPL&strategy=mean_reversion&start=2020-01-01
  GET /api/portfolio?tickers=AAPL,MSFT,GOOGL&method=risk_parity
  GET /api/screen?rsi_lt=30&volume_gt=1.5
  GET /api/health
"""

from __future__ import annotations

import json
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable
from urllib.parse import urlparse, parse_qs


def _json_response(data: Any) -> bytes:
    """Serialize response to JSON bytes."""
    return json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")


class FinClawHandler(BaseHTTPRequestHandler):
    """Request handler for FinClaw API."""

    # Attached by FinClawServer
    _routes: dict[str, Callable] = {}
    _cors_origin: str = "*"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}

        handler = self._routes.get(path)
        if handler is None:
            self._send(404, {"error": "not_found", "path": path})
            return

        try:
            result = handler(params)
            self._send(200, result)
        except Exception as exc:
            self._send(500, {"error": str(exc), "traceback": traceback.format_exc()})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", self._cors_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send(self, code: int, data: Any) -> None:
        body = _json_response(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Suppress default stderr logging."""
        pass


class FinClawServer:
    """
    Lightweight REST API server for FinClaw.

    Usage:
        server = FinClawServer(port=8080)
        server.start()  # blocking
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, cors_origin: str = "*"):
        self.host = host
        self.port = port
        self._routes: dict[str, Callable] = {}
        self._cors_origin = cors_origin
        self._start_time = time.time()
        self._register_defaults()

    def route(self, path: str, handler: Callable) -> None:
        """Register a route handler. Handler receives dict of query params."""
        self._routes[path.rstrip("/")] = handler

    def _register_defaults(self) -> None:
        self.route("/api/health", self._handle_health)
        self.route("/api/signal", self._handle_signal)
        self.route("/api/backtest", self._handle_backtest)
        self.route("/api/portfolio", self._handle_portfolio)
        self.route("/api/screen", self._handle_screen)

    # --- Default handlers ---

    def _handle_health(self, params: dict) -> dict:
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "version": "1.8.0",
        }

    def _handle_signal(self, params: dict) -> dict:
        ticker = params.get("ticker")
        strategy = params.get("strategy", "momentum")
        if not ticker:
            return {"error": "missing required param: ticker"}
        return {
            "ticker": ticker,
            "strategy": strategy,
            "signal": "hold",
            "strength": 0.0,
            "timestamp": time.time(),
        }

    def _handle_backtest(self, params: dict) -> dict:
        ticker = params.get("ticker")
        strategy = params.get("strategy", "momentum")
        start = params.get("start", "2020-01-01")
        if not ticker:
            return {"error": "missing required param: ticker"}
        return {
            "ticker": ticker,
            "strategy": strategy,
            "start": start,
            "status": "placeholder",
            "message": "Connect backtest engine for live results",
        }

    def _handle_portfolio(self, params: dict) -> dict:
        tickers_raw = params.get("tickers", "")
        method = params.get("method", "equal_weight")
        tickers = [t.strip() for t in tickers_raw.split(",") if t.strip()]
        if not tickers:
            return {"error": "missing required param: tickers"}
        n = len(tickers)
        return {
            "tickers": tickers,
            "method": method,
            "weights": {t: round(1.0 / n, 4) for t in tickers},
        }

    def _handle_screen(self, params: dict) -> dict:
        criteria = {}
        for key, val in params.items():
            try:
                criteria[key] = float(val)
            except (ValueError, TypeError):
                criteria[key] = val
        return {
            "criteria": criteria,
            "matches": [],
            "message": "Connect screener engine for live results",
        }

    def start(self) -> None:
        """Start the HTTP server (blocking)."""
        handler_cls = type("Handler", (FinClawHandler,), {
            "_routes": self._routes,
            "_cors_origin": self._cors_origin,
        })
        httpd = HTTPServer((self.host, self.port), handler_cls)
        httpd.serve_forever()

    def create_handler_class(self) -> type:
        """Create handler class for testing without starting server."""
        return type("Handler", (FinClawHandler,), {
            "_routes": self._routes,
            "_cors_origin": self._cors_origin,
        })
