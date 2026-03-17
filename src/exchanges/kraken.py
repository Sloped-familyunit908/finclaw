"""
Kraken REST API adapter.
Public: OHLC, ticker, orderbook, trades
Private: balance, orders (nonce + HMAC-SHA512 signing)
"""

import base64
import hashlib
import hmac
import time
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class KrakenAdapter(ExchangeAdapter):
    name = "kraken"
    exchange_type = "crypto"

    BASE_URL = "https://api.kraken.com"

    TIMEFRAME_MAP = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.client = HttpClient(self.BASE_URL)

    def _sign(self, path: str, data: dict) -> dict:
        """Kraken nonce + HMAC-SHA512 signature."""
        nonce = str(int(time.time() * 1000))
        data["nonce"] = nonce
        postdata = urllib.parse.urlencode(data)
        encoded = (nonce + postdata).encode("utf-8")
        message = path.encode("utf-8") + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512,
        )
        return {
            "API-Key": self.api_key,
            "API-Sign": base64.b64encode(signature.digest()).decode("utf-8"),
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _check_result(self, data: dict) -> dict | list:
        """Extract result from Kraken response, raise on error."""
        errors = data.get("error", [])
        if errors:
            raise RuntimeError(f"Kraken API error: {errors}")
        return data.get("result", {})

    # --- Public ---

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        interval = self.TIMEFRAME_MAP.get(timeframe, 1440)
        data = self.client.get("/0/public/OHLC", {"pair": symbol, "interval": interval})
        result = self._check_result(data)
        # Result is {pair_name: [...], last: ...} — grab the first key that's not 'last'
        candles = []
        for key, values in result.items():
            if key == "last":
                continue
            for c in values[-limit:]:
                candles.append({
                    "timestamp": int(c[0]) * 1000,
                    "open": float(c[1]), "high": float(c[2]),
                    "low": float(c[3]), "close": float(c[4]),
                    "volume": float(c[6]),
                })
            break
        return candles

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        data = self.client.get("/0/public/Ticker", {"pair": symbol})
        result = self._check_result(data)
        for pair, t in result.items():
            return {
                "symbol": pair,
                "last": float(t["c"][0]),
                "bid": float(t["b"][0]),
                "ask": float(t["a"][0]),
                "volume": float(t["v"][1]),  # 24h volume
                "timestamp": int(time.time() * 1000),
            }
        return {}

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        data = self.client.get("/0/public/Depth", {"pair": symbol, "count": depth})
        result = self._check_result(data)
        for pair, book in result.items():
            return {
                "bids": [[float(b[0]), float(b[1])] for b in book.get("bids", [])],
                "asks": [[float(a[0]), float(a[1])] for a in book.get("asks", [])],
            }
        return {"bids": [], "asks": []}

    @handle_network_errors
    def get_trades(self, symbol: str, limit: int = 50) -> list[dict]:
        data = self.client.get("/0/public/Trades", {"pair": symbol, "count": limit})
        result = self._check_result(data)
        trades = []
        for key, values in result.items():
            if key == "last":
                continue
            for t in values[-limit:]:
                trades.append({
                    "price": float(t[0]), "volume": float(t[1]),
                    "time": float(t[2]), "side": "buy" if t[3] == "b" else "sell",
                    "type": "market" if t[4] == "m" else "limit",
                })
            break
        return trades

    # --- Private ---

    @handle_network_errors
    def get_balance(self) -> dict:
        path = "/0/private/Balance"
        data = {"nonce": ""}
        headers = self._sign(path, data)
        postdata = urllib.parse.urlencode(data)
        # Use raw request for form-encoded POST
        result = self._check_result(
            self.client.request("POST", path, body=None, headers=headers)
        )
        # Kraken returns {asset: "balance_string"}
        return {
            asset: {"free": float(bal), "locked": 0.0}
            for asset, bal in result.items()
            if float(bal) > 0
        }

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        path = "/0/private/AddOrder"
        data = {
            "pair": symbol,
            "type": side.lower(),  # buy/sell
            "ordertype": type.lower(),  # market/limit
            "volume": str(amount),
        }
        if price is not None and type.lower() == "limit":
            data["price"] = str(price)
        headers = self._sign(path, data)
        result = self._check_result(
            self.client.request("POST", path, body=None, headers=headers)
        )
        return result

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        path = "/0/private/CancelOrder"
        data = {"txid": order_id}
        headers = self._sign(path, data)
        self._check_result(
            self.client.request("POST", path, body=None, headers=headers)
        )
        return True

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        path = "/0/private/OpenPositions"
        data = {}
        headers = self._sign(path, data)
        result = self._check_result(
            self.client.request("POST", path, body=None, headers=headers)
        )
        return [
            {"id": pid, "symbol": p.get("pair", ""), "side": p.get("type", ""),
             "amount": float(p.get("vol", 0)), "cost": float(p.get("cost", 0)),
             "unrealized_pnl": float(p.get("net", 0))}
            for pid, p in result.items()
        ]
