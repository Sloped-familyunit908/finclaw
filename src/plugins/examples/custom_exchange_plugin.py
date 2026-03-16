"""
Custom Exchange Plugin Example
Demonstrates how to add a third-party exchange via the plugin system.
"""

from src.plugins.exchange_plugin import ExchangePlugin


class DemoExchange(ExchangePlugin):
    name = "demo_exchange"
    version = "1.0.0"
    description = "Demo exchange adapter for testing"
    exchange_type = "demo"

    def __init__(self, config=None):
        super().__init__(config)
        self._balances = {"USDT": {"free": 10000.0, "locked": 0.0}}
        self._orders = []

    def get_ohlcv(self, symbol, timeframe="1d", limit=100):
        import random
        base = 100.0
        candles = []
        for i in range(limit):
            o = base + random.uniform(-2, 2)
            h = o + random.uniform(0, 3)
            l = o - random.uniform(0, 3)
            c = (o + h + l) / 3
            candles.append({
                "timestamp": 1700000000 + i * 86400,
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
                "volume": round(random.uniform(1000, 10000), 2),
            })
            base = c
        return candles

    def get_ticker(self, symbol):
        return {
            "symbol": symbol,
            "last": 100.0,
            "bid": 99.9,
            "ask": 100.1,
            "volume": 5000.0,
            "timestamp": 1700000000,
        }

    def get_orderbook(self, symbol, depth=20):
        bids = [[100.0 - i * 0.1, 10.0] for i in range(depth)]
        asks = [[100.0 + i * 0.1, 10.0] for i in range(depth)]
        return {"bids": bids, "asks": asks}

    def place_order(self, symbol, side, type, amount, price=None):
        order = {
            "id": f"demo-{len(self._orders)}",
            "symbol": symbol,
            "side": side,
            "type": type,
            "amount": amount,
            "price": price or 100.0,
            "status": "filled",
        }
        self._orders.append(order)
        return order

    def cancel_order(self, order_id):
        return True

    def get_balance(self):
        return self._balances

    def get_positions(self):
        return []
