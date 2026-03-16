"""
Alpaca Trading API adapter — FREE paper + live trading for US stocks.
Market data: bars, quotes, trades
Trading: orders, positions, account
Paper trading mode built-in.
"""

import json
import time

from src.exchanges.base import ExchangeAdapter
from src.exchanges.http_client import HttpClient


class AlpacaAdapter(ExchangeAdapter):
    name = "alpaca"
    exchange_type = "stock_us"

    LIVE_URL = "https://api.alpaca.markets"
    PAPER_URL = "https://paper-api.alpaca.markets"
    DATA_URL = "https://data.alpaca.markets"

    TIMEFRAME_MAP = {
        "1m": "1Min", "5m": "5Min", "15m": "15Min", "30m": "30Min",
        "1h": "1Hour", "4h": "4Hour", "1d": "1Day", "1w": "1Week", "1M": "1Month",
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.api_secret = self.config.get("api_secret", "")
        self.paper = self.config.get("paper", True)
        trade_base = self.PAPER_URL if self.paper else self.LIVE_URL
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }
        self.trade_client = HttpClient(trade_base, headers=headers)
        self.data_client = HttpClient(self.DATA_URL, headers=headers)

    # --- Market Data ---

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        tf = self.TIMEFRAME_MAP.get(timeframe, "1Day")
        data = self.data_client.get(f"/v2/stocks/{symbol.upper()}/bars", {
            "timeframe": tf, "limit": limit, "adjustment": "split",
        })
        bars = data.get("bars", [])
        return [
            {"timestamp": b["t"], "open": float(b["o"]), "high": float(b["h"]),
             "low": float(b["l"]), "close": float(b["c"]), "volume": int(b["v"])}
            for b in bars
        ]

    def get_ticker(self, symbol: str) -> dict:
        d = self.data_client.get(f"/v2/stocks/{symbol.upper()}/snapshot")
        latest = d.get("latestTrade", {})
        quote = d.get("latestQuote", {})
        daily = d.get("dailyBar", {})
        return {
            "symbol": symbol.upper(),
            "last": float(latest.get("p", 0)),
            "bid": float(quote.get("bp", 0)),
            "ask": float(quote.get("ap", 0)),
            "volume": int(daily.get("v", 0)),
            "timestamp": latest.get("t", ""),
        }

    def get_quotes(self, symbol: str, limit: int = 50) -> list[dict]:
        data = self.data_client.get(f"/v2/stocks/{symbol.upper()}/quotes", {"limit": limit})
        return [
            {"bid": float(q["bp"]), "ask": float(q["ap"]),
             "bid_size": int(q["bs"]), "ask_size": int(q["as"]),
             "timestamp": q["t"]}
            for q in data.get("quotes", [])
        ]

    def get_trades_history(self, symbol: str, limit: int = 50) -> list[dict]:
        data = self.data_client.get(f"/v2/stocks/{symbol.upper()}/trades", {"limit": limit})
        return [
            {"price": float(t["p"]), "size": int(t["s"]),
             "timestamp": t["t"], "exchange": t.get("x", "")}
            for t in data.get("trades", [])
        ]

    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        # Alpaca doesn't have a traditional orderbook endpoint — use latest quote
        d = self.data_client.get(f"/v2/stocks/{symbol.upper()}/snapshot")
        q = d.get("latestQuote", {})
        return {
            "bids": [[float(q.get("bp", 0)), int(q.get("bs", 0))]],
            "asks": [[float(q.get("ap", 0)), int(q.get("as", 0))]],
        }

    # --- Trading ---

    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        body: dict = {
            "symbol": symbol.upper(),
            "qty": str(amount),
            "side": side.lower(),
            "type": type.lower(),
            "time_in_force": "gtc" if type.lower() == "limit" else "day",
        }
        if price is not None and type.lower() == "limit":
            body["limit_price"] = str(price)
        return self.trade_client.post("/v2/orders", body=body)

    def cancel_order(self, order_id: str) -> bool:
        self.trade_client.delete(f"/v2/orders/{order_id}")
        return True

    def get_balance(self) -> dict:
        acct = self.trade_client.get("/v2/account")
        return {
            "USD": {
                "free": float(acct.get("buying_power", 0)),
                "locked": float(acct.get("portfolio_value", 0)) - float(acct.get("buying_power", 0)),
            },
            "_account": {
                "equity": float(acct.get("equity", 0)),
                "cash": float(acct.get("cash", 0)),
                "buying_power": float(acct.get("buying_power", 0)),
                "portfolio_value": float(acct.get("portfolio_value", 0)),
            },
        }

    def get_positions(self) -> list[dict]:
        data = self.trade_client.get("/v2/positions")
        return [
            {"symbol": p["symbol"], "side": p["side"],
             "amount": float(p["qty"]), "entry_price": float(p["avg_entry_price"]),
             "current_price": float(p["current_price"]),
             "unrealized_pnl": float(p["unrealized_pl"]),
             "market_value": float(p["market_value"])}
            for p in data
        ]

    def get_orders(self, status: str = "open", limit: int = 50) -> list[dict]:
        data = self.trade_client.get("/v2/orders", {"status": status, "limit": limit})
        return [
            {"id": o["id"], "symbol": o["symbol"], "side": o["side"],
             "type": o["type"], "qty": o["qty"], "filled_qty": o.get("filled_qty", "0"),
             "status": o["status"], "created_at": o["created_at"]}
            for o in data
        ]

    def get_account(self) -> dict:
        return self.trade_client.get("/v2/account")
