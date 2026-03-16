"""
FinClaw v4.0.0 — Exchange adapter tests (50+ tests).
All API calls are mocked. No real network requests.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# ============================================================================
# Base & Registry Tests
# ============================================================================


class TestExchangeBase:
    def test_base_is_abstract(self):
        from src.exchanges.base import ExchangeAdapter
        with pytest.raises(TypeError):
            ExchangeAdapter()

    def test_base_config_default(self):
        from src.exchanges.base import ExchangeAdapter

        class Dummy(ExchangeAdapter):
            def get_ohlcv(self, *a, **k): return []
            def get_ticker(self, *a, **k): return {}
            def get_orderbook(self, *a, **k): return {}
            def place_order(self, *a, **k): return {}
            def cancel_order(self, *a, **k): return True
            def get_balance(self, *a, **k): return {}
            def get_positions(self, *a, **k): return []

        d = Dummy()
        assert d.config == {}
        d2 = Dummy({"key": "val"})
        assert d2.config["key"] == "val"


class TestExchangeRegistry:
    def setup_method(self):
        from src.exchanges.registry import ExchangeRegistry
        self._backup = dict(ExchangeRegistry._exchanges), dict(ExchangeRegistry._type_map)

    def teardown_method(self):
        from src.exchanges.registry import ExchangeRegistry
        ExchangeRegistry._exchanges, ExchangeRegistry._type_map = self._backup

    def test_list_exchanges(self):
        from src.exchanges.registry import ExchangeRegistry
        names = ExchangeRegistry.list_exchanges()
        assert "binance" in names
        assert "yahoo" in names
        assert "akshare" in names

    def test_list_by_type_crypto(self):
        from src.exchanges.registry import ExchangeRegistry
        crypto = ExchangeRegistry.list_by_type("crypto")
        assert "binance" in crypto
        assert "okx" in crypto
        assert "bybit" in crypto

    def test_list_by_type_stock_us(self):
        from src.exchanges.registry import ExchangeRegistry
        us = ExchangeRegistry.list_by_type("stock_us")
        assert "yahoo" in us
        assert "alpha_vantage" in us

    def test_list_by_type_stock_cn(self):
        from src.exchanges.registry import ExchangeRegistry
        cn = ExchangeRegistry.list_by_type("stock_cn")
        assert "tushare" in cn
        assert "akshare" in cn

    def test_get_unknown_raises(self):
        from src.exchanges.registry import ExchangeRegistry
        with pytest.raises(KeyError, match="not registered"):
            ExchangeRegistry.get("nonexistent_exchange")

    def test_get_returns_adapter(self):
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get("binance")
        assert adapter.name == "binance"

    def test_register_custom(self):
        from src.exchanges.registry import ExchangeRegistry
        from src.exchanges.base import ExchangeAdapter

        class Custom(ExchangeAdapter):
            name = "custom"
            exchange_type = "test"
            def get_ohlcv(self, *a, **k): return []
            def get_ticker(self, *a, **k): return {}
            def get_orderbook(self, *a, **k): return {}
            def place_order(self, *a, **k): return {}
            def cancel_order(self, *a, **k): return True
            def get_balance(self, *a, **k): return {}
            def get_positions(self, *a, **k): return []

        ExchangeRegistry.register("custom_test", Custom, "test")
        assert "custom_test" in ExchangeRegistry.list_exchanges()
        assert "custom_test" in ExchangeRegistry.list_by_type("test")


# ============================================================================
# HTTP Client Tests
# ============================================================================


class TestHttpClient:
    def test_hmac_sign(self):
        from src.exchanges.http_client import hmac_sha256_sign
        sig = hmac_sha256_sign("secret", "message")
        assert len(sig) == 64  # hex SHA256

    def test_timestamp_ms(self):
        from src.exchanges.http_client import timestamp_ms
        ts = timestamp_ms()
        assert ts > 1700000000000

    def test_exchange_api_error(self):
        from src.exchanges.http_client import ExchangeAPIError
        e = ExchangeAPIError(400, "bad request", "https://example.com")
        assert e.status == 400
        assert "400" in str(e)

    def test_connection_error(self):
        from src.exchanges.http_client import ExchangeConnectionError
        e = ExchangeConnectionError("timeout", "https://example.com")
        assert "timeout" in str(e)


# ============================================================================
# Binance Tests
# ============================================================================

def _mock_urlopen(response_data, status=200):
    """Create a mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestBinanceAdapter:
    def _make(self, **kw):
        from src.exchanges.binance import BinanceAdapter
        return BinanceAdapter(kw)

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen([
            [1700000000000, "42000.0", "42500.0", "41800.0", "42200.0", "100.5", 0, 0, 0, 0, 0, 0],
            [1700086400000, "42200.0", "43000.0", "42100.0", "42800.0", "120.3", 0, 0, 0, 0, 0, 0],
        ])
        adapter = self._make()
        candles = adapter.get_ohlcv("BTCUSDT", "1d", 2)
        assert len(candles) == 2
        assert candles[0]["open"] == 42000.0
        assert candles[1]["close"] == 42800.0

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "symbol": "BTCUSDT", "lastPrice": "42000.50", "bidPrice": "41999.0",
            "askPrice": "42001.0", "volume": "5000.0", "closeTime": 1700000000000,
        })
        adapter = self._make()
        t = adapter.get_ticker("BTCUSDT")
        assert t["last"] == 42000.50
        assert t["symbol"] == "BTCUSDT"

    @patch("urllib.request.urlopen")
    def test_get_orderbook(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "bids": [["42000.0", "1.5"], ["41999.0", "2.0"]],
            "asks": [["42001.0", "1.0"], ["42002.0", "3.0"]],
        })
        adapter = self._make()
        book = adapter.get_orderbook("BTCUSDT", 2)
        assert len(book["bids"]) == 2
        assert book["asks"][0][0] == 42001.0

    @patch("urllib.request.urlopen")
    def test_place_order(self, mock_url):
        mock_url.return_value = _mock_urlopen({"orderId": "12345", "status": "NEW"})
        adapter = self._make(api_key="key", api_secret="secret")
        result = adapter.place_order("BTCUSDT", "buy", "limit", 0.1, 42000.0)
        assert result["orderId"] == "12345"

    @patch("urllib.request.urlopen")
    def test_cancel_order(self, mock_url):
        mock_url.return_value = _mock_urlopen({"orderId": "12345", "status": "CANCELED"})
        adapter = self._make(api_key="key", api_secret="secret")
        assert adapter.cancel_order("12345") is True

    @patch("urllib.request.urlopen")
    def test_get_balance_spot(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "balances": [{"asset": "BTC", "free": "1.5", "locked": "0.5"},
                         {"asset": "USDT", "free": "10000.0", "locked": "0.0"}]
        })
        adapter = self._make(api_key="key", api_secret="secret")
        bal = adapter.get_balance()
        assert bal["BTC"]["free"] == 1.5

    @patch("urllib.request.urlopen")
    def test_get_positions_futures(self, mock_url):
        mock_url.return_value = _mock_urlopen([
            {"symbol": "BTCUSDT", "positionAmt": "0.5", "entryPrice": "42000.0", "unRealizedProfit": "500.0"},
            {"symbol": "ETHUSDT", "positionAmt": "0", "entryPrice": "0", "unRealizedProfit": "0"},
        ])
        adapter = self._make(api_key="key", api_secret="secret", futures=True)
        pos = adapter.get_positions()
        assert len(pos) == 1
        assert pos[0]["symbol"] == "BTCUSDT"

    def test_spot_no_positions(self):
        adapter = self._make()
        assert adapter.get_positions() == []

    def test_timeframe_mapping(self):
        adapter = self._make()
        assert adapter.TIMEFRAME_MAP["1h"] == "1h"
        assert adapter.TIMEFRAME_MAP["1d"] == "1d"


# ============================================================================
# OKX Tests
# ============================================================================


class TestOKXAdapter:
    def _make(self, **kw):
        from src.exchanges.okx import OKXAdapter
        return OKXAdapter(kw)

    def test_inst_id_conversion(self):
        adapter = self._make()
        assert adapter._inst_id("BTCUSDT") == "BTC-USDT"
        assert adapter._inst_id("BTC-USDT") == "BTC-USDT"
        assert adapter._inst_id("ETHBTC") == "ETH-BTC"

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": [["1700000000000", "42000", "42500", "41800", "42200", "100", "0"]]
        })
        adapter = self._make()
        candles = adapter.get_ohlcv("BTCUSDT")
        assert len(candles) == 1
        assert candles[0]["high"] == 42500.0

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": [{"instId": "BTC-USDT", "last": "42000", "bidPx": "41999",
                       "askPx": "42001", "vol24h": "5000", "ts": "1700000000000"}]
        })
        adapter = self._make()
        t = adapter.get_ticker("BTCUSDT")
        assert t["last"] == 42000.0

    @patch("urllib.request.urlopen")
    def test_get_orderbook(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": [{"bids": [["42000", "1.5"]], "asks": [["42001", "1.0"]]}]
        })
        adapter = self._make()
        book = adapter.get_orderbook("BTCUSDT")
        assert book["bids"][0][0] == 42000.0

    @patch("urllib.request.urlopen")
    def test_get_balance(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": [{"details": [{"ccy": "BTC", "availBal": "1.5", "frozenBal": "0.5"}]}]
        })
        adapter = self._make(api_key="k", api_secret="s", passphrase="p")
        bal = adapter.get_balance()
        assert bal["BTC"]["free"] == 1.5

    @patch("urllib.request.urlopen")
    def test_get_positions(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": [{"instId": "BTC-USDT", "posSide": "long", "pos": "0.5", "avgPx": "42000", "upl": "500"}]
        })
        adapter = self._make(api_key="k", api_secret="s", passphrase="p")
        pos = adapter.get_positions()
        assert len(pos) == 1


# ============================================================================
# Bybit Tests
# ============================================================================


class TestBybitAdapter:
    def _make(self, **kw):
        from src.exchanges.bybit import BybitAdapter
        return BybitAdapter(kw)

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "result": {"list": [["1700000000000", "42000", "42500", "41800", "42200", "100"]]}
        })
        adapter = self._make()
        candles = adapter.get_ohlcv("BTCUSDT")
        assert candles[0]["open"] == 42000.0

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "42000",
                                  "bid1Price": "41999", "ask1Price": "42001", "volume24h": "5000"}]},
            "time": 1700000000000,
        })
        adapter = self._make()
        t = adapter.get_ticker("BTCUSDT")
        assert t["last"] == 42000.0

    @patch("urllib.request.urlopen")
    def test_get_orderbook(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "result": {"b": [["42000", "1.5"]], "a": [["42001", "1.0"]]}
        })
        adapter = self._make()
        book = adapter.get_orderbook("BTCUSDT")
        assert book["bids"][0][0] == 42000.0

    @patch("urllib.request.urlopen")
    def test_place_order(self, mock_url):
        mock_url.return_value = _mock_urlopen({"retCode": 0, "result": {"orderId": "123"}})
        adapter = self._make(api_key="k", api_secret="s")
        result = adapter.place_order("BTCUSDT", "buy", "limit", 0.1, 42000)
        assert result["retCode"] == 0

    @patch("urllib.request.urlopen")
    def test_get_balance(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "result": {"list": [{"coin": [{"coin": "USDT", "availableToWithdraw": "10000", "locked": "500"}]}]}
        })
        adapter = self._make(api_key="k", api_secret="s")
        bal = adapter.get_balance()
        assert bal["USDT"]["free"] == 10000.0


# ============================================================================
# Yahoo Finance Tests
# ============================================================================


class TestYahooFinanceAdapter:
    def _make(self):
        from src.exchanges.yahoo_finance import YahooFinanceAdapter
        return YahooFinanceAdapter()

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "chart": {"result": [{"timestamp": [1700000000, 1700086400],
                                   "indicators": {"quote": [{"open": [150.0, 151.0], "high": [152.0, 153.0],
                                                              "low": [149.0, 150.0], "close": [151.0, 152.0],
                                                              "volume": [1000000, 1100000]}]}}]}
        })
        adapter = self._make()
        candles = adapter.get_ohlcv("AAPL")
        assert len(candles) == 2
        assert candles[0]["close"] == 151.0

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "chart": {"result": [{"meta": {"symbol": "AAPL", "regularMarketPrice": 151.5,
                                            "regularMarketVolume": 50000000, "regularMarketTime": 1700000000},
                                   "timestamp": [1700000000],
                                   "indicators": {"quote": [{"open": [150], "high": [152], "low": [149],
                                                              "close": [151], "volume": [50000000]}]}}]}
        })
        adapter = self._make()
        t = adapter.get_ticker("AAPL")
        assert t["last"] == 151.5
        assert t["symbol"] == "AAPL"

    def test_orderbook_empty(self):
        adapter = self._make()
        book = adapter.get_orderbook("AAPL")
        assert book == {"bids": [], "asks": []}

    def test_place_order_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.place_order("AAPL", "buy", "market", 10)

    def test_cancel_order_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.cancel_order("123")

    def test_get_balance_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.get_balance()

    def test_get_positions_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.get_positions()


# ============================================================================
# Alpha Vantage Tests
# ============================================================================


class TestAlphaVantageAdapter:
    def _make(self, **kw):
        from src.exchanges.alpha_vantage import AlphaVantageAdapter
        return AlphaVantageAdapter(kw)

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "Time Series (Daily)": {
                "2024-01-02": {"1. open": "150", "2. high": "152", "3. low": "149", "4. close": "151", "5. volume": "1000000"},
                "2024-01-03": {"1. open": "151", "2. high": "153", "3. low": "150", "4. close": "152", "5. volume": "1100000"},
            }
        })
        adapter = self._make(api_key="demo")
        candles = adapter.get_ohlcv("AAPL")
        assert len(candles) == 2

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "Global Quote": {"01. symbol": "AAPL", "05. price": "151.5",
                             "06. volume": "50000000", "07. latest trading day": "2024-01-03"}
        })
        adapter = self._make(api_key="demo")
        t = adapter.get_ticker("AAPL")
        assert t["last"] == 151.5

    @patch("urllib.request.urlopen")
    def test_get_ohlcv_empty(self, mock_url):
        mock_url.return_value = _mock_urlopen({"Note": "API limit reached"})
        adapter = self._make()
        assert adapter.get_ohlcv("AAPL") == []

    def test_place_order_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.place_order("AAPL", "buy", "market", 10)


# ============================================================================
# Tushare Tests
# ============================================================================


class TestTushareAdapter:
    def _make(self, **kw):
        from src.exchanges.tushare_adapter import TushareAdapter
        return TushareAdapter(kw)

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "code": 0,
            "data": {"fields": ["trade_date", "open", "high", "low", "close", "vol"],
                     "items": [["20240103", 10.5, 10.8, 10.3, 10.6, 500000],
                               ["20240102", 10.2, 10.6, 10.1, 10.5, 400000]]}
        })
        adapter = self._make(token="test")
        candles = adapter.get_ohlcv("000001.SZ")
        assert len(candles) == 2
        # Should be reversed (oldest first)
        assert candles[0]["open"] == 10.2

    @patch("urllib.request.urlopen")
    def test_get_ticker(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "code": 0,
            "data": {"fields": ["ts_code", "trade_date", "close", "vol"],
                     "items": [["000001.SZ", "20240103", 10.6, 500000]]}
        })
        adapter = self._make(token="test")
        t = adapter.get_ticker("000001.SZ")
        assert t["last"] == 10.6

    @patch("urllib.request.urlopen")
    def test_get_ticker_empty(self, mock_url):
        mock_url.return_value = _mock_urlopen({"code": 0, "data": {"fields": [], "items": []}})
        adapter = self._make(token="test")
        t = adapter.get_ticker("000001.SZ")
        assert t["last"] == 0

    @patch("urllib.request.urlopen")
    def test_api_error(self, mock_url):
        mock_url.return_value = _mock_urlopen({"code": -1, "msg": "token error"})
        adapter = self._make()
        with pytest.raises(RuntimeError, match="token error"):
            adapter.get_ohlcv("000001.SZ")

    def test_place_order_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.place_order("000001.SZ", "buy", "market", 100)


# ============================================================================
# AKShare Tests
# ============================================================================


class TestAKShareAdapter:
    def _make(self, **kw):
        from src.exchanges.akshare_adapter import AKShareAdapter
        return AKShareAdapter(kw)

    def test_parse_symbol(self):
        adapter = self._make()
        assert adapter._parse_symbol("000001.SZ") == ("000001", "SZ")
        assert adapter._parse_symbol("600000.SH") == ("600000", "SH")
        assert adapter._parse_symbol("600000") == ("600000", "SH")
        assert adapter._parse_symbol("000001") == ("000001", "SZ")

    def test_sina_symbol(self):
        adapter = self._make()
        assert adapter._sina_symbol("600000", "SH") == "sh600000"
        assert adapter._sina_symbol("000001", "SZ") == "sz000001"

    @patch("urllib.request.urlopen")
    def test_get_ohlcv(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "data": {"klines": ["2024-01-02,10.5,10.6,10.8,10.3,500000",
                                "2024-01-03,10.6,10.7,10.9,10.4,600000"]}
        })
        adapter = self._make()
        candles = adapter.get_ohlcv("000001.SZ")
        assert len(candles) == 2
        assert candles[0]["open"] == 10.5

    @patch("urllib.request.urlopen")
    def test_get_ohlcv_empty(self, mock_url):
        mock_url.return_value = _mock_urlopen({"data": None})
        adapter = self._make()
        assert adapter.get_ohlcv("000001.SZ") == []

    def test_place_order_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.place_order("000001.SZ", "buy", "market", 100)

    def test_get_balance_raises(self):
        adapter = self._make()
        with pytest.raises(NotImplementedError):
            adapter.get_balance()


# ============================================================================
# CLI Integration Tests
# ============================================================================


class TestCLIExchanges:
    def test_exchanges_list(self):
        from src.cli import main
        # Should not raise
        ret = main(["exchanges"])
        assert ret == 0

    @patch("urllib.request.urlopen")
    def test_quote_command(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "chart": {"result": [{"meta": {"symbol": "AAPL", "regularMarketPrice": 151.5,
                                            "regularMarketVolume": 50000000, "regularMarketTime": 1700000000},
                                   "timestamp": [1700000000],
                                   "indicators": {"quote": [{"open": [150], "high": [152], "low": [149],
                                                              "close": [151], "volume": [50000000]}]}}]}
        })
        from src.cli import main
        ret = main(["quote", "AAPL", "--exchange", "yahoo"])
        assert ret == 0

    @patch("urllib.request.urlopen")
    def test_history_command(self, mock_url):
        mock_url.return_value = _mock_urlopen({
            "chart": {"result": [{"timestamp": [1700000000],
                                   "indicators": {"quote": [{"open": [150.0], "high": [152.0],
                                                              "low": [149.0], "close": [151.0],
                                                              "volume": [1000000]}]}}]}
        })
        from src.cli import main
        ret = main(["history", "AAPL", "--exchange", "yahoo", "--limit", "5"])
        assert ret == 0

    def test_info_command(self):
        from src.cli import main
        ret = main(["info"])
        assert ret == 0


# ============================================================================
# Cross-cutting Tests
# ============================================================================


class TestAdapterInterfaces:
    """Verify all adapters implement the required interface."""

    @pytest.mark.parametrize("name", ["binance", "okx", "bybit", "yahoo", "alpha_vantage", "tushare", "akshare"])
    def test_has_all_methods(self, name):
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get(name)
        for method in ["get_ohlcv", "get_ticker", "get_orderbook", "place_order", "cancel_order", "get_balance", "get_positions"]:
            assert hasattr(adapter, method), f"{name} missing {method}"
            assert callable(getattr(adapter, method))

    @pytest.mark.parametrize("name", ["binance", "okx", "bybit", "yahoo", "alpha_vantage", "tushare", "akshare"])
    def test_has_name_and_type(self, name):
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get(name)
        assert adapter.name
        assert adapter.exchange_type in ("crypto", "stock_us", "stock_cn")

    @pytest.mark.parametrize("name", ["yahoo", "alpha_vantage", "tushare", "akshare"])
    def test_data_only_raises_on_trade(self, name):
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get(name)
        with pytest.raises(NotImplementedError):
            adapter.place_order("X", "buy", "market", 1)
