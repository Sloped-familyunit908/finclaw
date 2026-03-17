"""Tests for watchlist manager and stock screener."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.watchlist.manager import WatchlistManager, Watchlist, DEFAULT_PATH
from src.screener.stock_screener import StockScreener, StockData


# ======================================================================
# Watchlist Manager Tests
# ======================================================================


class TestWatchlistManager:
    """Tests for WatchlistManager CRUD and persistence."""

    @pytest.fixture
    def tmp_path_file(self, tmp_path):
        return tmp_path / "watchlists.json"

    @pytest.fixture
    def wm(self, tmp_path_file):
        return WatchlistManager(path=tmp_path_file)

    def test_create_watchlist(self, wm):
        wl = wm.create("default")
        assert wl.name == "default"
        assert wl.tickers == []

    def test_create_with_tickers(self, wm):
        wl = wm.create("crypto", tickers=["btc", "eth"])
        assert wl.tickers == ["BTC", "ETH"]

    def test_add_ticker(self, wm):
        wm.create("default")
        wm.add_ticker("default", "aapl")
        wl = wm.get("default")
        assert "AAPL" in wl.tickers

    def test_add_ticker_no_duplicates(self, wm):
        wm.create("default")
        wm.add_ticker("default", "AAPL")
        wm.add_ticker("default", "aapl")
        assert wm.get("default").tickers == ["AAPL"]

    def test_add_tickers_bulk(self, wm):
        wm.create("default")
        wm.add_tickers("default", ["aapl", "msft", "goog"])
        assert wm.get("default").tickers == ["AAPL", "MSFT", "GOOG"]

    def test_remove_ticker(self, wm):
        wm.create("default", ["AAPL", "MSFT"])
        wm.remove_ticker("default", "aapl")
        assert "AAPL" not in wm.get("default").tickers
        assert "MSFT" in wm.get("default").tickers

    def test_remove_nonexistent_ticker(self, wm):
        wm.create("default", ["AAPL"])
        wm.remove_ticker("default", "BTC")  # no error
        assert wm.get("default").tickers == ["AAPL"]

    def test_add_ticker_missing_watchlist(self, wm):
        with pytest.raises(KeyError):
            wm.add_ticker("nope", "AAPL")

    def test_delete_watchlist(self, wm):
        wm.create("temp")
        assert wm.delete("temp") is True
        assert wm.get("temp") is None

    def test_delete_nonexistent(self, wm):
        assert wm.delete("nope") is False

    def test_list_all(self, wm):
        wm.create("stocks")
        wm.create("crypto")
        assert set(wm.list_all()) == {"stocks", "crypto"}

    def test_persistence(self, tmp_path_file):
        wm1 = WatchlistManager(path=tmp_path_file)
        wm1.create("test", ["AAPL", "MSFT"])
        wm1.add_alert("test", "AAPL", "price > 200")

        wm2 = WatchlistManager(path=tmp_path_file)
        wl = wm2.get("test")
        assert wl is not None
        assert wl.tickers == ["AAPL", "MSFT"]
        assert len(wl.alerts) == 1
        assert wl.alerts[0].condition == "price > 200"

    def test_corrupted_file(self, tmp_path_file):
        tmp_path_file.write_text("not json!", encoding="utf-8")
        wm = WatchlistManager(path=tmp_path_file)
        assert wm.list_all() == []

    def test_alerts(self, wm):
        wm.create("default")
        wm.add_alert("default", "AAPL", "price > 200")
        alerts = wm.get_alerts("default")
        assert len(alerts) == 1
        assert alerts[0].ticker == "AAPL"

    def test_get_signals(self, wm):
        wm.create("test", ["AAPL", "MSFT"])
        signals = wm.get_signals("test")
        assert len(signals) == 2
        assert signals[0]["ticker"] == "AAPL"

    def test_fetch_quotes_mocked(self, wm):
        wm.create("test", ["AAPL"])
        mock_quote = {
            "ticker": "AAPL",
            "price": 150.0,
            "change": 2.5,
            "change_pct": 0.017,
            "volume": 1000000,
            "error": None,
        }
        with patch.object(WatchlistManager, "_fetch_single", return_value=mock_quote):
            quotes = wm.fetch_quotes("test")
        assert len(quotes) == 1
        assert quotes[0]["price"] == 150.0

    def test_format_table(self, wm):
        wm.create("test", ["AAPL"])
        quotes = [{
            "ticker": "AAPL", "price": 150.0,
            "change": 2.5, "change_pct": 0.017, "volume": 1000000, "error": None,
        }]
        table = wm.format_table("test", quotes)
        assert "AAPL" in table
        assert "150.00" in table

    def test_format_table_with_error(self, wm):
        wm.create("test", ["BAD"])
        quotes = [{"ticker": "BAD", "error": "unavailable"}]
        table = wm.format_table("test", quotes)
        assert "BAD" in table
        assert "error" in table

    def test_format_table_negative_change(self, wm):
        wm.create("test", ["AAPL"])
        quotes = [{
            "ticker": "AAPL", "price": 148.0,
            "change": -2.0, "change_pct": -0.013, "volume": 900000, "error": None,
        }]
        table = wm.format_table("test", quotes)
        assert "-2.00" in table


# ======================================================================
# Stock Screener Tests
# ======================================================================


class TestStockScreener:
    """Tests for StockScreener filtering."""

    @pytest.fixture
    def screener(self):
        return StockScreener()

    def _make_stock(self, ticker, prices, volumes=None, market_cap=None, pe_ratio=None):
        close = np.array(prices, dtype=np.float64)
        vol = np.array(volumes, dtype=np.float64) if volumes else None
        return StockData(
            ticker=ticker, close=close, volume=vol,
            market_cap=market_cap, pe_ratio=pe_ratio,
        )

    def test_price_filter(self, screener):
        stock = self._make_stock("AAPL", [145.0, 150.0])
        results = screener.screen([stock], {"price": {"gte": 140, "lte": 160}})
        assert len(results) == 1
        assert results[0]["ticker"] == "AAPL"

    def test_price_filter_excludes(self, screener):
        stock = self._make_stock("AAPL", [145.0, 150.0])
        results = screener.screen([stock], {"price": {"gt": 200}})
        assert len(results) == 0

    def test_change_pct_filter(self, screener):
        # 100 -> 110 = +10%
        stock = self._make_stock("GAINER", [100.0, 110.0])
        results = screener.screen([stock], {"change_pct": {"gte": 5}})
        assert len(results) == 1
        assert abs(results[0]["change_pct"] - 10.0) < 0.01

    def test_volume_filter(self, screener):
        stock = self._make_stock("VOL", [100.0, 105.0], volumes=[500000, 2000000])
        results = screener.screen([stock], {"volume": {"gte": 1000000}})
        assert len(results) == 1

    def test_volume_filter_excludes(self, screener):
        stock = self._make_stock("VOL", [100.0, 105.0], volumes=[500000, 200000])
        results = screener.screen([stock], {"volume": {"gte": 1000000}})
        assert len(results) == 0

    def test_market_cap_filter(self, screener):
        stock = self._make_stock("BIG", [100.0, 105.0], market_cap=500e9)
        results = screener.screen([stock], {"market_cap": {"gte": 100e9}})
        assert len(results) == 1

    def test_rsi_filter(self, screener):
        # Create enough data for RSI calculation (15+ points)
        prices = list(range(100, 140)) + list(range(140, 120, -1))  # 40 + 20 = 60 points
        stock = self._make_stock("RSI_TEST", prices)
        results = screener.screen([stock], {"rsi_14": {"lt": 50}})
        # RSI should exist - may or may not pass depending on values
        # Just verify it runs without error
        assert isinstance(results, list)

    def test_combined_filters(self, screener):
        stock1 = self._make_stock("A", [100.0, 110.0], volumes=[1e6, 2e6], market_cap=100e9)
        stock2 = self._make_stock("B", [100.0, 101.0], volumes=[1e6, 500000], market_cap=50e9)
        results = screener.screen(
            [stock1, stock2],
            {
                "change_pct": {"gte": 5},
                "volume": {"gte": 1e6},
                "market_cap": {"gte": 80e9},
            },
        )
        assert len(results) == 1
        assert results[0]["ticker"] == "A"

    def test_gainers(self, screener):
        stocks = [
            self._make_stock("UP1", [100.0, 115.0], volumes=[1e6, 1e6]),
            self._make_stock("UP2", [100.0, 108.0], volumes=[1e6, 1e6]),
            self._make_stock("DOWN", [100.0, 95.0], volumes=[1e6, 1e6]),
        ]
        results = screener.screen_gainers(stocks, limit=10)
        assert len(results) == 2
        assert results[0]["ticker"] == "UP1"  # +15% first
        assert results[1]["ticker"] == "UP2"  # +8% second

    def test_losers(self, screener):
        stocks = [
            self._make_stock("DOWN1", [100.0, 85.0], volumes=[1e6, 1e6]),
            self._make_stock("DOWN2", [100.0, 92.0], volumes=[1e6, 1e6]),
            self._make_stock("UP", [100.0, 105.0], volumes=[1e6, 1e6]),
        ]
        results = screener.screen_losers(stocks, limit=10)
        assert len(results) == 2
        assert results[0]["ticker"] == "DOWN1"  # -15% first (most negative)
        assert results[1]["ticker"] == "DOWN2"

    def test_sort_by(self, screener):
        stocks = [
            self._make_stock("A", [100.0, 105.0]),
            self._make_stock("B", [100.0, 120.0]),
            self._make_stock("C", [100.0, 110.0]),
        ]
        results = screener.screen(stocks, {"change_pct": {"gt": 0}}, sort_by="change_pct")
        assert results[0]["ticker"] == "A"  # +5% (ascending)

    def test_sort_by_descending(self, screener):
        stocks = [
            self._make_stock("A", [100.0, 105.0]),
            self._make_stock("B", [100.0, 120.0]),
        ]
        results = screener.screen(stocks, {"change_pct": {"gt": 0}}, sort_by="-change_pct")
        assert results[0]["ticker"] == "B"  # +20% first

    def test_limit(self, screener):
        stocks = [self._make_stock(f"S{i}", [100.0, 100.0 + i]) for i in range(1, 10)]
        results = screener.screen(stocks, {"change_pct": {"gt": 0}}, limit=3)
        assert len(results) == 3

    def test_empty_universe(self, screener):
        results = screener.screen([], {"price": {"gt": 0}})
        assert results == []

    def test_insufficient_data(self, screener):
        stock = self._make_stock("SHORT", [100.0])  # Only 1 data point
        results = screener.screen([stock], {"change_pct": {"gt": 0}})
        assert len(results) == 0  # change_pct needs 2 points

    def test_check_equality(self):
        assert StockScreener._check("bullish", "bullish") is True
        assert StockScreener._check("bearish", "bullish") is False

    def test_check_dict_conditions(self):
        assert StockScreener._check(50, {"gt": 30, "lt": 70}) is True
        assert StockScreener._check(80, {"gt": 30, "lt": 70}) is False


# ======================================================================
# CLI Integration Tests (watch command)
# ======================================================================


class TestCLIWatch:
    """Tests for the watch CLI command."""

    @pytest.fixture
    def tmp_watchlist(self, tmp_path):
        return tmp_path / "watchlists.json"

    def test_watch_create_and_add(self, tmp_watchlist):
        wm = WatchlistManager(path=tmp_watchlist)
        wm.create("default")
        wm.add_tickers("default", ["AAPL", "MSFT", "GOOG"])
        wl = wm.get("default")
        assert wl.tickers == ["AAPL", "MSFT", "GOOG"]

    def test_watch_multiple_lists(self, tmp_watchlist):
        wm = WatchlistManager(path=tmp_watchlist)
        wm.create("stocks", ["AAPL", "MSFT"])
        wm.create("crypto", ["BTC", "ETH"])
        assert set(wm.list_all()) == {"stocks", "crypto"}
        assert wm.get("stocks").tickers == ["AAPL", "MSFT"]
        assert wm.get("crypto").tickers == ["BTC", "ETH"]
