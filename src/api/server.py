"""
FinClaw REST API Server v5.1.0
Lightweight HTTP API using built-in http.server — no Flask/FastAPI dependency.

Endpoints (all under /api/v1):
  GET  /health                      — health check
  GET  /exchanges                   — list exchanges
  GET  /quote/{exchange}/{symbol}   — get quote
  GET  /history/{exchange}/{symbol} — get OHLCV history
  GET  /strategies                  — list strategies
  POST /backtest                    — run backtest
  GET  /portfolio                   — get portfolio status
  POST /alerts                      — create alert
  GET  /alerts                      — list alerts
  GET  /docs                        — Swagger UI
  GET  /openapi.json                — OpenAPI spec
"""

from __future__ import annotations

import json
import re
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable
from urllib.parse import urlparse, parse_qs

from .auth import APIAuth
from .rate_limiter import RateLimiter
from .docs import APIDocGenerator


def _json_response(data: Any) -> bytes:
    return json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")


# Route patterns: (method, regex, handler_name)
_ROUTES: list[tuple[str, str, str]] = [
    ("GET",  r"/api/v1/health$",                          "_handle_health"),
    ("GET",  r"/api/v1/exchanges$",                       "_handle_exchanges"),
    ("GET",  r"/api/v1/quote/(?P<exchange>[^/]+)/(?P<symbol>[^/]+)$", "_handle_quote"),
    ("GET",  r"/api/v1/history/(?P<exchange>[^/]+)/(?P<symbol>[^/]+)$", "_handle_history"),
    ("GET",  r"/api/v1/strategies$",                      "_handle_strategies"),
    ("POST", r"/api/v1/backtest$",                        "_handle_backtest"),
    ("GET",  r"/api/v1/portfolio$",                       "_handle_portfolio"),
    ("GET",  r"/api/v1/alerts$",                          "_handle_list_alerts"),
    ("POST", r"/api/v1/alerts$",                          "_handle_create_alert"),
    ("GET",  r"/api/v1/docs$",                            "_handle_docs"),
    ("GET",  r"/api/v1/openapi\\.json$",                  "_handle_openapi"),
]


class FinClawHandler(BaseHTTPRequestHandler):
    """Request handler for FinClaw API."""

    _api: "FinClawAPI" = None  # type: ignore[assignment]

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}

        api = self._api

        # Auth check (skip health + docs)
        if api.auth_enabled and not path.endswith(("/health", "/docs", "/openapi.json")):
            key = APIAuth.extract_key(dict(self.headers))
            if not api.auth.validate_key(key or ""):
                self._send(401, {"error": "unauthorized", "message": "Invalid or missing API key"})
                return

        # Rate limiting
        client_ip = self.client_address[0]
        if not api.rate_limiter.check(client_ip):
            self._send(429, {"error": "rate_limited", "message": "Too many requests"})
            return

        # Match route
        for route_method, pattern, handler_name in _ROUTES:
            if route_method != method:
                continue
            m = re.match(pattern, path)
            if m:
                handler = getattr(api, handler_name)
                try:
                    result = handler(params=params, path_params=m.groupdict(), request=self)
                    code = result.pop("_status", 200) if isinstance(result, dict) else 200
                    self._send(code, result)
                except Exception as exc:
                    self._send(500, {"error": str(exc), "traceback": traceback.format_exc()})
                return

        self._send(404, {"error": "not_found", "path": path})

    def _cors_headers(self) -> None:
        origin = self._api.cors_origin if self._api else "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")

    def _send(self, code: int, data: Any) -> None:
        body = _json_response(data)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def log_message(self, format: str, *args: Any) -> None:
        pass


class FinClawAPI:
    """
    REST API server for FinClaw.

    Usage:
        api = FinClawAPI(port=8080)
        api.start()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        cors_origin: str = "*",
        auth_enabled: bool = False,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        self.host = host
        self.port = port
        self.cors_origin = cors_origin
        self.auth_enabled = auth_enabled
        self.auth = APIAuth()
        self.rate_limiter = RateLimiter(max_requests, window_seconds)
        self.docs = APIDocGenerator()
        self._start_time = time.time()
        self._alerts: list[dict] = []
        self._httpd: HTTPServer | None = None
        self._cors_origin = cors_origin
        self._custom_routes: dict = {}

    def route(self, path: str, handler) -> None:
        """Register a custom route handler."""
        self._custom_routes[path] = handler

    # ── Endpoint handlers ──────────────────────────────────────

    def _handle_health(self, *args, **kw: Any) -> dict:
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "version": "5.1.0",
        }

    def _handle_exchanges(self, *args, **kw: Any) -> dict:
        try:
            from src.exchanges.registry import ExchangeRegistry
            exchanges = ExchangeRegistry.list_exchanges()
            return {"exchanges": exchanges}
        except ImportError:
            return {"exchanges": ["yahoo"], "note": "exchange registry not available"}

    def _handle_signal(self, *args, **kw: Any) -> dict:
        body = args[0] if args and isinstance(args[0], dict) else {}
        ticker = body.get("ticker")
        if not ticker:
            return {"error": "ticker required", "_status": 400}
        strategy = body.get("strategy", "momentum")
        return {"ticker": ticker, "strategy": strategy, "signal": "hold", "confidence": 0.5}

    def _handle_screen(self, *args, **kw: Any) -> dict:
        body = args[0] if args and isinstance(args[0], dict) else {}
        criteria = {}
        for k, v in body.items():
            try:
                criteria[k] = float(v)
            except (ValueError, TypeError):
                criteria[k] = v
        return {"criteria": criteria, "results": []}

    def _handle_quote(self, path_params: dict, **kw: Any) -> dict:
        exchange = path_params["exchange"]
        symbol = path_params["symbol"]
        try:
            from src.exchanges.registry import ExchangeRegistry
            adapter = ExchangeRegistry.get(exchange)
            ticker = adapter.get_ticker(symbol)
            return {"exchange": exchange, "symbol": symbol, "data": ticker}
        except Exception as e:
            return {"error": str(e), "_status": 400}

    def _handle_history(self, params: dict, path_params: dict, **kw: Any) -> dict:
        exchange = path_params["exchange"]
        symbol = path_params["symbol"]
        timeframe = params.get("timeframe", "1d")
        limit = int(params.get("limit", "100"))
        try:
            from src.exchanges.registry import ExchangeRegistry
            adapter = ExchangeRegistry.get(exchange)
            candles = adapter.get_ohlcv(symbol, timeframe, limit)
            return {"exchange": exchange, "symbol": symbol, "timeframe": timeframe, "candles": candles}
        except Exception as e:
            return {"error": str(e), "_status": 400}

    def _handle_strategies(self, *args, **kw: Any) -> dict:
        try:
            from src.strategies.library import list_strategies
            strategies = list_strategies()
            return {
                "strategies": [
                    {"slug": s.slug, "name": s.name, "category": s.category, "description": s.description}
                    for s in strategies
                ]
            }
        except ImportError:
            return {"strategies": [], "note": "strategy library not available"}

    def _handle_backtest(self, request: Any = None, **kw: Any) -> dict:
        try:
            if isinstance(request, dict):
                body = request
            else:
                body = request._read_json_body() if request else {}
        except (json.JSONDecodeError, Exception):
            return {"error": "invalid JSON body", "_status": 400}

        ticker = body.get("ticker") or body.get("symbol")
        symbol = ticker
        strategy = body.get("strategy")
        if not symbol or not strategy:
            return {"error": "symbol and strategy are required", "_status": 400}

        return {
            "ticker": ticker,
            "symbol": symbol,
            "strategy": strategy,
            "start": body.get("start"),
            "end": body.get("end"),
            "capital": body.get("capital", 10000),
            "status": "placeholder",
            "message": "Connect backtest engine for live results",
        }

    def _handle_portfolio(self, *args, **kw: Any) -> dict:
        body = args[0] if args and isinstance(args[0], dict) else {}
        tickers_str = body.get("tickers", "")
        if not tickers_str:
            return {
                "holdings": [],
                "total_value": 0,
                "message": "Connect portfolio tracker for live data",
            }
        tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
        weight = 1.0 / len(tickers) if tickers else 0
        return {
            "holdings": tickers,
            "weights": {t: weight for t in tickers},
            "total_value": 0,
            "message": "Connect portfolio tracker for live data",
        }

    def _handle_list_alerts(self, *args, **kw: Any) -> dict:
        return {"alerts": self._alerts}

    def _handle_create_alert(self, request: Any = None, **kw: Any) -> dict:
        try:
            body = request._read_json_body() if request else {}
        except (json.JSONDecodeError, Exception):
            return {"error": "invalid JSON body", "_status": 400}

        ticker = body.get("ticker") or body.get("symbol")
        symbol = ticker
        condition = body.get("condition")
        price = body.get("price")
        if not all([symbol, condition, price]):
            return {"error": "symbol, condition, and price are required", "_status": 400}
        if condition not in ("above", "below"):
            return {"error": "condition must be 'above' or 'below'", "_status": 400}

        alert = {
            "id": len(self._alerts) + 1,
            "symbol": symbol,
            "condition": condition,
            "price": price,
            "created": time.time(),
            "triggered": False,
        }
        self._alerts.append(alert)
        return {"alert": alert, "_status": 201}

    def _handle_docs(self, *args, **kw: Any) -> dict:
        # Special: return HTML directly. We abuse the dict pattern
        # by returning a marker that the handler detects.
        return {"_html": self.docs.serve_docs_html(), "_status": 200}

    def _handle_openapi(self, *args, **kw: Any) -> dict:
        return self.docs.generate_openapi_spec()

    # ── Server lifecycle ───────────────────────────────────────

    def start(self) -> None:
        """Start the HTTP server (blocking)."""
        handler_cls = type("Handler", (FinClawHandler,), {"_api": self})
        self._httpd = HTTPServer((self.host, self.port), handler_cls)
        print(f"  🦀 FinClaw API running on http://{self.host}:{self.port}/api/v1")
        print(f"  📖 Docs: http://{self.host}:{self.port}/api/v1/docs")
        self._httpd.serve_forever()

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
        self._cors_origin = cors_origin
        self._custom_routes: dict = {}

    def route(self, path: str, handler) -> None:
        """Register a custom route handler."""
        self._custom_routes[path] = handler

    def create_handler_class(self) -> type:
        """Create handler class for testing without starting server."""
        routes = {pattern.replace(r"$", "").replace("\\.", "."): name for _, pattern, name in _ROUTES}
        routes["/api/health"] = "_handle_health"
        routes.update(self._custom_routes)
        return type("Handler", (FinClawHandler,), {"_api": self, "_routes": routes})


# Keep backward compat alias
FinClawServer = FinClawAPI
