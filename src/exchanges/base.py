"""
Base exchange adapter interface.
All exchange adapters must implement this ABC.
"""

from abc import ABC, abstractmethod
from typing import Any


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
