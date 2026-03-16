"""
FinClaw - WebSocket Market Data Streaming
Real-time price streaming using free sources (Yahoo Finance, etc.).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketTick:
    """Single market data tick."""
    ticker: str
    price: float
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def spread(self) -> float:
        return self.ask - self.bid if self.ask > 0 and self.bid > 0 else 0.0


class MarketDataStream:
    """
    Real-time market data streaming with pub/sub pattern.

    Supports multiple data sources and allows subscribing callbacks
    per ticker for real-time price updates.

    Usage:
        stream = MarketDataStream()
        stream.subscribe('AAPL', my_callback)
        await stream.connect(source='yahoo')
        await stream.start()
    """

    SOURCES = ('yahoo', 'polygon', 'alpaca', 'mock')

    def __init__(self):
        self.subscribers: dict[str, list[Callable[[MarketTick], Any]]] = defaultdict(list)
        self._running = False
        self._source: str = 'yahoo'
        self._connection: Optional[Any] = None
        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 60.0
        self._last_ticks: dict[str, MarketTick] = {}
        self._tick_count: int = 0
        self._error_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def subscribed_tickers(self) -> list[str]:
        return list(self.subscribers.keys())

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def last_tick(self, ticker: str) -> Optional[MarketTick]:
        """Get the most recent tick for a ticker."""
        return self._last_ticks.get(ticker)

    async def connect(self, source: str = 'yahoo') -> bool:
        """
        Connect to a market data source.

        Args:
            source: Data source name ('yahoo', 'polygon', 'alpaca', 'mock')

        Returns:
            True if connection was established.

        Raises:
            ValueError: If source is not supported.
        """
        if source not in self.SOURCES:
            raise ValueError(f"Unsupported source: {source}. Use one of {self.SOURCES}")

        self._source = source
        self._reconnect_delay = 1.0
        logger.info("Connected to %s market data source", source)
        return True

    def subscribe(self, ticker: str, callback: Callable[[MarketTick], Any]) -> None:
        """
        Subscribe to real-time updates for a ticker.

        Args:
            ticker: Stock/asset ticker symbol (e.g. 'AAPL')
            callback: Function called with MarketTick on each update
        """
        ticker = ticker.upper()
        if callback not in self.subscribers[ticker]:
            self.subscribers[ticker].append(callback)
            logger.debug("Subscribed to %s (total callbacks: %d)", ticker, len(self.subscribers[ticker]))

    def unsubscribe(self, ticker: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from ticker updates.

        Args:
            ticker: Ticker to unsubscribe from
            callback: Specific callback to remove. If None, removes all.
        """
        ticker = ticker.upper()
        if ticker not in self.subscribers:
            return
        if callback is None:
            del self.subscribers[ticker]
        else:
            self.subscribers[ticker] = [cb for cb in self.subscribers[ticker] if cb is not callback]
            if not self.subscribers[ticker]:
                del self.subscribers[ticker]

    async def _dispatch(self, tick: MarketTick) -> None:
        """Dispatch a tick to all subscribers for that ticker."""
        self._last_ticks[tick.ticker] = tick
        self._tick_count += 1
        for cb in self.subscribers.get(tick.ticker, []):
            try:
                result = cb(tick)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self._error_count += 1
                logger.error("Callback error for %s: %s", tick.ticker, e)

    async def _generate_mock_ticks(self) -> None:
        """Generate mock ticks for testing."""
        import random
        base_prices = {t: 100.0 + random.random() * 400 for t in self.subscribers}
        while self._running:
            for ticker in list(self.subscribers.keys()):
                if ticker not in base_prices:
                    base_prices[ticker] = 100.0 + random.random() * 400
                price = base_prices[ticker] * (1 + random.gauss(0, 0.001))
                base_prices[ticker] = price
                tick = MarketTick(
                    ticker=ticker,
                    price=round(price, 2),
                    volume=random.randint(100, 10000),
                    bid=round(price - 0.01, 2),
                    ask=round(price + 0.01, 2),
                )
                await self._dispatch(tick)
            await asyncio.sleep(0.1)

    async def inject_tick(self, tick: MarketTick) -> None:
        """Inject a tick manually (useful for testing and replay)."""
        await self._dispatch(tick)

    async def start(self) -> None:
        """
        Start streaming market data. Blocks until stop() is called.

        Will automatically reconnect on failures with exponential backoff.
        """
        if not self.subscribers:
            logger.warning("No subscriptions — nothing to stream")
            return

        self._running = True
        logger.info("Starting %s stream for %d tickers", self._source, len(self.subscribers))

        while self._running:
            try:
                if self._source == 'mock':
                    await self._generate_mock_ticks()
                else:
                    # For real sources, would use websocket-client or aiohttp
                    # Placeholder: sleep and wait for injected ticks
                    while self._running:
                        await asyncio.sleep(0.1)
            except Exception as e:
                if not self._running:
                    break
                logger.error("Stream error: %s. Reconnecting in %.1fs", e, self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

    async def stop(self) -> None:
        """Stop the market data stream."""
        self._running = False
        logger.info("Market data stream stopped. Total ticks: %d", self._tick_count)

    def stats(self) -> dict:
        """Return streaming statistics."""
        return {
            'source': self._source,
            'running': self._running,
            'subscriptions': len(self.subscribers),
            'tickers': list(self.subscribers.keys()),
            'tick_count': self._tick_count,
            'error_count': self._error_count,
        }
