"""Tests for exchange adapter network error handling (Issue #4)."""

import pytest
from unittest.mock import patch, MagicMock

from src.exchanges.base import ExchangeError, handle_network_errors
from src.exchanges.http_client import ExchangeAPIError, ExchangeConnectionError
from src.exchanges.binance import BinanceAdapter
from src.exchanges.okx import OKXAdapter
from src.exchanges.bybit import BybitAdapter
from src.exchanges.coinbase import CoinbaseAdapter
from src.exchanges.kraken import KrakenAdapter
from src.exchanges.yahoo_finance import YahooFinanceAdapter
from src.exchanges.alpaca import AlpacaAdapter
from src.exchanges.polygon import PolygonAdapter
from src.exchanges.alpha_vantage import AlphaVantageAdapter


class TestExchangeErrorBase:
    """Test that ExchangeError is raised with correct info."""

    def test_exchange_error_attributes(self):
        err = ExchangeError("binance", "get_ticker", "something broke")
        assert err.exchange == "binance"
        assert err.operation == "get_ticker"
        assert "binance" in str(err)
        assert "get_ticker" in str(err)

    def test_exchange_error_preserves_original(self):
        orig = ValueError("bad")
        err = ExchangeError("okx", "get_ohlcv", "parse failed", original=orig)
        assert err.original is orig


class TestHandleNetworkErrorsDecorator:
    """Test the decorator catches various exception types."""

    def test_catches_api_error(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                raise ExchangeAPIError(429, "rate limited", "https://api.test.com/v1")

        with pytest.raises(ExchangeError, match="HTTP 429"):
            FakeAdapter().do_thing()

    def test_catches_connection_error(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                raise ExchangeConnectionError("DNS lookup failed", "https://api.test.com")

        with pytest.raises(ExchangeError, match="Connection failed"):
            FakeAdapter().do_thing()

    def test_catches_timeout(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                raise TimeoutError("timed out")

        with pytest.raises(ExchangeError, match="timed out"):
            FakeAdapter().do_thing()

    def test_catches_os_error(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                raise OSError("Network unreachable")

        with pytest.raises(ExchangeError, match="Network error"):
            FakeAdapter().do_thing()

    def test_catches_key_error(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                raise KeyError("missing_field")

        with pytest.raises(ExchangeError, match="Unexpected response"):
            FakeAdapter().do_thing()

    def test_passes_through_on_success(self):
        class FakeAdapter:
            name = "test"

            @handle_network_errors
            def do_thing(self):
                return {"ok": True}

        assert FakeAdapter().do_thing() == {"ok": True}


class TestBinanceErrorHandling:
    """Test Binance adapter wraps errors properly."""

    def setup_method(self):
        self.adapter = BinanceAdapter()

    def test_get_ticker_connection_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeConnectionError("timeout", "https://api.binance.com")):
            with pytest.raises(ExchangeError, match="binance.*Connection failed"):
                self.adapter.get_ticker("BTCUSDT")

    def test_get_ohlcv_api_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeAPIError(503, "Service Unavailable", "https://api.binance.com")):
            with pytest.raises(ExchangeError, match="HTTP 503"):
                self.adapter.get_ohlcv("BTCUSDT")

    def test_get_orderbook_timeout(self):
        with patch.object(self.adapter.client, "get", side_effect=TimeoutError()):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_orderbook("BTCUSDT")


class TestOKXErrorHandling:
    def setup_method(self):
        self.adapter = OKXAdapter()

    def test_get_ticker_connection_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeConnectionError("refused", "https://www.okx.com")):
            with pytest.raises(ExchangeError, match="okx.*Connection failed"):
                self.adapter.get_ticker("BTC-USDT")


class TestBybitErrorHandling:
    def setup_method(self):
        self.adapter = BybitAdapter()

    def test_get_ohlcv_api_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeAPIError(500, "Internal Error", "https://api.bybit.com")):
            with pytest.raises(ExchangeError, match="HTTP 500"):
                self.adapter.get_ohlcv("BTCUSDT")


class TestYahooErrorHandling:
    def setup_method(self):
        self.adapter = YahooFinanceAdapter()

    def test_get_ticker_network_error(self):
        with patch.object(self.adapter.client, "get", side_effect=OSError("Network is down")):
            with pytest.raises(ExchangeError, match="Network error"):
                self.adapter.get_ticker("AAPL")

    def test_get_ohlcv_bad_response(self):
        with patch.object(self.adapter.client, "get", return_value={"chart": {"result": [{}]}}):
            with pytest.raises(ExchangeError, match="Unexpected response"):
                self.adapter.get_ohlcv("AAPL")


class TestCoinbaseErrorHandling:
    def setup_method(self):
        self.adapter = CoinbaseAdapter()

    def test_get_ticker_connection_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeConnectionError("refused", "https://api.coinbase.com")):
            with pytest.raises(ExchangeError, match="coinbase.*Connection failed"):
                self.adapter.get_ticker("BTC-USD")


class TestKrakenErrorHandling:
    def setup_method(self):
        self.adapter = KrakenAdapter()

    def test_get_ticker_api_error(self):
        with patch.object(self.adapter.client, "get", side_effect=ExchangeAPIError(502, "Bad Gateway", "https://api.kraken.com")):
            with pytest.raises(ExchangeError, match="HTTP 502"):
                self.adapter.get_ticker("XXBTZUSD")


class TestAlpacaErrorHandling:
    def setup_method(self):
        self.adapter = AlpacaAdapter()

    def test_get_ticker_connection_error(self):
        with patch.object(self.adapter.data_client, "get", side_effect=ExchangeConnectionError("refused", "https://data.alpaca.markets")):
            with pytest.raises(ExchangeError, match="alpaca.*Connection failed"):
                self.adapter.get_ticker("AAPL")


class TestPolygonErrorHandling:
    def setup_method(self):
        self.adapter = PolygonAdapter()

    def test_get_ohlcv_timeout(self):
        with patch.object(self.adapter.client, "get", side_effect=TimeoutError()):
            with pytest.raises(ExchangeError, match="timed out"):
                self.adapter.get_ohlcv("AAPL")
