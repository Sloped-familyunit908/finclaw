"""
Polygon.io adapter — aggregates, tickers, quotes, reference data.
Free tier: 5 API calls/min.
"""

import time

from src.exchanges.base import ExchangeAdapter
from src.exchanges.http_client import HttpClient


class PolygonAdapter(ExchangeAdapter):
    name = "polygon"
    exchange_type = "stock_us"

    BASE_URL = "https://api.polygon.io"

    TIMEFRAME_MAP = {
        "1m": ("minute", 1), "5m": ("minute", 5), "15m": ("minute", 15),
        "30m": ("minute", 30), "1h": ("hour", 1), "4h": ("hour", 4),
        "1d": ("day", 1), "1w": ("week", 1), "1M": ("month", 1),
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.client = HttpClient(self.BASE_URL)

    def _params(self, extra: dict | None = None) -> dict:
        p = {"apiKey": self.api_key}
        if extra:
            p.update(extra)
        return p

    # --- Market Data ---

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        multiplier_type = self.TIMEFRAME_MAP.get(timeframe, ("day", 1))
        timespan, multiplier = multiplier_type
        # Default date range: last 6 months
        to_date = time.strftime("%Y-%m-%d")
        # rough calculation
        days_back = limit * {"minute": 1, "hour": 1, "day": 1, "week": 7, "month": 30}.get(timespan, 1)
        from_ts = time.time() - days_back * 86400
        from_date = time.strftime("%Y-%m-%d", time.gmtime(from_ts))
        path = f"/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        data = self.client.get(path, self._params({"limit": limit, "sort": "asc"}))
        results = data.get("results", [])
        return [
            {"timestamp": int(r["t"]), "open": float(r["o"]), "high": float(r["h"]),
             "low": float(r["l"]), "close": float(r["c"]), "volume": float(r.get("v", 0))}
            for r in results
        ]

    def get_ticker(self, symbol: str) -> dict:
        data = self.client.get(
            f"/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}",
            self._params(),
        )
        ticker = data.get("ticker", {})
        day = ticker.get("day", {})
        last_trade = ticker.get("lastTrade", {})
        last_quote = ticker.get("lastQuote", {})
        return {
            "symbol": symbol.upper(),
            "last": float(last_trade.get("p", 0)),
            "bid": float(last_quote.get("p", 0)),
            "ask": float(last_quote.get("P", 0)),
            "volume": float(day.get("v", 0)),
            "timestamp": int(ticker.get("updated", 0)),
        }

    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        data = self.client.get(
            f"/v3/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}/book",
            self._params(),
        )
        bids = data.get("data", {}).get("bids", [])
        asks = data.get("data", {}).get("asks", [])
        return {
            "bids": [[float(b["p"]), float(b.get("s", 0))] for b in bids[:depth]],
            "asks": [[float(a["p"]), float(a.get("s", 0))] for a in asks[:depth]],
        }

    def get_quotes(self, symbol: str, limit: int = 50) -> list[dict]:
        data = self.client.get(
            f"/v3/quotes/{symbol.upper()}",
            self._params({"limit": limit, "sort": "timestamp", "order": "desc"}),
        )
        return [
            {"bid": float(q.get("bid_price", 0)), "ask": float(q.get("ask_price", 0)),
             "bid_size": int(q.get("bid_size", 0)), "ask_size": int(q.get("ask_size", 0)),
             "timestamp": q.get("sip_timestamp", 0)}
            for q in data.get("results", [])
        ]

    # --- Reference Data ---

    def get_ticker_details(self, symbol: str) -> dict:
        data = self.client.get(f"/v3/reference/tickers/{symbol.upper()}", self._params())
        return data.get("results", {})

    def get_market_status(self) -> dict:
        return self.client.get("/v1/marketstatus/now", self._params())

    def search_tickers(self, query: str, limit: int = 20) -> list[dict]:
        data = self.client.get(
            "/v3/reference/tickers",
            self._params({"search": query, "limit": limit, "active": "true"}),
        )
        return data.get("results", [])

    # --- Not supported (read-only data provider) ---

    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("Polygon.io is a data provider — no trading support")

    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Polygon.io is a data provider — no trading support")

    def get_balance(self) -> dict:
        return {}

    def get_positions(self) -> list[dict]:
        return []
