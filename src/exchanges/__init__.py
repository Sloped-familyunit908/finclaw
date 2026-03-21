"""
FinClaw Exchange Adapters — Real market data from crypto, US stocks, and China markets.
"""

from src.exchanges.registry import ExchangeRegistry
from src.exchanges.base import ExchangeAdapter, ExchangeError, handle_network_errors
from src.exchanges.http_client import ExchangeRateLimitError
from src.exchanges.ws_client import WebSocketClient
from src.exchanges.binance_ws import BinanceWebSocket
from src.exchanges.okx_ws import OKXWebSocket
from src.exchanges.bybit_ws import BybitWebSocket
from src.exchanges.data_aggregator import DataAggregator

__all__ = [
    "ExchangeRegistry", "ExchangeAdapter", "ExchangeError", "ExchangeRateLimitError",
    "handle_network_errors",
    "WebSocketClient", "BinanceWebSocket", "OKXWebSocket", "BybitWebSocket",
    "DataAggregator",
]
