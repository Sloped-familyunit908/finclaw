"""
Tests for v4.9.0 — New exchange adapters: Coinbase, Kraken, Alpaca, Polygon, Baostock
+ Exchange comparison CLI feature.
45+ tests covering all new adapters and features.
"""

import json
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─── Registry Tests ───

class TestRegistryNewAdapters:
    """Test that all new adapters are registered properly."""

    def test_coinbase_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "coinbase" in ExchangeRegistry.list_exchanges()

    def test_kraken_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "kraken" in ExchangeRegistry.list_exchanges()

    def test_alpaca_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "alpaca" in ExchangeRegistry.list_exchanges()

    def test_polygon_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "polygon" in ExchangeRegistry.list_exchanges()

    def test_baostock_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "baostock" in ExchangeRegistry.list_exchanges()

    def test_crypto_includes_coinbase_kraken(self):
        from src.exchanges.registry import ExchangeRegistry
        crypto = ExchangeRegistry.list_by_type("crypto")
        assert "coinbase" in crypto
        assert "kraken" in crypto

    def test_stock_us_includes_alpaca_polygon(self):
        from src.exchanges.registry import ExchangeRegistry
        us = ExchangeRegistry.list_by_type("stock_us")
        assert "alpaca" in us
        assert "polygon" in us

    def test_stock_cn_includes_baostock(self):
        from src.exchanges.registry import ExchangeRegistry
        cn = ExchangeRegistry.list_by_type("stock_cn")
        assert "baostock" in cn

    def test_total_exchange_count(self):
        from src.exchanges.registry import ExchangeRegistry
        # 7 original + 5 new = 12
        assert len(ExchangeRegistry.list_exchanges()) >= 12


# ─── Coinbase Adapter Tests ───

class TestCoinbaseAdapter:
    def _adapter(self):
        from src.exchanges.coinbase import CoinbaseAdapter
        return CoinbaseAdapter({"api_key": "test", "api_secret": "secret"})

    def test_init(self):
        a = self._adapter()
        assert a.name == "coinbase"
        assert a.exchange_type == "crypto"

    def test_product_id_conversion(self):
        from src.exchanges.coinbase import CoinbaseAdapter
        assert CoinbaseAdapter._to_product_id("BTCUSD") == "BTC-USD"
        assert CoinbaseAdapter._to_product_id("ETHUSDT") == "ETH-USDT"
        assert CoinbaseAdapter._to_product_id("BTC-USD") == "BTC-USD"

    def test_granularity_seconds(self):
        from src.exchanges.coinbase import CoinbaseAdapter
        assert CoinbaseAdapter._granularity_seconds("1m") == 60
        assert CoinbaseAdapter._granularity_seconds("1d") == 86400

    def test_timeframe_map(self):
        a = self._adapter()
        assert "1m" in a.TIMEFRAME_MAP
        assert a.TIMEFRAME_MAP["1d"] == "ONE_DAY"

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv(self, mock_get):
        mock_get.return_value = {"candles": [
            {"start": "1700000000", "open": "40000", "high": "41000",
             "low": "39000", "close": "40500", "volume": "100"},
        ]}
        a = self._adapter()
        result = a.get_ohlcv("BTC-USD", "1d", 1)
        assert len(result) == 1
        assert result[0]["close"] == 40500.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ticker(self, mock_get):
        mock_get.return_value = {
            "price": "40500", "bid": "40490", "ask": "40510", "volume_24h": "1000",
        }
        a = self._adapter()
        t = a.get_ticker("BTC-USD")
        assert t["last"] == 40500.0
        assert t["symbol"] == "BTC-USD"

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_orderbook(self, mock_get):
        mock_get.return_value = {"pricebook": {
            "bids": [{"price": "40000", "size": "1.5"}],
            "asks": [{"price": "40100", "size": "2.0"}],
        }}
        a = self._adapter()
        ob = a.get_orderbook("BTC-USD")
        assert len(ob["bids"]) == 1
        assert ob["asks"][0][0] == 40100.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_trades(self, mock_get):
        mock_get.return_value = {"trades": [
            {"price": "40500", "size": "0.5", "side": "BUY", "time": "2024-01-01"},
        ]}
        a = self._adapter()
        trades = a.get_trades("BTC-USD")
        assert len(trades) == 1

    def test_auth_headers(self):
        a = self._adapter()
        h = a._auth_headers("GET", "/test")
        assert "CB-ACCESS-KEY" in h
        assert "CB-ACCESS-SIGN" in h
        assert h["CB-ACCESS-KEY"] == "test"

    def test_positions_empty(self):
        a = self._adapter()
        assert a.get_positions() == []


# ─── Kraken Adapter Tests ───

class TestKrakenAdapter:
    def _adapter(self):
        from src.exchanges.kraken import KrakenAdapter
        import base64
        # Kraken needs base64-encoded secret
        secret = base64.b64encode(b"testsecret123456").decode()
        return KrakenAdapter({"api_key": "test", "api_secret": secret})

    def test_init(self):
        a = self._adapter()
        assert a.name == "kraken"
        assert a.exchange_type == "crypto"

    def test_timeframe_map(self):
        a = self._adapter()
        assert a.TIMEFRAME_MAP["1d"] == 1440
        assert a.TIMEFRAME_MAP["1h"] == 60

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv(self, mock_get):
        mock_get.return_value = {"error": [], "result": {
            "XXBTZUSD": [
                [1700000000, "40000", "41000", "39000", "40500", "0", "100", 5],
            ],
            "last": 1700000000,
        }}
        a = self._adapter()
        result = a.get_ohlcv("XBTUSD")
        assert len(result) == 1
        assert result[0]["close"] == 40500.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ticker(self, mock_get):
        mock_get.return_value = {"error": [], "result": {
            "XXBTZUSD": {
                "c": ["40500.0", "1"], "b": ["40490.0", "1", "1"],
                "a": ["40510.0", "1", "1"], "v": ["500", "1200"],
            }
        }}
        a = self._adapter()
        t = a.get_ticker("XBTUSD")
        assert t["last"] == 40500.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_orderbook(self, mock_get):
        mock_get.return_value = {"error": [], "result": {
            "XXBTZUSD": {
                "bids": [["40000", "1.5", 1700000000]],
                "asks": [["40100", "2.0", 1700000000]],
            }
        }}
        a = self._adapter()
        ob = a.get_orderbook("XBTUSD")
        assert ob["bids"][0][0] == 40000.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_trades(self, mock_get):
        mock_get.return_value = {"error": [], "result": {
            "XXBTZUSD": [
                ["40500", "0.5", 1700000000.0, "b", "m", ""],
            ],
            "last": "1700000000",
        }}
        a = self._adapter()
        trades = a.get_trades("XBTUSD")
        assert len(trades) == 1
        assert trades[0]["side"] == "buy"

    def test_check_result_error(self):
        a = self._adapter()
        with pytest.raises(RuntimeError, match="Kraken API error"):
            a._check_result({"error": ["EGeneral:Invalid arguments"], "result": {}})

    def test_sign_generates_headers(self):
        a = self._adapter()
        h = a._sign("/0/private/Balance", {"nonce": "123"})
        assert "API-Key" in h
        assert "API-Sign" in h


# ─── Alpaca Adapter Tests ───

class TestAlpacaAdapter:
    def _adapter(self, paper=True):
        from src.exchanges.alpaca import AlpacaAdapter
        return AlpacaAdapter({"api_key": "test", "api_secret": "secret", "paper": paper})

    def test_init_paper(self):
        a = self._adapter(paper=True)
        assert a.name == "alpaca"
        assert a.exchange_type == "stock_us"
        assert a.paper is True
        assert "paper-api" in a.trade_client.base_url

    def test_init_live(self):
        a = self._adapter(paper=False)
        assert "paper" not in a.trade_client.base_url

    def test_timeframe_map(self):
        a = self._adapter()
        assert a.TIMEFRAME_MAP["1d"] == "1Day"
        assert a.TIMEFRAME_MAP["1m"] == "1Min"

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv(self, mock_get):
        mock_get.return_value = {"bars": [
            {"t": "2024-01-01T00:00:00Z", "o": 150.0, "h": 155.0,
             "l": 149.0, "c": 153.0, "v": 1000000},
        ]}
        a = self._adapter()
        result = a.get_ohlcv("AAPL")
        assert len(result) == 1
        assert result[0]["close"] == 153.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ticker(self, mock_get):
        mock_get.return_value = {
            "latestTrade": {"p": 153.0, "t": "2024-01-01"},
            "latestQuote": {"bp": 152.9, "ap": 153.1},
            "dailyBar": {"v": 5000000},
        }
        a = self._adapter()
        t = a.get_ticker("AAPL")
        assert t["last"] == 153.0
        assert t["symbol"] == "AAPL"

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_orderbook(self, mock_get):
        mock_get.return_value = {
            "latestQuote": {"bp": 152.9, "ap": 153.1, "bs": 100, "as": 200},
        }
        a = self._adapter()
        ob = a.get_orderbook("AAPL")
        assert ob["bids"][0][0] == 152.9

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_balance(self, mock_get):
        mock_get.return_value = {
            "buying_power": "50000", "portfolio_value": "100000",
            "equity": "100000", "cash": "50000",
        }
        a = self._adapter()
        bal = a.get_balance()
        assert bal["USD"]["free"] == 50000.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_positions(self, mock_get):
        mock_get.return_value = [
            {"symbol": "AAPL", "side": "long", "qty": "100",
             "avg_entry_price": "150", "current_price": "155",
             "unrealized_pl": "500", "market_value": "15500"},
        ]
        a = self._adapter()
        pos = a.get_positions()
        assert len(pos) == 1
        assert pos[0]["symbol"] == "AAPL"

    @patch("src.exchanges.http_client.HttpClient.delete")
    def test_cancel_order(self, mock_del):
        mock_del.return_value = {}
        a = self._adapter()
        assert a.cancel_order("order123") is True


# ─── Polygon Adapter Tests ───

class TestPolygonAdapter:
    def _adapter(self):
        from src.exchanges.polygon import PolygonAdapter
        return PolygonAdapter({"api_key": "test_key"})

    def test_init(self):
        a = self._adapter()
        assert a.name == "polygon"
        assert a.exchange_type == "stock_us"

    def test_timeframe_map(self):
        a = self._adapter()
        assert a.TIMEFRAME_MAP["1d"] == ("day", 1)
        assert a.TIMEFRAME_MAP["1h"] == ("hour", 1)

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv(self, mock_get):
        mock_get.return_value = {"results": [
            {"t": 1700000000000, "o": 150.0, "h": 155.0,
             "l": 149.0, "c": 153.0, "v": 1000000},
        ]}
        a = self._adapter()
        result = a.get_ohlcv("AAPL")
        assert len(result) == 1
        assert result[0]["open"] == 150.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ticker(self, mock_get):
        mock_get.return_value = {"ticker": {
            "day": {"v": 5000000},
            "lastTrade": {"p": 153.0},
            "lastQuote": {"p": 152.9, "P": 153.1},
            "updated": 1700000000000,
        }}
        a = self._adapter()
        t = a.get_ticker("AAPL")
        assert t["last"] == 153.0

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_orderbook(self, mock_get):
        mock_get.return_value = {"data": {
            "bids": [{"p": 152.9, "s": 100}],
            "asks": [{"p": 153.1, "s": 200}],
        }}
        a = self._adapter()
        ob = a.get_orderbook("AAPL")
        assert ob["bids"][0][0] == 152.9

    def test_place_order_not_supported(self):
        a = self._adapter()
        with pytest.raises(NotImplementedError):
            a.place_order("AAPL", "buy", "market", 100)

    def test_cancel_order_not_supported(self):
        a = self._adapter()
        with pytest.raises(NotImplementedError):
            a.cancel_order("123")

    def test_balance_empty(self):
        a = self._adapter()
        assert a.get_balance() == {}

    def test_positions_empty(self):
        a = self._adapter()
        assert a.get_positions() == []

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_search_tickers(self, mock_get):
        mock_get.return_value = {"results": [{"ticker": "AAPL", "name": "Apple"}]}
        a = self._adapter()
        results = a.search_tickers("apple")
        assert len(results) == 1

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_market_status(self, mock_get):
        mock_get.return_value = {"market": "open"}
        a = self._adapter()
        assert a.get_market_status()["market"] == "open"


# ─── Baostock Adapter Tests ───

class TestBaostockAdapter:
    def _adapter(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        return BaostockAdapter()

    def test_init(self):
        a = self._adapter()
        assert a.name == "baostock"
        assert a.exchange_type == "stock_cn"

    def test_normalize_symbol_sh(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        assert BaostockAdapter._normalize_symbol("600000") == "sh.600000"

    def test_normalize_symbol_sz(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        assert BaostockAdapter._normalize_symbol("000001") == "sz.000001"

    def test_normalize_symbol_already_prefixed(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        assert BaostockAdapter._normalize_symbol("sh.600000") == "sh.600000"

    def test_normalize_symbol_300(self):
        from src.exchanges.baostock_adapter import BaostockAdapter
        assert BaostockAdapter._normalize_symbol("300750") == "sz.300750"

    def test_freq_map(self):
        a = self._adapter()
        assert a.FREQ_MAP["1d"] == "d"
        assert a.FREQ_MAP["1w"] == "w"

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv(self, mock_get):
        mock_get.return_value = {"data": [
            {"date": "2024-01-02", "open": "10.5", "high": "11.0",
             "low": "10.2", "close": "10.8", "volume": "500000"},
        ]}
        a = self._adapter()
        result = a.get_ohlcv("600000")
        assert len(result) == 1

    @patch("src.exchanges.http_client.HttpClient.get")
    def test_get_ohlcv_graceful_failure(self, mock_get):
        mock_get.side_effect = Exception("connection failed")
        a = self._adapter()
        result = a.get_ohlcv("600000")
        assert result == []

    def test_place_order_not_supported(self):
        a = self._adapter()
        with pytest.raises(NotImplementedError):
            a.place_order("600000", "buy", "market", 100)

    def test_balance_empty(self):
        a = self._adapter()
        assert a.get_balance() == {}

    def test_orderbook_empty(self):
        a = self._adapter()
        assert a.get_orderbook("600000") == {"bids": [], "asks": []}


# ─── Exchange Compare CLI Tests ───

class TestExchangeCompare:
    def test_compare_function_exists(self):
        from src.cli import _compare_exchanges
        assert callable(_compare_exchanges)

    def test_compare_prints_table(self, capsys):
        from src.cli import _compare_exchanges
        _compare_exchanges(["binance", "coinbase", "kraken"])
        out = capsys.readouterr().out
        assert "Feature" in out
        assert "OHLCV" in out
        assert "✅" in out

    def test_compare_invalid_exchange(self, capsys):
        from src.cli import _compare_exchanges
        _compare_exchanges(["nonexistent_exchange"])
        out = capsys.readouterr().out
        assert "not found" in out

    def test_compare_shows_exchange_types(self, capsys):
        from src.cli import _compare_exchanges
        _compare_exchanges(["binance", "alpaca"])
        out = capsys.readouterr().out
        assert "crypto" in out
        assert "stock_us" in out
