"""
Real-time data aggregator — combines feeds from multiple exchanges,
computes cross-exchange spreads and arbitrage opportunities.
"""

import asyncio
import logging
import time
from typing import Any

from src.exchanges.ws_client import WebSocketClient
from src.exchanges.binance_ws import BinanceWebSocket
from src.exchanges.okx_ws import OKXWebSocket
from src.exchanges.bybit_ws import BybitWebSocket

logger = logging.getLogger(__name__)

EXCHANGE_WS_MAP = {
    "binance": BinanceWebSocket,
    "okx": OKXWebSocket,
    "bybit": BybitWebSocket,
}


class DataAggregator:
    """Aggregates real-time market data from multiple exchange WebSocket feeds."""

    def __init__(self):
        self.feeds: dict[str, WebSocketClient] = {}
        self._latest: dict[str, dict[str, dict]] = {}  # {exchange: {symbol: data}}
        self._running = False
        self._callbacks: list = []

    def add_feed(self, exchange: str, symbol: str, channels: list[str]) -> None:
        """Register a feed to subscribe to when started."""
        key = exchange.lower()
        if key not in self._latest:
            self._latest[key] = {}
        if key not in self.feeds:
            if key not in EXCHANGE_WS_MAP:
                raise ValueError(f"Unsupported exchange: {exchange}")
            ws = EXCHANGE_WS_MAP[key](on_message=lambda data, ex=key: self._handle_message(ex, data))
            self.feeds[key] = ws

        # Store subscription intent
        self._latest[key].setdefault(symbol, {"_channels": channels, "_subscribed": False})

    def on_update(self, callback) -> None:
        """Register callback for data updates: callback(exchange, symbol, data)."""
        self._callbacks.append(callback)

    def _handle_message(self, exchange: str, data: dict) -> None:
        """Process incoming message and update latest data."""
        parsed = self._parse(exchange, data)
        if parsed and "symbol" in parsed:
            symbol = parsed["symbol"]
            self._latest.setdefault(exchange, {})[symbol] = {
                **self._latest.get(exchange, {}).get(symbol, {}),
                **parsed,
                "_updated": time.time(),
            }
            for cb in self._callbacks:
                try:
                    cb(exchange, symbol, parsed)
                except Exception as e:
                    logger.error("Callback error: %s", e)

    def _parse(self, exchange: str, data: dict) -> dict | None:
        """Parse exchange-specific message into normalized format."""
        ws = self.feeds.get(exchange)
        if ws and hasattr(ws, "parse_ticker"):
            result = ws.parse_ticker(data)
            if result:
                return result
        if ws and hasattr(ws, "parse_trade"):
            result = ws.parse_trade(data)
            if result:
                return result
        return None

    def get_latest(self, exchange: str, symbol: str) -> dict:
        """Get latest data for an exchange+symbol pair."""
        return self._latest.get(exchange.lower(), {}).get(symbol, {})

    def get_spread(self, symbol: str) -> dict:
        """Compute cross-exchange spread for a symbol."""
        prices = {}
        for exchange, symbols in self._latest.items():
            if symbol in symbols and "last" in symbols[symbol]:
                prices[exchange] = symbols[symbol]["last"]

        if len(prices) < 2:
            return {"symbol": symbol, "exchanges": prices, "spread": 0, "spread_pct": 0}

        sorted_prices = sorted(prices.items(), key=lambda x: x[1])
        low_ex, low_price = sorted_prices[0]
        high_ex, high_price = sorted_prices[-1]
        spread = high_price - low_price
        spread_pct = (spread / low_price * 100) if low_price > 0 else 0

        return {
            "symbol": symbol,
            "exchanges": prices,
            "low": {"exchange": low_ex, "price": low_price},
            "high": {"exchange": high_ex, "price": high_price},
            "spread": spread,
            "spread_pct": round(spread_pct, 4),
        }

    def get_arbitrage_opportunities(self, min_spread_pct: float = 0.1) -> list[dict]:
        """Find cross-exchange arbitrage opportunities above threshold."""
        symbols = set()
        for exchange_data in self._latest.values():
            symbols.update(exchange_data.keys())

        opportunities = []
        for symbol in symbols:
            spread_info = self.get_spread(symbol)
            if spread_info["spread_pct"] >= min_spread_pct:
                opportunities.append(spread_info)

        return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)

    async def start(self) -> None:
        """Connect all feeds and subscribe to registered channels."""
        self._running = True
        connect_tasks = []
        for exchange, ws in self.feeds.items():
            connect_tasks.append(self._start_feed(exchange, ws))
        await asyncio.gather(*connect_tasks, return_exceptions=True)

    async def _start_feed(self, exchange: str, ws: WebSocketClient) -> None:
        """Connect one feed and subscribe."""
        await ws.connect()
        for symbol, info in self._latest.get(exchange, {}).items():
            if isinstance(info, dict) and "_channels" in info:
                for channel in info["_channels"]:
                    await ws.subscribe(channel, symbol)
                info["_subscribed"] = True

    async def stop(self) -> None:
        """Close all WebSocket connections."""
        self._running = False
        for ws in self.feeds.values():
            await ws.close()
        logger.info("All feeds stopped")

    @property
    def connected_exchanges(self) -> list[str]:
        return [ex for ex, ws in self.feeds.items() if ws.connected]
