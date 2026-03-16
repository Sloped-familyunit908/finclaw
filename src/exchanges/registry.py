"""
Exchange Registry — central access point for all exchange adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.exchanges.base import ExchangeAdapter


class ExchangeRegistry:
    """Registry for exchange adapter classes."""

    _exchanges: dict[str, type] = {}
    _type_map: dict[str, str] = {}  # name -> exchange_type

    @classmethod
    def register(cls, name: str, adapter_class: type, exchange_type: str | None = None) -> None:
        cls._exchanges[name.lower()] = adapter_class
        if exchange_type:
            cls._type_map[name.lower()] = exchange_type
        elif hasattr(adapter_class, "exchange_type"):
            cls._type_map[name.lower()] = adapter_class.exchange_type

    @classmethod
    def get(cls, name: str, config: dict | None = None) -> "ExchangeAdapter":
        name = name.lower()
        if name not in cls._exchanges:
            raise KeyError(f"Exchange '{name}' not registered. Available: {cls.list_exchanges()}")
        return cls._exchanges[name](config)

    @classmethod
    def list_exchanges(cls) -> list[str]:
        return sorted(cls._exchanges.keys())

    @classmethod
    def list_by_type(cls, exchange_type: str) -> list[str]:
        return sorted(n for n, t in cls._type_map.items() if t == exchange_type)

    @classmethod
    def clear(cls) -> None:
        cls._exchanges.clear()
        cls._type_map.clear()


def _register_all() -> None:
    """Register all built-in adapters."""
    from src.exchanges.binance import BinanceAdapter
    from src.exchanges.okx import OKXAdapter
    from src.exchanges.bybit import BybitAdapter
    from src.exchanges.yahoo_finance import YahooFinanceAdapter
    from src.exchanges.alpha_vantage import AlphaVantageAdapter
    from src.exchanges.tushare_adapter import TushareAdapter
    from src.exchanges.akshare_adapter import AKShareAdapter

    ExchangeRegistry.register("binance", BinanceAdapter, "crypto")
    ExchangeRegistry.register("okx", OKXAdapter, "crypto")
    ExchangeRegistry.register("bybit", BybitAdapter, "crypto")
    ExchangeRegistry.register("yahoo", YahooFinanceAdapter, "stock_us")
    ExchangeRegistry.register("alpha_vantage", AlphaVantageAdapter, "stock_us")
    ExchangeRegistry.register("tushare", TushareAdapter, "stock_cn")
    ExchangeRegistry.register("akshare", AKShareAdapter, "stock_cn")


_register_all()
