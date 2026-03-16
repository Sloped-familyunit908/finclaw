"""
Bybit WebSocket streams — ticker, kline, orderbook, trades.
"""

import json
import logging
from typing import Callable

from src.exchanges.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

PUBLIC_WS = "wss://stream.bybit.com/v5/public/spot"


class BybitWebSocket(WebSocketClient):
    """Bybit V5 WebSocket client for real-time market data."""

    def __init__(self, category: str = "spot", on_message: Callable | None = None, on_error: Callable | None = None):
        url = f"wss://stream.bybit.com/v5/public/{category}"
        super().__init__(url, on_message=on_message, on_error=on_error)
        self.category = category
        self._req_id = 0

    def _next_req_id(self) -> str:
        self._req_id += 1
        return str(self._req_id)

    async def _send_subscribe(self, channel: str, symbol: str, params: dict) -> None:
        topic = self._build_topic(channel, symbol, params)
        await self.send({"req_id": self._next_req_id(), "op": "subscribe", "args": [topic]})

    async def _send_unsubscribe(self, channel: str, symbol: str) -> None:
        topic = self._build_topic(channel, symbol, {})
        await self.send({"req_id": self._next_req_id(), "op": "unsubscribe", "args": [topic]})

    def _build_topic(self, channel: str, symbol: str, params: dict) -> str:
        if channel == "ticker":
            return f"tickers.{symbol}"
        elif channel == "kline":
            interval = params.get("interval", "1")
            return f"kline.{interval}.{symbol}"
        elif channel == "orderbook":
            depth = params.get("depth", 5)
            # Bybit depth levels: 1, 25, 50, 200
            valid = [1, 25, 50, 200]
            depth = min(valid, key=lambda x: abs(x - depth))
            return f"orderbook.{depth}.{symbol}"
        elif channel == "trades":
            return f"publicTrade.{symbol}"
        else:
            return f"{channel}.{symbol}"

    async def subscribe_ticker(self, symbol: str) -> None:
        await self.subscribe("ticker", symbol)

    async def subscribe_kline(self, symbol: str, interval: str = "1") -> None:
        await self.subscribe("kline", symbol, interval=interval)

    async def subscribe_orderbook(self, symbol: str, depth: int = 5) -> None:
        await self.subscribe("orderbook", symbol, depth=depth)

    async def subscribe_trades(self, symbol: str) -> None:
        await self.subscribe("trades", symbol)

    @staticmethod
    def parse_ticker(data: dict) -> dict | None:
        if data.get("topic", "").startswith("tickers.") and "data" in data:
            d = data["data"]
            return {
                "exchange": "bybit",
                "symbol": d.get("symbol", ""),
                "last": float(d.get("lastPrice", 0)),
                "bid": float(d.get("bid1Price", 0)),
                "ask": float(d.get("ask1Price", 0)),
                "high": float(d.get("highPrice24h", 0)),
                "low": float(d.get("lowPrice24h", 0)),
                "volume": float(d.get("volume24h", 0)),
                "timestamp": int(data.get("ts", 0)),
            }
        return None

    @staticmethod
    def parse_trade(data: dict) -> dict | None:
        if data.get("topic", "").startswith("publicTrade.") and "data" in data:
            trades = data["data"]
            if not trades:
                return None
            d = trades[0]
            return {
                "exchange": "bybit",
                "symbol": d.get("s", ""),
                "price": float(d.get("p", 0)),
                "quantity": float(d.get("v", 0)),
                "side": d.get("S", "").lower(),
                "timestamp": int(d.get("T", 0)),
                "trade_id": d.get("i", ""),
            }
        return None
