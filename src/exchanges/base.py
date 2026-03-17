"""
Base exchange adapter interface.
All exchange adapters must implement this ABC.
"""

from abc import ABC, abstractmethod
from functools import wraps
from typing import Any

from src.exchanges.http_client import ExchangeAPIError, ExchangeConnectionError


class ExchangeError(Exception):
    """User-friendly error raised by exchange adapters on network/API failures."""

    def __init__(self, exchange: str, operation: str, message: str, original: Exception | None = None):
        self.exchange = exchange
        self.operation = operation
        self.original = original
        super().__init__(f"[{exchange}] {operation} failed: {message}")


def handle_network_errors(func):
    """Decorator that catches network/HTTP errors and re-raises as user-friendly ExchangeError."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ExchangeAPIError as e:
            raise ExchangeError(
                self.name, func.__name__,
                f"HTTP {e.status} error — {e.body[:200]}",
                original=e,
            ) from e
        except ExchangeConnectionError as e:
            raise ExchangeError(
                self.name, func.__name__,
                f"Connection failed — {e.reason}. Check your network or try again later.",
                original=e,
            ) from e
        except TimeoutError as e:
            raise ExchangeError(
                self.name, func.__name__,
                "Request timed out. The exchange may be slow or unreachable.",
                original=e,
            ) from e
        except (OSError, ConnectionError) as e:
            raise ExchangeError(
                self.name, func.__name__,
                f"Network error — {e}",
                original=e,
            ) from e
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ExchangeError(
                self.name, func.__name__,
                f"Unexpected response format — {type(e).__name__}: {e}",
                original=e,
            ) from e

    return wrapper


class ExchangeAdapter(ABC):
    """Abstract base class for all exchange/data adapters."""

    exchange_type: str = "unknown"  # 'crypto', 'stock_us', 'stock_cn'
    name: str = "base"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        """Return OHLCV candles as list of dicts with keys: timestamp, open, high, low, close, volume."""
        ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> dict:
        """Return ticker with keys: symbol, last, bid, ask, volume, timestamp."""
        ...

    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        """Return orderbook with keys: bids (list of [price, qty]), asks (list of [price, qty])."""
        ...

    @abstractmethod
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        """Place an order. Returns order info dict."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True on success."""
        ...

    @abstractmethod
    def get_balance(self) -> dict:
        """Return account balances as {asset: {free: float, locked: float}}."""
        ...

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """Return open positions."""
        ...
