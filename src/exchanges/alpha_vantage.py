"""
Alpha Vantage adapter — free tier: 25 requests/day.
Historical OHLCV (daily/weekly/monthly) and real-time quotes.
"""

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class AlphaVantageAdapter(ExchangeAdapter):
    name = "alpha_vantage"
    exchange_type = "stock_us"
    BASE_URL = "https://www.alphavantage.co"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "demo")
        self.client = HttpClient(self.BASE_URL)

    def _query(self, **params) -> dict:
        params["apikey"] = self.api_key
        return self.client.get("/query", params)

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        func_map = {"1d": "TIME_SERIES_DAILY", "1w": "TIME_SERIES_WEEKLY", "1M": "TIME_SERIES_MONTHLY"}
        function = func_map.get(timeframe, "TIME_SERIES_DAILY")
        data = self._query(function=function, symbol=symbol, outputsize="compact")

        # Find the time series key
        ts_key = None
        for k in data:
            if "Time Series" in k:
                ts_key = k
                break
        if not ts_key:
            return []

        candles = []
        for date_str, values in sorted(data[ts_key].items()):
            candles.append({
                "timestamp": date_str,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": float(values["5. volume"]),
            })
        return candles[-limit:]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        data = self._query(function="GLOBAL_QUOTE", symbol=symbol)
        q = data.get("Global Quote", {})
        return {
            "symbol": q.get("01. symbol", symbol),
            "last": float(q.get("05. price", 0)),
            "bid": float(q.get("05. price", 0)),
            "ask": float(q.get("05. price", 0)),
            "volume": float(q.get("06. volume", 0)),
            "timestamp": q.get("07. latest trading day", ""),
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        return {"bids": [], "asks": []}

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("Alpha Vantage is a data-only adapter; trading not supported.")

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Alpha Vantage is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_balance(self) -> dict:
        raise NotImplementedError("Alpha Vantage is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        raise NotImplementedError("Alpha Vantage is a data-only adapter; trading not supported.")
