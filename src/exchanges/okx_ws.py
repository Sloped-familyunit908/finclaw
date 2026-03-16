"""
OKX WebSocket streams — ticker, kline, orderbook, trades.
"""

import json
import logging
from typing import Callable

from src.exchanges.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

PUBLIC_WS = "wss://ws.okx.com:8443/ws/v5/public"


class OKXWebSocket(WebSocketClient):
    """OKX WebSocket client for real-time market data."""

    def __init__(self, on_message: Callable | None = None, on_error: Callable | None = None):
        super().__init__(PUBLIC_WS, on_message=on_message, on_error=on_error)

    async def _send_subscribe(self, channel: str, symbol: str, params: dict) -> None:
        args = self._build_args(channel, symbol, params)
        await self.send({"op": "subscribe", "args": [args]})

    async def _send_unsubscribe(self, channel: str, symbol: str) -> None:
        args = self._build_args(channel, symbol, {})
        await self.send({"op": "unsubscribe", "args": [args]})

    def _build_args(self, channel: str, symbol: str, params: dict) -> dict:
        channel_map = {
            "ticker": "tickers",
            "kline": f"candle{params.get('interval', '1m')}",
            "orderbook": f"books{params.get('depth', 5)}",
            "trades": "trades",
        }
        return {"channel": channel_map.get(channel, channel), "instId": symbol}

    async def subscribe_ticker(self, symbol: str) -> None:
        await self.subscribe("ticker", symbol)

    async def subscribe_kline(self, symbol: str, interval: str = "1m") -> None:
        await self.subscribe("kline", symbol, interval=interval)

    async def subscribe_orderbook(self, symbol: str, depth: int = 5) -> None:
        await self.subscribe("orderbook", symbol, depth=depth)

    async def subscribe_trades(self, symbol: str) -> None:
        await self.subscribe("trades", symbol)

    @staticmethod
    def parse_ticker(data: dict) -> dict | None:
        if "arg" not in data or data.get("arg", {}).get("channel") != "tickers":
            return None
        if not data.get("data"):
            return None
        d = data["data"][0]
        return {
            "exchange": "okx",
            "symbol": d["instId"],
            "last": float(d["last"]),
            "bid": float(d.get("bidPx", 0)),
            "ask": float(d.get("askPx", 0)),
            "high": float(d.get("high24h", 0)),
            "low": float(d.get("low24h", 0)),
            "volume": float(d.get("vol24h", 0)),
            "timestamp": int(d.get("ts", 0)),
        }

    @staticmethod
    def parse_trade(data: dict) -> dict | None:
        if "arg" not in data or data.get("arg", {}).get("channel") != "trades":
            return None
        if not data.get("data"):
            return None
        d = data["data"][0]
        return {
            "exchange": "okx",
            "symbol": d["instId"],
            "price": float(d["px"]),
            "quantity": float(d["sz"]),
            "side": d["side"],
            "timestamp": int(d["ts"]),
            "trade_id": d.get("tradeId", ""),
        }
