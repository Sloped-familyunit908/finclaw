"""
Exchange Integration Tests
===========================
Tests error handling for exchange adapters: timeouts, HTTP errors,
empty responses, malformed JSON, rate limits.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exchanges.base import ExchangeError, ExchangeAdapter, handle_network_errors
from src.exchanges.http_client import ExchangeAPIError, ExchangeConnectionError, HttpClient


# ── HttpClient Error Tests ───────────────────────────────────────

class TestHttpClientErrors:
    def test_http_500_raises_api_error(self):
        client = HttpClient("https://httpbin.org", timeout=5)
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.HTTPError(
                "https://example.com", 500, "Internal Server Error",
                {}, None
            )
            with pytest.raises(ExchangeAPIError) as exc_info:
                client.get("/test")
            assert exc_info.value.status == 500

    def test_connection_refused_raises(self):
        client = HttpClient("https://httpbin.org", timeout=5)
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = urllib.error.URLError("Connection refused")
            with pytest.raises(ExchangeConnectionError):
                client.get("/test")

    def test_timeout_raises(self):
        client = HttpClient("https://httpbin.org", timeout=1)
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.side_effect = TimeoutError("timed out")
            with pytest.raises(TimeoutError):
                client.get("/test")


# ── handle_network_errors Decorator ─────────────────────────────

class TestHandleNetworkErrors:
    """Test the @handle_network_errors decorator converts exceptions to ExchangeError."""

    def _make_adapter_class(self):
        class FakeAdapter(ExchangeAdapter):
            name = "fake"
            exchange_type = "test"

            def get_ohlcv(self, symbol, timeframe="1d", limit=100):
                raise NotImplementedError

            def get_ticker(self, symbol):
                raise NotImplementedError

            def get_orderbook(self, symbol, depth=20):
                raise NotImplementedError

            def place_order(self, symbol, side, type, amount, price=None):
                raise NotImplementedError

            def cancel_order(self, order_id):
                raise NotImplementedError

            def get_balance(self):
                raise NotImplementedError

            def get_positions(self):
                raise NotImplementedError

            @handle_network_errors
            def fetch_data(self):
                pass  # will be overridden by tests

        return FakeAdapter

    def test_api_error_wrapped(self):
        FakeAdapter = self._make_adapter_class()
        adapter = FakeAdapter()
        adapter.fetch_data = handle_network_errors(
            lambda self: (_ for _ in ()).throw(ExchangeAPIError(429, "Rate limited", "https://api.example.com"))
        ).__get__(adapter)
        with pytest.raises(ExchangeError) as exc_info:
            adapter.fetch_data()
        assert "429" in str(exc_info.value)

    def test_connection_error_wrapped(self):
        FakeAdapter = self._make_adapter_class()
        adapter = FakeAdapter()

        @handle_network_errors
        def fetch(self):
            raise ExchangeConnectionError("Connection refused", "https://api.example.com")

        adapter.fetch_data = fetch.__get__(adapter)
        with pytest.raises(ExchangeError) as exc_info:
            adapter.fetch_data()
        assert "Connection failed" in str(exc_info.value)

    def test_timeout_wrapped(self):
        FakeAdapter = self._make_adapter_class()
        adapter = FakeAdapter()

        @handle_network_errors
        def fetch(self):
            raise TimeoutError("timed out")

        adapter.fetch_data = fetch.__get__(adapter)
        with pytest.raises(ExchangeError) as exc_info:
            adapter.fetch_data()
        assert "timed out" in str(exc_info.value).lower()

    def test_key_error_wrapped(self):
        """Malformed JSON (missing keys) should be caught."""
        FakeAdapter = self._make_adapter_class()
        adapter = FakeAdapter()

        @handle_network_errors
        def fetch(self):
            d = {}
            return d["missing_key"]

        adapter.fetch_data = fetch.__get__(adapter)
        with pytest.raises(ExchangeError) as exc_info:
            adapter.fetch_data()
        assert "Unexpected response" in str(exc_info.value)


# ── Binance Adapter Error Handling ───────────────────────────────

class TestBinanceAdapterErrors:
    def test_get_ticker_api_error(self):
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        with patch.object(adapter.client, "get", side_effect=ExchangeAPIError(500, "Server Error", "url")):
            with pytest.raises(ExchangeError):
                adapter.get_ticker("BTCUSDT")

    def test_get_ohlcv_timeout(self):
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        with patch.object(adapter.client, "get", side_effect=TimeoutError("timeout")):
            with pytest.raises(ExchangeError):
                adapter.get_ohlcv("BTCUSDT")

    def test_get_ticker_connection_refused(self):
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        with patch.object(adapter.client, "get", side_effect=ExchangeConnectionError("refused", "url")):
            with pytest.raises(ExchangeError):
                adapter.get_ticker("BTCUSDT")

    def test_get_ticker_malformed_json(self):
        """Malformed response missing expected keys."""
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        # Return dict missing 'symbol' key → should raise ExchangeError via KeyError
        with patch.object(adapter.client, "get", return_value={"unexpected": "data"}):
            with pytest.raises(ExchangeError):
                adapter.get_ticker("BTCUSDT")

    def test_get_ohlcv_empty_response(self):
        """Empty list response."""
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        with patch.object(adapter.client, "get", return_value=[]):
            result = adapter.get_ohlcv("BTCUSDT")
            assert result == []

    def test_rate_limit_429(self):
        from src.exchanges.binance import BinanceAdapter
        adapter = BinanceAdapter()
        with patch.object(adapter.client, "get", side_effect=ExchangeAPIError(429, "Rate limit", "url")):
            with pytest.raises(ExchangeError) as exc_info:
                adapter.get_ticker("BTCUSDT")
            assert "429" in str(exc_info.value)


# ── OKX Adapter Error Handling ───────────────────────────────────

class TestOKXAdapterErrors:
    def test_get_ticker_timeout(self):
        from src.exchanges.okx import OKXAdapter
        adapter = OKXAdapter()
        with patch.object(adapter.client, "get", side_effect=TimeoutError("timeout")):
            with pytest.raises(ExchangeError):
                adapter.get_ticker("BTC-USDT")

    def test_get_ticker_500(self):
        from src.exchanges.okx import OKXAdapter
        adapter = OKXAdapter()
        with patch.object(adapter.client, "get", side_effect=ExchangeAPIError(500, "Error", "url")):
            with pytest.raises(ExchangeError):
                adapter.get_ticker("BTC-USDT")


# ── Exchange Registry ────────────────────────────────────────────

class TestExchangeRegistry:
    def test_list_exchanges(self):
        from src.exchanges.registry import ExchangeRegistry
        exchanges = ExchangeRegistry.list_exchanges()
        assert isinstance(exchanges, list)
        assert "binance" in exchanges
        assert "yahoo" in exchanges

    def test_get_unknown_exchange(self):
        from src.exchanges.registry import ExchangeRegistry
        with pytest.raises(KeyError):
            ExchangeRegistry.get("nonexistent_exchange_xyz")

    def test_list_by_type(self):
        from src.exchanges.registry import ExchangeRegistry
        crypto = ExchangeRegistry.list_by_type("crypto")
        assert "binance" in crypto
        stocks = ExchangeRegistry.list_by_type("stock_us")
        assert "yahoo" in stocks
