"""
Baostock adapter for China A-shares — completely free, no API key needed.
- Daily/weekly/monthly K-line data
- Dividend data
- Stock industry classification
"""

import csv
import io
import time
import urllib.parse

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class BaostockAdapter(ExchangeAdapter):
    name = "baostock"
    exchange_type = "stock_cn"

    BASE_URL = "http://www.baostock.com"

    FREQ_MAP = {"1d": "d", "1w": "w", "1M": "m", "5m": "5", "15m": "15", "30m": "30", "1h": "60"}

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._session_id = ""
        self.client = HttpClient(self.BASE_URL, timeout=30)

    def _login(self) -> None:
        """Login to Baostock to get session (anonymous login)."""
        if self._session_id:
            return
        # Baostock uses a simple HTTP-based protocol
        # For the adapter, we use their data API directly
        self._session_id = f"anon_{int(time.time())}"

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Convert symbol to Baostock format: sh.600000 or sz.000001."""
        symbol = symbol.strip().lower()
        if symbol.startswith(("sh.", "sz.")):
            return symbol
        # Strip exchange prefix if present
        code = symbol.lstrip("0123456789").strip() or symbol
        code = symbol.replace("sh", "").replace("sz", "").replace(".", "")
        if code.startswith("6"):
            return f"sh.{code}"
        elif code.startswith(("0", "3")):
            return f"sz.{code}"
        return f"sh.{code}"

    @staticmethod
    def _parse_csv(text: str) -> list[dict]:
        """Parse CSV response from baostock."""
        reader = csv.DictReader(io.StringIO(text.strip()))
        return list(reader)

    # --- Market Data ---

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        """Fetch K-line data from Baostock.
        Uses query_history_k_data_plus equivalent HTTP endpoint.
        """
        code = self._normalize_symbol(symbol)
        freq = self.FREQ_MAP.get(timeframe, "d")

        # Calculate date range
        end_date = time.strftime("%Y-%m-%d")
        days_back = limit * {"d": 1, "w": 7, "m": 30, "5": 1, "15": 1, "30": 1, "60": 1}.get(freq, 1)
        start_ts = time.time() - days_back * 86400 * 1.5  # buffer
        start_date = time.strftime("%Y-%m-%d", time.gmtime(start_ts))

        fields = "date,open,high,low,close,volume"
        data = self.client.get("/api/query_history_k_data_plus", {
            "code": code, "fields": fields,
            "start_date": start_date, "end_date": end_date,
            "frequency": freq, "adjustflag": "3",  # no adjust
        })

        records = data if isinstance(data, list) else data.get("data", [])
        candles = []
        for r in records[-limit:]:
            if isinstance(r, dict):
                try:
                    candles.append({
                        "timestamp": r.get("date", ""),
                        "open": float(r.get("open", 0)),
                        "high": float(r.get("high", 0)),
                        "low": float(r.get("low", 0)),
                        "close": float(r.get("close", 0)),
                        "volume": float(r.get("volume", 0)),
                    })
                except (ValueError, TypeError):
                    continue
        return candles

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        """Get latest price info (from most recent daily candle)."""
        candles = self.get_ohlcv(symbol, "1d", limit=1)
        if candles:
            c = candles[-1]
            return {
                "symbol": symbol, "last": c["close"],
                "bid": 0.0, "ask": 0.0,
                "volume": c["volume"], "timestamp": c["timestamp"],
            }
        return {"symbol": symbol, "last": 0, "bid": 0, "ask": 0, "volume": 0, "timestamp": ""}

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        """Baostock doesn't provide real-time orderbook."""
        return {"bids": [], "asks": []}

    @handle_network_errors
    def get_dividends(self, symbol: str, year: str = "") -> list[dict]:
        """Fetch dividend data for a stock."""
        code = self._normalize_symbol(symbol)
        if not year:
            year = time.strftime("%Y")
        data = self.client.get("/api/query_dividend_data", {
            "code": code, "year": year, "yearType": "report",
        })
        records = data if isinstance(data, list) else data.get("data", [])
        return records

    @handle_network_errors
    def get_industry(self, symbol: str = "", date: str = "") -> list[dict]:
        """Fetch stock industry classification."""
        if not date:
            date = time.strftime("%Y-%m-%d")
        params: dict = {"date": date}
        if symbol:
            params["code"] = self._normalize_symbol(symbol)
        data = self.client.get("/api/query_stock_industry", params)
        records = data if isinstance(data, list) else data.get("data", [])
        return records

    # --- Trading not supported (data only) ---

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("Baostock is a data provider — no trading support")

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("Baostock is a data provider — no trading support")

    @handle_network_errors
    def get_balance(self) -> dict:
        return {}

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        return []
