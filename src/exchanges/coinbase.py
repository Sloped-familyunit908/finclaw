"""
Coinbase Advanced Trade API adapter.
Public: candles, ticker, orderbook, trades
Private: accounts, orders, fills (JWT auth)
"""

import hashlib
import hmac
import json
import time
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient, ExchangeAPIError


class CoinbaseAdapter(ExchangeAdapter):
    name = "coinbase"
    exchange_type = "crypto"

    BASE_URL = "https://api.coinbase.com"

    TIMEFRAME_MAP = {
        "1m": "ONE_MINUTE", "5m": "FIVE_MINUTE", "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE", "1h": "ONE_HOUR", "2h": "TWO_HOUR",
        "6h": "SIX_HOUR", "1d": "ONE_DAY",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.client = HttpClient(self.BASE_URL)

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict:
        """Generate JWT-style HMAC auth headers for Coinbase Advanced Trade."""
        ts = str(int(time.time()))
        message = ts + method.upper() + path + body
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json",
        }

    # --- Public ---

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        product_id = self._to_product_id(symbol)
        granularity = self.TIMEFRAME_MAP.get(timeframe, "ONE_DAY")
        end = int(time.time())
        start = end - limit * self._granularity_seconds(timeframe)
        path = f"/api/v3/brokerage/market/products/{product_id}/candles"
        data = self.client.get(path, {
            "start": str(start), "end": str(end), "granularity": granularity,
        })
        candles = data.get("candles", [])
        return [
            {"timestamp": int(c["start"]) * 1000, "open": float(c["open"]),
             "high": float(c["high"]), "low": float(c["low"]),
             "close": float(c["close"]), "volume": float(c["volume"])}
            for c in candles
        ]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        product_id = self._to_product_id(symbol)
        d = self.client.get(f"/api/v3/brokerage/market/products/{product_id}")
        return {
            "symbol": product_id,
            "last": float(d.get("price", 0)),
            "bid": float(d.get("bid", 0)),
            "ask": float(d.get("ask", 0)),
            "volume": float(d.get("volume_24h", 0)),
            "timestamp": int(time.time() * 1000),
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        product_id = self._to_product_id(symbol)
        d = self.client.get(
            f"/api/v3/brokerage/market/products/{product_id}/book",
            {"limit": depth},
        )
        pricebook = d.get("pricebook", {})
        return {
            "bids": [[float(b["price"]), float(b["size"])] for b in pricebook.get("bids", [])],
            "asks": [[float(a["price"]), float(a["size"])] for a in pricebook.get("asks", [])],
        }

    @handle_network_errors
    def get_trades(self, symbol: str, limit: int = 50) -> list[dict]:
        product_id = self._to_product_id(symbol)
        d = self.client.get(
            f"/api/v3/brokerage/market/products/{product_id}/ticker",
            {"limit": limit},
        )
        return [
            {"price": float(t["price"]), "size": float(t["size"]),
             "side": t.get("side", ""), "time": t.get("time", "")}
            for t in d.get("trades", [])
        ]

    # --- Private ---

    @handle_network_errors
    def get_balance(self) -> dict:
        path = "/api/v3/brokerage/accounts"
        data = self.client.get(path, headers=self._auth_headers("GET", path))
        result = {}
        for acct in data.get("accounts", []):
            bal = acct.get("available_balance", {})
            hold = acct.get("hold", {})
            currency = bal.get("currency", acct.get("currency", ""))
            free = float(bal.get("value", 0))
            locked = float(hold.get("value", 0)) if hold else 0.0
            if free + locked > 0:
                result[currency] = {"free": free, "locked": locked}
        return result

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        path = "/api/v3/brokerage/orders"
        product_id = self._to_product_id(symbol)
        order_config = {}
        if type.upper() == "MARKET":
            order_config = {"market_market_ioc": {"base_size": str(amount)}}
        else:
            order_config = {"limit_limit_gtc": {"base_size": str(amount), "limit_price": str(price or 0)}}

        body = {
            "client_order_id": str(int(time.time() * 1000)),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": order_config,
        }
        body_str = json.dumps(body)
        return self.client.post(path, body=body, headers=self._auth_headers("POST", path, body_str))

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        path = "/api/v3/brokerage/orders/batch_cancel"
        body = {"order_ids": [order_id]}
        body_str = json.dumps(body)
        self.client.post(path, body=body, headers=self._auth_headers("POST", path, body_str))
        return True

    @handle_network_errors
    def get_fills(self, symbol: str | None = None, limit: int = 50) -> list[dict]:
        path = "/api/v3/brokerage/orders/historical/fills"
        params: dict = {"limit": limit}
        if symbol:
            params["product_id"] = self._to_product_id(symbol)
        return self.client.get(path, params=params, headers=self._auth_headers("GET", path))

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        return []  # Coinbase spot — no positions concept

    # --- Helpers ---

    @staticmethod
    def _to_product_id(symbol: str) -> str:
        if "-" in symbol:
            return symbol.upper()
        # BTCUSD -> BTC-USD, BTCUSDT -> BTC-USDT
        for quote in ("USDT", "USD", "EUR", "GBP", "BTC", "ETH"):
            if symbol.upper().endswith(quote):
                base = symbol[:len(symbol) - len(quote)]
                return f"{base.upper()}-{quote}"
        return symbol.upper()

    @staticmethod
    def _granularity_seconds(timeframe: str) -> int:
        mapping = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800,
                   "1h": 3600, "2h": 7200, "6h": 21600, "1d": 86400}
        return mapping.get(timeframe, 86400)
