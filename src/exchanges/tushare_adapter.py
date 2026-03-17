"""
Tushare adapter for A股 (China A-shares).
Requires a Tushare Pro token (free registration).
"""

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class TushareAdapter(ExchangeAdapter):
    name = "tushare"
    exchange_type = "stock_cn"
    BASE_URL = "http://api.tushare.pro"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.token = self.config.get("token", "")
        self.client = HttpClient(self.BASE_URL, headers={"Content-Type": "application/json"})

    def _api(self, api_name: str, params: dict | None = None, fields: str = "") -> list[list]:
        body = {"api_name": api_name, "token": self.token, "params": params or {}, "fields": fields}
        data = self.client.post("", body=body)
        if data.get("code") != 0:
            raise RuntimeError(f"Tushare API error: {data.get('msg', 'unknown')}")
        result = data.get("data", {})
        columns = result.get("fields", [])
        items = result.get("items", [])
        return [dict(zip(columns, row)) for row in items]

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        # Tushare uses ts_code format: 000001.SZ
        rows = self._api("daily", {"ts_code": symbol, "limit": limit},
                         fields="trade_date,open,high,low,close,vol")
        return [
            {"timestamp": r["trade_date"], "open": float(r["open"]), "high": float(r["high"]),
             "low": float(r["low"]), "close": float(r["close"]), "volume": float(r["vol"])}
            for r in reversed(rows)  # Tushare returns newest first
        ]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        rows = self._api("daily", {"ts_code": symbol, "limit": 1},
                         fields="ts_code,trade_date,close,vol")
        if not rows:
            return {"symbol": symbol, "last": 0, "bid": 0, "ask": 0, "volume": 0, "timestamp": ""}
        r = rows[0]
        return {
            "symbol": r["ts_code"], "last": float(r["close"]),
            "bid": float(r["close"]), "ask": float(r["close"]),
            "volume": float(r["vol"]), "timestamp": r["trade_date"],
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        return {"bids": [], "asks": []}

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("Tushare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Tushare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_balance(self) -> dict:
        raise NotImplementedError("Tushare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        raise NotImplementedError("Tushare is a data-only adapter; trading not supported.")
