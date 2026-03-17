"""Tests for Binance adapter (Issue #1) — unit tests with mocked HTTP."""

import pytest
from unittest.mock import patch, MagicMock

from src.exchanges.binance import BinanceAdapter


class TestBinanceAdapterInit:
    def test_default_spot(self):
        adapter = BinanceAdapter()
        assert adapter.name == "binance"
        assert adapter.exchange_type == "crypto"
        assert adapter.futures is False
        assert "api.binance.com" in adapter.client.base_url

    def test_futures_mode(self):
        adapter = BinanceAdapter({"futures": True})
        assert adapter.futures is True
        assert "fapi.binance.com" in adapter.client.base_url

    def test_api_key_header(self):
        adapter = BinanceAdapter({"api_key": "testkey"})
        assert adapter.client.default_headers.get("X-MBX-APIKEY") == "testkey"


class TestBinanceGetOHLCV:
    def setup_method(self):
        self.adapter = BinanceAdapter()

    def test_parses_klines(self):
        mock_data = [
            [1700000000000, "42000.0", "42500.0", "41800.0", "42200.0", "1234.5",
             1700003600000, "0", 100, "0", "0", "0"]
        ]
        with patch.object(self.adapter.client, "get", return_value=mock_data):
            result = self.adapter.get_ohlcv("BTCUSDT", "1d", 1)
        assert len(result) == 1
        assert result[0]["open"] == 42000.0
        assert result[0]["close"] == 42200.0
        assert result[0]["volume"] == 1234.5
        assert result[0]["timestamp"] == 1700000000000

    def test_timeframe_mapping(self):
        with patch.object(self.adapter.client, "get", return_value=[]) as mock_get:
            self.adapter.get_ohlcv("BTCUSDT", "1h", 50)
            args, kwargs = mock_get.call_args
            assert kwargs.get("params", args[1] if len(args) > 1 else {}).get("interval") == "1h"


class TestBinanceGetTicker:
    def setup_method(self):
        self.adapter = BinanceAdapter()

    def test_parses_ticker(self):
        mock_data = {
            "symbol": "BTCUSDT", "lastPrice": "42000.50",
            "bidPrice": "41999.0", "askPrice": "42001.0",
            "volume": "50000.0", "closeTime": 1700000000000,
        }
        with patch.object(self.adapter.client, "get", return_value=mock_data):
            result = self.adapter.get_ticker("BTCUSDT")
        assert result["symbol"] == "BTCUSDT"
        assert result["last"] == 42000.50
        assert result["bid"] == 41999.0
        assert result["ask"] == 42001.0
        assert result["volume"] == 50000.0


class TestBinanceGetOrderbook:
    def setup_method(self):
        self.adapter = BinanceAdapter()

    def test_parses_orderbook(self):
        mock_data = {
            "bids": [["42000.0", "1.5"], ["41999.0", "2.0"]],
            "asks": [["42001.0", "1.0"], ["42002.0", "3.0"]],
        }
        with patch.object(self.adapter.client, "get", return_value=mock_data):
            result = self.adapter.get_orderbook("BTCUSDT", 2)
        assert len(result["bids"]) == 2
        assert result["bids"][0] == [42000.0, 1.5]
        assert result["asks"][0] == [42001.0, 1.0]


class TestBinanceFutures:
    def setup_method(self):
        self.adapter = BinanceAdapter({"futures": True})

    def test_futures_uses_fapi_path(self):
        with patch.object(self.adapter.client, "get", return_value=[]) as mock_get:
            self.adapter.get_ohlcv("BTCUSDT")
            assert mock_get.call_args[0][0] == "/fapi/v1/klines"


class TestBinanceRegistry:
    def test_registered(self):
        from src.exchanges.registry import ExchangeRegistry
        assert "binance" in ExchangeRegistry.list_exchanges()
        assert "binance" in ExchangeRegistry.list_by_type("crypto")

    def test_create_from_registry(self):
        from src.exchanges.registry import ExchangeRegistry
        adapter = ExchangeRegistry.get("binance")
        assert isinstance(adapter, BinanceAdapter)
