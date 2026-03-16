"""
Multi-Source Data Fetcher
Fetch from yfinance with cache, extensible to other sources.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from .cache import DataCache


@dataclass
class FetchResult:
    source: str
    bars: list[dict]
    symbol: str
    from_cache: bool


class MultiSourceFetcher:
    """
    Fetch price data with caching and fallback sources.
    Primary: yfinance. Extensible via register_source().
    """

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()
        self._sources: list[tuple[str, callable]] = []
        # Register default yfinance source
        self._sources.append(("yfinance", self._fetch_yfinance))

    def register_source(self, name: str, fetcher: callable):
        """Register an additional data source."""
        self._sources.append((name, fetcher))

    async def fetch(
        self,
        symbol: str,
        period: str = "2y",
        interval: str = "1d",
    ) -> FetchResult:
        """Fetch with cache-first, then try each source in order."""
        cache_key = f"{symbol}_{period}_{interval}"

        # Cache hit
        cached = self.cache.get(cache_key)
        if cached:
            return FetchResult(source="cache", bars=cached, symbol=symbol, from_cache=True)

        # Try each source
        for name, fetcher in self._sources:
            try:
                bars = await fetcher(symbol, period, interval)
                if bars and len(bars) > 0:
                    self.cache.set(cache_key, bars)
                    return FetchResult(source=name, bars=bars, symbol=symbol, from_cache=False)
            except Exception:
                continue

        return FetchResult(source="none", bars=[], symbol=symbol, from_cache=False)

    @staticmethod
    async def _fetch_yfinance(symbol: str, period: str, interval: str) -> list[dict]:
        """Fetch from yfinance (runs in thread to avoid blocking)."""
        import asyncio
        import yfinance as yf

        def _do():
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            bars = []
            for idx, row in df.iterrows():
                bars.append({
                    "date": idx.to_pydatetime(),
                    "price": float(row["Close"]),
                    "open": float(row.get("Open", row["Close"])),
                    "high": float(row.get("High", row["Close"])),
                    "low": float(row.get("Low", row["Close"])),
                    "volume": float(row.get("Volume", 0)),
                })
            return bars

        return await asyncio.get_event_loop().run_in_executor(None, _do)
