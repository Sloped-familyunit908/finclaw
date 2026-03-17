"""
Bybit REST API v5 adapter.
Public: kline, tickers, orderbook
Private: account, order (HMAC-SHA256 signing)
"""

import json
import time
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient, hmac_sha256_sign, timestamp_ms


class BybitAdapter(ExchangeAdapter):
    name = "bybit"
    exchange_type = "crypto"
    BASE_URL = "https://api.bybit.com"

    TIMEFRAME_MAP = {
        "1m": "1", "5m": "5", "15m": "15", "30m": "30",
        "1h": "60", "4h": "240", "1d": "D", "1w": "W", "1M": "M",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.client = HttpClient(self.BASE_URL)

    def _sign_headers(self, params_str: str) -> dict:
        ts = str(timestamp_ms())
        recv_window = "5000"
        sign_str = ts + self.api_key + recv_window + params_str
        sig = hmac_sha256_sign(self.api_secret, sign_str)
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": recv_window,
        }

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        interval = self.TIMEFRAME_MAP.get(timeframe, timeframe)
        data = self.client.get("/v5/market/kline", {
            "category": "linear", "symbol": symbol, "interval": interval, "limit": limit,
        })
        return [
            {"timestamp": int(k[0]), "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
            for k in data.get("result", {}).get("list", [])
        ]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        data = self.client.get("/v5/market/tickers", {"category": "linear", "symbol": symbol})
        t = data["result"]["list"][0]
        return {
            "symbol": t["symbol"], "last": float(t["lastPrice"]),
            "bid": float(t["bid1Price"]), "ask": float(t["ask1Price"]),
            "volume": float(t["volume24h"]), "timestamp": int(data.get("time", 0)),
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        data = self.client.get("/v5/market/orderbook", {"category": "linear", "symbol": symbol, "limit": depth})
        book = data["result"]
        return {
            "bids": [[float(b[0]), float(b[1])] for b in book["b"]],
            "asks": [[float(a[0]), float(a[1])] for a in book["a"]],
        }

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        body = {"category": "linear", "symbol": symbol, "side": side.capitalize(),
                "orderType": type.capitalize(), "qty": str(amount)}
        if price is not None:
            body["price"] = str(price)
        body_str = json.dumps(body)
        headers = self._sign_headers(body_str)
        return self.client.post("/v5/order/create", body=body, headers=headers)

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        body = {"category": "linear", "orderId": order_id}
        body_str = json.dumps(body)
        headers = self._sign_headers(body_str)
        self.client.post("/v5/order/cancel", body=body, headers=headers)
        return True

    @handle_network_errors
    def get_balance(self) -> dict:
        params = urllib.parse.urlencode({"accountType": "UNIFIED"})
        headers = self._sign_headers(params)
        data = self.client.get("/v5/account/wallet-balance", {"accountType": "UNIFIED"}, headers=headers)
        result = {}
        for coin in data.get("result", {}).get("list", [{}])[0].get("coin", []):
            result[coin["coin"]] = {"free": float(coin["availableToWithdraw"]), "locked": float(coin["locked"])}
        return result

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        params = urllib.parse.urlencode({"category": "linear"})
        headers = self._sign_headers(params)
        data = self.client.get("/v5/position/list", {"category": "linear"}, headers=headers)
        return [
            {"symbol": p["symbol"], "side": p["side"].lower(), "amount": float(p["size"]),
             "entry_price": float(p["avgPrice"]), "unrealized_pnl": float(p["unrealisedPnl"])}
            for p in data.get("result", {}).get("list", []) if float(p.get("size", 0)) != 0
        ]
