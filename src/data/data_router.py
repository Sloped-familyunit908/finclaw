"""
FinClaw Data Router v3.5.0
Unified market data access with provider fallback chain.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Base class for all data providers."""

    @abstractmethod
    def get_ohlcv(self, ticker: str, start: str, end: str) -> dict:
        """Return OHLCV data: {dates, open, high, low, close, volume}."""

    @abstractmethod
    def get_realtime(self, ticker: str) -> dict:
        """Return realtime quote: {price, volume, timestamp, bid, ask}."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if provider is operational."""


class YahooProvider(DataProvider):
    """Yahoo Finance data provider (via yfinance)."""

    name = "yahoo"

    def get_ohlcv(self, ticker: str, start: str, end: str) -> dict:
        try:
            import yfinance as yf
            df = yf.download(ticker, start=start, end=end, progress=False)
            if df.empty:
                raise ValueError(f"No data for {ticker}")
            # Handle multi-level columns from yfinance
            if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
                df.columns = df.columns.droplevel(1)
            return {
                "dates": [d.isoformat() for d in df.index],
                "open": df["Open"].tolist(),
                "high": df["High"].tolist(),
                "low": df["Low"].tolist(),
                "close": df["Close"].tolist(),
                "volume": df["Volume"].tolist(),
                "source": "yahoo",
            }
        except Exception as e:
            logger.warning("Yahoo provider failed for %s: %s", ticker, e)
            raise

    def get_realtime(self, ticker: str) -> dict:
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info
            return {
                "price": float(info.last_price),
                "volume": int(info.last_volume) if hasattr(info, "last_volume") else 0,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "yahoo",
            }
        except Exception as e:
            logger.warning("Yahoo realtime failed for %s: %s", ticker, e)
            raise

    def health_check(self) -> bool:
        try:
            import yfinance as yf
            t = yf.Ticker("AAPL")
            _ = t.fast_info.last_price
            return True
        except Exception:
            return False


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider."""

    name = "alpha_vantage"

    def __init__(self, api_key: str = "demo"):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"

    def get_ohlcv(self, ticker: str, start: str, end: str) -> dict:
        try:
            import requests
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "full",
                "apikey": self.api_key,
            }
            resp = requests.get(self.base_url, params=params, timeout=15)
            data = resp.json()
            ts = data.get("Time Series (Daily)", {})
            if not ts:
                raise ValueError(f"No data from Alpha Vantage for {ticker}")

            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            filtered = {
                k: v for k, v in ts.items()
                if start_dt <= datetime.fromisoformat(k) <= end_dt
            }
            dates = sorted(filtered.keys())
            return {
                "dates": dates,
                "open": [float(filtered[d]["1. open"]) for d in dates],
                "high": [float(filtered[d]["2. high"]) for d in dates],
                "low": [float(filtered[d]["3. low"]) for d in dates],
                "close": [float(filtered[d]["4. close"]) for d in dates],
                "volume": [int(filtered[d]["5. volume"]) for d in dates],
                "source": "alpha_vantage",
            }
        except Exception as e:
            logger.warning("Alpha Vantage failed for %s: %s", ticker, e)
            raise

    def get_realtime(self, ticker: str) -> dict:
        try:
            import requests
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
                "apikey": self.api_key,
            }
            resp = requests.get(self.base_url, params=params, timeout=15)
            q = resp.json().get("Global Quote", {})
            if not q:
                raise ValueError(f"No realtime data for {ticker}")
            return {
                "price": float(q["05. price"]),
                "volume": int(q["06. volume"]),
                "timestamp": datetime.utcnow().isoformat(),
                "source": "alpha_vantage",
            }
        except Exception as e:
            logger.warning("Alpha Vantage realtime failed for %s: %s", ticker, e)
            raise

    def health_check(self) -> bool:
        try:
            import requests
            params = {"function": "GLOBAL_QUOTE", "symbol": "IBM", "apikey": self.api_key}
            resp = requests.get(self.base_url, params=params, timeout=10)
            return "Global Quote" in resp.json()
        except Exception:
            return False


class MockProvider(DataProvider):
    """Mock data provider for testing and development."""

    name = "mock"

    def __init__(self):
        self._data: dict[str, dict] = {}

    def seed(self, ticker: str, ohlcv: dict = None, realtime: dict = None):
        """Pre-load mock data for a ticker."""
        self._data[ticker] = {"ohlcv": ohlcv, "realtime": realtime}

    def get_ohlcv(self, ticker: str, start: str, end: str) -> dict:
        if ticker in self._data and self._data[ticker].get("ohlcv"):
            return {**self._data[ticker]["ohlcv"], "source": "mock"}
        # Generate synthetic data
        import random
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        days = max(1, (end_dt - start_dt).days)
        price = 100.0
        dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
        for i in range(days):
            d = start_dt + timedelta(days=i)
            if d.weekday() >= 5:
                continue
            o = price
            c = price * (1 + random.gauss(0, 0.02))
            h = max(o, c) * (1 + abs(random.gauss(0, 0.005)))
            l = min(o, c) * (1 - abs(random.gauss(0, 0.005)))
            v = random.randint(1_000_000, 50_000_000)
            dates.append(d.strftime("%Y-%m-%d"))
            opens.append(round(o, 2))
            highs.append(round(h, 2))
            lows.append(round(l, 2))
            closes.append(round(c, 2))
            volumes.append(v)
            price = c
        return {
            "dates": dates, "open": opens, "high": highs,
            "low": lows, "close": closes, "volume": volumes,
            "source": "mock",
        }

    def get_realtime(self, ticker: str) -> dict:
        if ticker in self._data and self._data[ticker].get("realtime"):
            return {**self._data[ticker]["realtime"], "source": "mock"}
        import random
        return {
            "price": round(100 + random.gauss(0, 5), 2),
            "volume": random.randint(100_000, 10_000_000),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "mock",
        }

    def health_check(self) -> bool:
        return True


# Provider registry
_PROVIDER_CLASSES: dict[str, type] = {
    "yahoo": YahooProvider,
    "alpha_vantage": AlphaVantageProvider,
    "mock": MockProvider,
}


class DataRouter:
    """
    Unified market data access with automatic provider fallback.

    Tries each provider in order; returns first successful result.
    """

    def __init__(self, providers: Optional[list[str]] = None, **kwargs):
        if providers is None:
            providers = ["yahoo", "alpha_vantage", "mock"]
        self._provider_names = providers
        self._providers: dict[str, DataProvider] = {}
        for name in providers:
            cls = _PROVIDER_CLASSES.get(name)
            if cls:
                self._providers[name] = cls(**kwargs.get(name, {})) if kwargs.get(name) else cls()
            else:
                logger.warning("Unknown provider: %s (skipped)", name)

    @property
    def provider_order(self) -> list[str]:
        return list(self._providers.keys())

    def add_provider(self, name: str, provider: DataProvider):
        """Register a custom data provider."""
        self._providers[name] = provider
        if name not in self._provider_names:
            self._provider_names.append(name)

    def get_ohlcv(self, ticker: str, start: str, end: str) -> dict:
        """Fetch OHLCV data, falling back through providers on failure."""
        errors = {}
        for name, provider in self._providers.items():
            try:
                result = provider.get_ohlcv(ticker, start, end)
                logger.debug("OHLCV for %s served by %s", ticker, name)
                return result
            except Exception as e:
                errors[name] = str(e)
                logger.info("Provider %s failed for OHLCV(%s): %s", name, ticker, e)
        raise RuntimeError(
            f"All providers failed for OHLCV({ticker}): {errors}"
        )

    def get_realtime(self, ticker: str) -> dict:
        """Fetch realtime quote, falling back through providers on failure."""
        errors = {}
        for name, provider in self._providers.items():
            try:
                result = provider.get_realtime(ticker)
                logger.debug("Realtime for %s served by %s", ticker, name)
                return result
            except Exception as e:
                errors[name] = str(e)
                logger.info("Provider %s failed for realtime(%s): %s", name, ticker, e)
        raise RuntimeError(
            f"All providers failed for realtime({ticker}): {errors}"
        )

    def health_check(self) -> dict:
        """Check health of all registered providers."""
        status = {}
        for name, provider in self._providers.items():
            try:
                status[name] = provider.health_check()
            except Exception:
                status[name] = False
        return status
