"""
OKX REST API adapter.
Public: candles, ticker, orderbook
Private: account, orders (HMAC-SHA256 + base64 signing)
"""

import base64
import datetime
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient, timestamp_ms
import hashlib
import hmac


class OKXAdapter(ExchangeAdapter):
    name = "okx"
    exchange_type = "crypto"
    BASE_URL = "https://www.okx.com"

    TIMEFRAME_MAP = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W", "1M": "1M",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.passphrase = self.config.get("passphrase", "")
        self.client = HttpClient(self.BASE_URL)

    def _sign_headers(self, method: str, path: str, body: str = "") -> dict:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        msg = ts + method.upper() + path + body
        sig = base64.b64encode(hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).digest()).decode()
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
        }

    def _inst_id(self, symbol: str) -> str:
        """Convert BTCUSDT -> BTC-USDT if needed."""
        if "-" in symbol:
            return symbol
        # Try common patterns
        for quote in ("USDT", "USDC", "USD", "BTC", "ETH"):
            if symbol.endswith(quote):
                return symbol[:-len(quote)] + "-" + quote
        return symbol

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        bar = self.TIMEFRAME_MAP.get(timeframe, timeframe)
        data = self.client.get("/api/v5/market/candles", {"instId": self._inst_id(symbol), "bar": bar, "limit": str(limit)})
        candles = data.get("data", [])
        return [
            {"timestamp": int(c[0]), "open": float(c[1]), "high": float(c[2]),
             "low": float(c[3]), "close": float(c[4]), "volume": float(c[5])}
            for c in candles
        ]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        data = self.client.get("/api/v5/market/ticker", {"instId": self._inst_id(symbol)})
        d = data["data"][0]
        return {
            "symbol": d["instId"], "last": float(d["last"]),
            "bid": float(d["bidPx"]), "ask": float(d["askPx"]),
            "volume": float(d["vol24h"]), "timestamp": int(d["ts"]),
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        data = self.client.get("/api/v5/market/books", {"instId": self._inst_id(symbol), "sz": str(depth)})
        book = data["data"][0]
        return {
            "bids": [[float(b[0]), float(b[1])] for b in book["bids"]],
            "asks": [[float(a[0]), float(a[1])] for a in book["asks"]],
        }

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        body = {"instId": self._inst_id(symbol), "tdMode": "cash", "side": side.lower(),
                "ordType": "limit" if price else "market", "sz": str(amount)}
        if price:
            body["px"] = str(price)
        import json
        body_str = json.dumps(body)
        headers = self._sign_headers("POST", "/api/v5/trade/order", body_str)
        return self.client.post("/api/v5/trade/order", body=body, headers=headers)

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        import json
        body = {"ordId": order_id}
        body_str = json.dumps(body)
        headers = self._sign_headers("POST", "/api/v5/trade/cancel-order", body_str)
        self.client.post("/api/v5/trade/cancel-order", body=body, headers=headers)
        return True

    @handle_network_errors
    def get_balance(self) -> dict:
        headers = self._sign_headers("GET", "/api/v5/account/balance")
        data = self.client.get("/api/v5/account/balance", headers=headers)
        result = {}
        for detail in data.get("data", [{}])[0].get("details", []):
            result[detail["ccy"]] = {"free": float(detail["availBal"]), "locked": float(detail["frozenBal"])}
        return result

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        headers = self._sign_headers("GET", "/api/v5/account/positions")
        data = self.client.get("/api/v5/account/positions", headers=headers)
        return [
            {"symbol": p["instId"], "side": p["posSide"], "amount": float(p["pos"]),
             "entry_price": float(p.get("avgPx", 0)), "unrealized_pnl": float(p.get("upl", 0))}
            for p in data.get("data", []) if float(p.get("pos", 0)) != 0
        ]
