"""
Binance REST API adapter — spot + futures.
Public: klines, ticker/24hr, depth
Private: account, order, positionRisk (HMAC-SHA256 signed)
"""

import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient, hmac_sha256_sign, timestamp_ms


class BinanceAdapter(ExchangeAdapter):
    name = "binance"
    exchange_type = "crypto"

    SPOT_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"

    TIMEFRAME_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w", "1M": "1M",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.futures = self.config.get("futures", False)
        base = self.FUTURES_URL if self.futures else self.SPOT_URL
        headers = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        self.client = HttpClient(base, headers=headers)

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = timestamp_ms()
        query = urllib.parse.urlencode(params)
        params["signature"] = hmac_sha256_sign(self.api_secret, query)
        return params

    # --- Public ---

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        path = "/fapi/v1/klines" if self.futures else "/api/v3/klines"
        interval = self.TIMEFRAME_MAP.get(timeframe, timeframe)
        data = self.client.get(path, {"symbol": symbol, "interval": interval, "limit": limit})
        return [
            {"timestamp": k[0], "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
            for k in data
        ]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        path = "/fapi/v1/ticker/24hr" if self.futures else "/api/v3/ticker/24hr"
        d = self.client.get(path, {"symbol": symbol})
        return {
            "symbol": d["symbol"], "last": float(d["lastPrice"]),
            "bid": float(d.get("bidPrice", 0)), "ask": float(d.get("askPrice", 0)),
            "volume": float(d["volume"]), "timestamp": d.get("closeTime", 0),
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        path = "/fapi/v1/depth" if self.futures else "/api/v3/depth"
        d = self.client.get(path, {"symbol": symbol, "limit": depth})
        return {
            "bids": [[float(p), float(q)] for p, q in d["bids"]],
            "asks": [[float(p), float(q)] for p, q in d["asks"]],
        }

    # --- Private (requires API key + secret) ---

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        path = "/fapi/v1/order" if self.futures else "/api/v3/order"
        params = {"symbol": symbol, "side": side.upper(), "type": type.upper(), "quantity": amount}
        if price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"
        return self.client.post(path, params=self._sign(params))

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        path = "/fapi/v1/order" if self.futures else "/api/v3/order"
        params = {"orderId": order_id}
        self.client.delete(path, params=self._sign(params))
        return True

    @handle_network_errors
    def get_balance(self) -> dict:
        if self.futures:
            data = self.client.get("/fapi/v2/balance", self._sign({}))
            return {b["asset"]: {"free": float(b["availableBalance"]), "locked": float(b["balance"]) - float(b["availableBalance"])} for b in data}
        data = self.client.get("/api/v3/account", self._sign({}))
        return {b["asset"]: {"free": float(b["free"]), "locked": float(b["locked"])} for b in data.get("balances", []) if float(b["free"]) + float(b["locked"]) > 0}

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        if not self.futures:
            return []
        data = self.client.get("/fapi/v2/positionRisk", self._sign({}))
        return [{"symbol": p["symbol"], "side": "long" if float(p["positionAmt"]) > 0 else "short",
                 "amount": abs(float(p["positionAmt"])), "entry_price": float(p["entryPrice"]),
                 "unrealized_pnl": float(p["unRealizedProfit"])}
                for p in data if float(p["positionAmt"]) != 0]
