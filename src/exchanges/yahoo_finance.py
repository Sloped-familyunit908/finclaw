"""
Yahoo Finance adapter — free, no API key needed.
Uses Yahoo Finance v8 API endpoints directly (no yfinance dependency).
"""

import time
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class YahooFinanceAdapter(ExchangeAdapter):
    name = "yahoo"
    exchange_type = "stock_us"
    BASE_URL = "https://query1.finance.yahoo.com"

    TIMEFRAME_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo",
    }

    # Range mapping for timeframes
    RANGE_MAP = {
        "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
        "1h": "730d", "1d": "10y", "1w": "10y", "1M": "10y",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.client = HttpClient(self.BASE_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        interval = self.TIMEFRAME_MAP.get(timeframe, "1d")
        range_ = self.RANGE_MAP.get(timeframe, "1y")
        data = self.client.get(f"/v8/finance/chart/{symbol}", {
            "interval": interval, "range": range_,
        })
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        candles = []
        for i in range(len(timestamps)):
            if quotes["open"][i] is None:
                continue
            candles.append({
                "timestamp": timestamps[i] * 1000,
                "open": float(quotes["open"][i]),
                "high": float(quotes["high"][i]),
                "low": float(quotes["low"][i]),
                "close": float(quotes["close"][i]),
                "volume": float(quotes["volume"][i] or 0),
            })
        return candles[-limit:]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        data = self.client.get(f"/v8/finance/chart/{symbol}", {"interval": "1d", "range": "5d"})
        result = data["chart"]["result"][0]
        meta = result["meta"]
        last = float(meta["regularMarketPrice"])
        prev_close = float(meta.get("chartPreviousClose", meta.get("previousClose", last)))
        change = last - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0.0
        return {
            "symbol": meta["symbol"],
            "last": last,
            "bid": float(meta.get("bid", last)),
            "ask": float(meta.get("ask", last)),
            "volume": float(meta.get("regularMarketVolume", 0)),
            "change": round(change, 4),
            "change_pct": round(change_pct, 4),
            "timestamp": int(meta.get("regularMarketTime", 0)) * 1000,
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        # Yahoo Finance doesn't provide orderbook data
        return {"bids": [], "asks": []}

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("Yahoo Finance is a data-only adapter; trading not supported.")

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Yahoo Finance is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_balance(self) -> dict:
        raise NotImplementedError("Yahoo Finance is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        raise NotImplementedError("Yahoo Finance is a data-only adapter; trading not supported.")
