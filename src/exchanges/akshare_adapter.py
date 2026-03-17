"""
AKShare adapter — free, no API key needed!
Supports A股, 港股, 期货, 基金, and macro economic data.
Uses AKShare's HTTP API endpoints.
"""

from src.exchanges.base import ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import HttpClient


class AKShareAdapter(ExchangeAdapter):
    name = "akshare"
    exchange_type = "stock_cn"
    # AKShare is a Python library, but we use its underlying data sources directly
    # via sina/eastmoney APIs for zero-dependency operation.
    SINA_HQ_URL = "https://hq.sinajs.cn"
    EASTMONEY_URL = "https://push2his.eastmoney.com"

    MARKET_MAP = {
        "SH": "1", "SZ": "0", "BJ": "0",  # eastmoney secid prefix
    }

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.sina_client = HttpClient(self.SINA_HQ_URL, headers={
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        })
        self.em_client = HttpClient(self.EASTMONEY_URL, headers={
            "User-Agent": "Mozilla/5.0",
        })

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """Parse '000001.SZ' -> ('000001', 'SZ') or '600000' -> ('600000', 'SH')."""
        if "." in symbol:
            code, market = symbol.split(".", 1)
            return code, market.upper()
        # Guess market from code prefix
        if symbol.startswith("6") or symbol.startswith("9"):
            return symbol, "SH"
        return symbol, "SZ"

    def _sina_symbol(self, code: str, market: str) -> str:
        return f"{'sh' if market == 'SH' else 'sz'}{code}"

    @handle_network_errors
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        code, market = self._parse_symbol(symbol)
        secid = f"{self.MARKET_MAP.get(market, '0')}.{code}"
        klt_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "1d": "101", "1w": "102", "1M": "103"}
        klt = klt_map.get(timeframe, "101")
        data = self.em_client.get("/api/qt/stock/kline/get", {
            "secid": secid, "fields1": "f1,f2,f3", "fields2": "f51,f52,f53,f54,f55,f56",
            "klt": klt, "fqt": "1", "lmt": str(limit), "end": "20990101",
        })
        klines = data.get("data", {})
        if not klines:
            return []
        candles = []
        for line in (klines.get("klines") or []):
            parts = line.split(",")
            if len(parts) >= 6:
                candles.append({
                    "timestamp": parts[0], "open": float(parts[1]), "close": float(parts[2]),
                    "high": float(parts[3]), "low": float(parts[4]), "volume": float(parts[5]),
                })
        return candles[-limit:]

    @handle_network_errors
    def get_ticker(self, symbol: str) -> dict:
        code, market = self._parse_symbol(symbol)
        sina_sym = self._sina_symbol(code, market)
        # Sina returns plain text, not JSON — use raw request
        import urllib.request
        url = f"{self.SINA_HQ_URL}/list={sina_sym}"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("gbk")
        # Parse: var hq_str_sh600000="浦发银行,10.50,10.49,...";
        parts = text.split('"')[1].split(",") if '"' in text else []
        if len(parts) < 10:
            return {"symbol": symbol, "last": 0, "bid": 0, "ask": 0, "volume": 0, "timestamp": ""}
        return {
            "symbol": symbol, "last": float(parts[3]),
            "bid": float(parts[6]), "ask": float(parts[7]),
            "volume": float(parts[8]), "timestamp": f"{parts[30]} {parts[31]}" if len(parts) > 31 else "",
        }

    @handle_network_errors
    def get_orderbook(self, symbol: str, depth: int = 20) -> dict:
        # Sina provides 5-level orderbook in the quote string
        code, market = self._parse_symbol(symbol)
        sina_sym = self._sina_symbol(code, market)
        import urllib.request
        url = f"{self.SINA_HQ_URL}/list={sina_sym}"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("gbk")
        parts = text.split('"')[1].split(",") if '"' in text else []
        if len(parts) < 30:
            return {"bids": [], "asks": []}
        # Bids: indices 10-19 (price, vol pairs), Asks: 20-29
        bids, asks = [], []
        for i in range(5):
            bids.append([float(parts[11 + i * 2]), float(parts[10 + i * 2])])
            asks.append([float(parts[21 + i * 2]), float(parts[20 + i * 2])])
        return {"bids": bids, "asks": asks}

    @handle_network_errors
    def place_order(self, symbol: str, side: str, type: str, amount: float, price: float | None = None) -> dict:
        raise NotImplementedError("AKShare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("AKShare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_balance(self) -> dict:
        raise NotImplementedError("AKShare is a data-only adapter; trading not supported.")

    @handle_network_errors
    def get_positions(self) -> list[dict]:
        raise NotImplementedError("AKShare is a data-only adapter; trading not supported.")
