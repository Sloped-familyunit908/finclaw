"""
Binance WebSocket streams — ticker, kline, orderbook, trades.
Supports spot (stream.binance.com) and futures (fstream.binance.com).
"""

import asyncio
import json
import logging
from typing import Callable

from src.exchanges.ws_client import WebSocketClient

logger = logging.getLogger(__name__)

SPOT_WS = "wss://stream.binance.com:9443/ws"
FUTURES_WS = "wss://fstream.binance.com/ws"


class BinanceWebSocket(WebSocketClient):
    """Binance WebSocket client for real-time market data."""

    def __init__(self, futures: bool = False, on_message: Callable | None = None, on_error: Callable | None = None):
        url = FUTURES_WS if futures else SPOT_WS
        super().__init__(url, on_message=on_message, on_error=on_error)
        self.futures = futures
        self._id_counter = 0

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    async def _send_subscribe(self, channel: str, symbol: str, params: dict) -> None:
        stream = self._build_stream(channel, symbol, params)
        try:
            await self.send({"method": "SUBSCRIBE", "params": [stream], "id": self._next_id()})
        except (ConnectionError, OSError, asyncio.TimeoutError) as e:
            logger.error("Binance subscribe failed for %s/%s: %s", channel, symbol, e)
            raise

    async def _send_unsubscribe(self, channel: str, symbol: str) -> None:
        stream = self._build_stream(channel, symbol, {})
        try:
            await self.send({"method": "UNSUBSCRIBE", "params": [stream], "id": self._next_id()})
        except (ConnectionError, OSError, asyncio.TimeoutError) as e:
            logger.error("Binance unsubscribe failed for %s/%s: %s", channel, symbol, e)
            raise

    def _build_stream(self, channel: str, symbol: str, params: dict) -> str:
        s = symbol.lower()
        if channel == "ticker":
            return f"{s}@ticker"
        elif channel == "kline":
            interval = params.get("interval", "1m")
            return f"{s}@kline_{interval}"
        elif channel == "orderbook":
            depth = params.get("depth", 5)
            return f"{s}@depth{depth}@100ms"
        elif channel == "trades":
            return f"{s}@trade"
        elif channel == "aggTrades":
            return f"{s}@aggTrade"
        else:
            return f"{s}@{channel}"

    # --- Convenience methods ---

    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to 24hr ticker updates."""
        await self.subscribe("ticker", symbol)

    async def subscribe_kline(self, symbol: str, interval: str = "1m") -> None:
        """Subscribe to kline/candlestick updates."""
        await self.subscribe("kline", symbol, interval=interval)

    async def subscribe_orderbook(self, symbol: str, depth: int = 5) -> None:
        """Subscribe to partial orderbook depth updates."""
        await self.subscribe("orderbook", symbol, depth=depth)

    async def subscribe_trades(self, symbol: str) -> None:
        """Subscribe to real-time trade stream."""
        await self.subscribe("trades", symbol)

    @staticmethod
    def parse_ticker(data: dict) -> dict | None:
        """Parse Binance ticker message into normalized format."""
        try:
            if "e" not in data or data["e"] != "24hrTicker":
                return None
            return {
                "exchange": "binance",
                "symbol": data["s"],
                "last": float(data["c"]),
                "bid": float(data["b"]),
                "ask": float(data["a"]),
                "high": float(data["h"]),
                "low": float(data["l"]),
                "volume": float(data["v"]),
                "change_pct": float(data["P"]),
                "timestamp": data["E"],
            }
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse Binance ticker: %s", e)
            return None

    @staticmethod
    def parse_kline(data: dict) -> dict | None:
        """Parse Binance kline message into normalized OHLCV."""
        try:
            if "e" not in data or data["e"] != "kline":
                return None
            k = data["k"]
            return {
                "exchange": "binance",
                "symbol": k["s"],
                "interval": k["i"],
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
                "timestamp": k["t"],
                "closed": k["x"],
            }
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse Binance kline: %s", e)
            return None

    @staticmethod
    def parse_trade(data: dict) -> dict | None:
        """Parse Binance trade message."""
        try:
            if "e" not in data or data["e"] != "trade":
                return None
            return {
                "exchange": "binance",
                "symbol": data["s"],
                "price": float(data["p"]),
                "quantity": float(data["q"]),
                "side": "sell" if data["m"] else "buy",
                "timestamp": data["T"],
                "trade_id": data["t"],
            }
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse Binance trade: %s", e)
            return None
