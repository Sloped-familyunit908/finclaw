"""Tests for v5.4.0 — Advanced Screener, Watchlist Manager, Market Scanner."""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candles(n: int = 100, base: float = 100.0, seed: int = 42) -> list[dict]:
    """Generate synthetic OHLCV candles."""
    rng = np.random.RandomState(seed)
    candles = []
    price = base
    for i in range(n):
        change = rng.normal(0, 1.5)
        o = price
        c = price + change
        h = max(o, c) + abs(rng.normal(0, 0.5))
        l = min(o, c) - abs(rng.normal(0, 0.5))
        vol = max(1000, int(rng.normal(1_000_000, 300_000)))
        candles.append({"timestamp": f"2024-01-{i+1:02d}", "open": o, "high": h, "low": l, "close": c, "volume": vol})
        price = c
    return candles


class FakeAdapter:
    """Fake exchange adapter for testing."""
    exchange_type = "stock_us"
    name = "fake"

    def __init__(self, candles: list[dict] | None = None, ticker: dict | None = None, symbols: list[str] | None = None):
        self._candles = candles or _make_candles()
        self._ticker = ticker or {"symbol": "FAKE", "last": 100.0, "bid": 99.9, "ask": 100.1, "volume": 1000000}
        self._symbols = symbols or ["AAPL", "MSFT", "GOOGL"]

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[dict]:
        return self._candles[-limit:]

    def get_ticker(self, symbol: str) -> dict:
        return {**self._ticker, "symbol": symbol}

    def list_symbols(self) -> list[str]:
        return self._symbols


class FakeRegistry:
    def get(self, name: str = "yahoo", config=None):
        return FakeAdapter()


# ===========================================================================
# Advanced Screener Tests
# ===========================================================================

class TestAdvancedScreener:
    def _make_screener(self, candles=None, symbols=None):
        from src.screener.advanced import AdvancedScreener
        adapter = FakeAdapter(candles=candles, symbols=symbols)
        registry = MagicMock()
        registry.get.return_value = adapter
        return AdvancedScreener(exchange_registry=registry)

    def test_screen_basic(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "rsi_14", "op": ">", "value": 0}], universe="AAPL")
        assert isinstance(results, list)

    def test_screen_rsi_below(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "rsi_14", "op": "<", "value": 100}], universe="AAPL")
        # RSI is always < 100, should match
        assert len(results) >= 1

    def test_screen_rsi_above_impossible(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "rsi_14", "op": ">", "value": 100}], universe="AAPL")
        assert len(results) == 0

    def test_screen_volume_ratio(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "volume_ratio", "op": ">", "value": 0}], universe="AAPL")
        assert isinstance(results, list)

    def test_screen_price_change_5d(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "price_change_5d", "op": ">", "value": -1.0}], universe="AAPL")
        assert len(results) >= 1

    def test_screen_multiple_criteria(self):
        screener = self._make_screener()
        criteria = [
            {"field": "rsi_14", "op": "<", "value": 100},
            {"field": "volume_ratio", "op": ">", "value": 0},
        ]
        results = screener.screen(criteria, universe="AAPL")
        assert isinstance(results, list)

    def test_screen_sp500_universe(self):
        screener = self._make_screener()
        results = screener.screen([{"field": "rsi_14", "op": "<", "value": 100}], universe="sp500")
        assert isinstance(results, list)

    def test_top_movers(self):
        screener = self._make_screener(symbols=["A", "B", "C"])
        movers = screener.top_movers("yahoo", n=5)
        assert isinstance(movers, list)
        for m in movers:
            assert "symbol" in m
            assert "change_pct" in m

    def test_top_movers_limited(self):
        screener = self._make_screener(symbols=["A", "B", "C"])
        movers = screener.top_movers("yahoo", n=2)
        assert len(movers) <= 2

    def test_unusual_volume(self):
        # Create candles with last volume spike
        candles = _make_candles(30)
        candles[-1]["volume"] = 10_000_000  # spike
        screener = self._make_screener(candles=candles, symbols=["SPY"])
        results = screener.unusual_volume("yahoo", threshold=2.0)
        assert isinstance(results, list)

    def test_unusual_volume_no_match(self):
        screener = self._make_screener(symbols=["SPY"])
        results = screener.unusual_volume("yahoo", threshold=999.0)
        assert len(results) == 0

    def test_new_highs_lows(self):
        screener = self._make_screener(candles=_make_candles(300), symbols=["AAPL"])
        results = screener.new_highs_lows("yahoo", period=52)
        assert isinstance(results, list)

    def test_sector_performance(self):
        screener = self._make_screener()
        perf = screener.sector_performance(period="1w")
        assert isinstance(perf, dict)

    def test_correlation_scan(self):
        screener = self._make_screener()
        results = screener.correlation_scan("AAPL", ["MSFT", "GOOGL"], period=20)
        assert isinstance(results, list)

    def test_correlation_scan_sorted(self):
        screener = self._make_screener()
        results = screener.correlation_scan("AAPL", ["MSFT", "GOOGL", "AMZN"], period=20)
        if len(results) >= 2:
            # Should be sorted by abs correlation descending
            assert abs(results[0]["correlation"]) >= abs(results[-1]["correlation"])

    def test_field_calculators_rsi(self):
        from src.screener.advanced import AdvancedScreener
        candles = _make_candles(50)
        val = AdvancedScreener._calc_rsi_14(candles)
        assert val is not None
        assert 0 <= val <= 100

    def test_field_calculators_atr(self):
        from src.screener.advanced import AdvancedScreener
        candles = _make_candles(50)
        val = AdvancedScreener._calc_atr_14(candles)
        assert val is not None
        assert val >= 0

    def test_field_calculators_bb_width(self):
        from src.screener.advanced import AdvancedScreener
        candles = _make_candles(50)
        val = AdvancedScreener._calc_bb_width(candles)
        assert val is not None
        assert val > 0

    def test_field_sma_20(self):
        from src.screener.advanced import AdvancedScreener
        assert AdvancedScreener._calc_sma_20(_make_candles(50)) is not None

    def test_field_sma_50(self):
        from src.screener.advanced import AdvancedScreener
        assert AdvancedScreener._calc_sma_50(_make_candles(60)) is not None

    def test_field_above_sma_20(self):
        from src.screener.advanced import AdvancedScreener
        val = AdvancedScreener._calc_above_sma_20(_make_candles(50))
        assert isinstance(val, bool)

    def test_matches_gt(self):
        from src.screener.advanced import AdvancedScreener
        assert AdvancedScreener._matches({"rsi_14": 25}, [{"field": "rsi_14", "op": "<", "value": 30}])

    def test_matches_fails(self):
        from src.screener.advanced import AdvancedScreener
        assert not AdvancedScreener._matches({"rsi_14": 50}, [{"field": "rsi_14", "op": "<", "value": 30}])

    def test_no_registry(self):
        from src.screener.advanced import AdvancedScreener
        screener = AdvancedScreener(exchange_registry=None)
        assert screener.screen([{"field": "rsi_14", "op": "<", "value": 30}], universe="AAPL") == []

    def test_resolve_universe_dow30(self):
        from src.screener.advanced import AdvancedScreener
        screener = AdvancedScreener()
        syms = screener._resolve_universe("dow30")
        assert len(syms) == 30

    def test_resolve_universe_custom(self):
        from src.screener.advanced import AdvancedScreener
        screener = AdvancedScreener()
        syms = screener._resolve_universe("AAPL,MSFT")
        assert syms == ["AAPL", "MSFT"]


# ===========================================================================
# Watchlist Manager Tests
# ===========================================================================

class TestWatchlistManager:
    def _make_manager(self, tmpdir) -> "WatchlistManager":
        from src.screener.watchlist import WatchlistManager
        return WatchlistManager(path=str(Path(tmpdir) / "watchlists.json"))

    def test_create(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wl = wm.create("test", ["AAPL", "MSFT"])
        assert wl.name == "test"
        assert wl.symbols == ["AAPL", "MSFT"]

    def test_create_empty(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wl = wm.create("empty")
        assert wl.symbols == []

    def test_add_symbol(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test")
        wm.add("test", "AAPL")
        wl = wm.get("test")
        assert "AAPL" in wl.symbols

    def test_add_duplicate(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL"])
        wm.add("test", "aapl")  # lowercase
        wl = wm.get("test")
        assert wl.symbols.count("AAPL") == 1

    def test_remove_symbol(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL", "MSFT"])
        wm.remove("test", "AAPL")
        wl = wm.get("test")
        assert "AAPL" not in wl.symbols
        assert "MSFT" in wl.symbols

    def test_remove_nonexistent(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL"])
        wm.remove("test", "GOOGL")  # no error
        assert len(wm.get("test").symbols) == 1

    def test_list_all(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("a")
        wm.create("b")
        assert set(wm.list_all()) == {"a", "b"}

    def test_delete(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test")
        assert wm.delete("test") is True
        assert wm.get("test") is None

    def test_delete_nonexistent(self, tmp_path):
        wm = self._make_manager(tmp_path)
        assert wm.delete("nope") is False

    def test_persistence(self, tmp_path):
        from src.screener.watchlist import WatchlistManager
        path = str(Path(tmp_path) / "wl.json")
        wm1 = WatchlistManager(path=path)
        wm1.create("persist", ["AAPL"])
        wm2 = WatchlistManager(path=path)
        assert wm2.get("persist").symbols == ["AAPL"]

    def test_get_quotes_no_registry(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL"])
        quotes = wm.get_quotes("test")
        assert len(quotes) == 1

    def test_get_quotes_not_found(self, tmp_path):
        wm = self._make_manager(tmp_path)
        with pytest.raises(KeyError):
            wm.get_quotes("nonexistent")

    def test_export_csv(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL", "MSFT"])
        csv_str = wm.export("test", format="csv")
        assert "AAPL" in csv_str
        assert "MSFT" in csv_str

    def test_export_json(self, tmp_path):
        wm = self._make_manager(tmp_path)
        wm.create("test", ["AAPL"])
        json_str = wm.export("test", format="json")
        data = json.loads(json_str)
        assert data["name"] == "test"
        assert "AAPL" in data["symbols"]

    def test_import_csv(self, tmp_path):
        wm = self._make_manager(tmp_path)
        csv_file = Path(tmp_path) / "import.csv"
        csv_file.write_text("symbol\nAAPL\nMSFT\n", encoding="utf-8")
        wl = wm.import_from(str(csv_file))
        assert "AAPL" in wl.symbols
        assert "MSFT" in wl.symbols

    def test_import_json(self, tmp_path):
        wm = self._make_manager(tmp_path)
        json_file = Path(tmp_path) / "import.json"
        json_file.write_text(json.dumps({"name": "imported", "symbols": ["GOOGL"]}), encoding="utf-8")
        wl = wm.import_from(str(json_file))
        assert wl.name == "imported"
        assert "GOOGL" in wl.symbols

    def test_add_to_nonexistent_raises(self, tmp_path):
        wm = self._make_manager(tmp_path)
        with pytest.raises(KeyError):
            wm.add("nope", "AAPL")


# ===========================================================================
# Market Scanner Tests
# ===========================================================================

class TestMarketScanner:
    def test_add_rule(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner()
        scanner.add_rule("test", lambda d: True)
        assert len(scanner.rules) == 1

    def test_remove_rule(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner()
        scanner.add_rule("test", lambda d: True)
        assert scanner.remove_rule("test") is True
        assert len(scanner.rules) == 0

    def test_remove_nonexistent(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner()
        assert scanner.remove_rule("nope") is False

    def test_clear_rules(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner()
        scanner.add_rule("a", lambda d: True)
        scanner.add_rule("b", lambda d: True)
        scanner.clear_rules()
        assert len(scanner.rules) == 0

    def test_scan_once_no_registry(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner()
        scanner.add_rule("test", lambda d: True)
        results = scanner.scan_once(["AAPL"])
        assert results == []

    def test_scan_once_with_match(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("always", lambda d: True, action="alert")
        results = scanner.scan_once(["AAPL"])
        assert len(results) >= 1
        assert results[0].symbol == "AAPL"
        assert results[0].rule_name == "always"

    def test_scan_once_no_match(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("never", lambda d: False)
        results = scanner.scan_once(["AAPL"])
        assert results == []

    def test_rsi_below_builder(self):
        from src.screener.scanner import MarketScanner
        cond = MarketScanner.rsi_below(30)
        assert cond({"rsi_14": 25}) is True
        assert cond({"rsi_14": 50}) is False

    def test_rsi_above_builder(self):
        from src.screener.scanner import MarketScanner
        cond = MarketScanner.rsi_above(70)
        assert cond({"rsi_14": 80}) is True
        assert cond({"rsi_14": 50}) is False

    def test_volume_above_builder(self):
        from src.screener.scanner import MarketScanner
        cond = MarketScanner.volume_above(2.0)
        assert cond({"volume_ratio": 3.0}) is True
        assert cond({"volume_ratio": 1.5}) is False

    def test_price_change_above_builder(self):
        from src.screener.scanner import MarketScanner
        cond = MarketScanner.price_change_above(0.05)
        assert cond({"price_change_1d": 0.1}) is True
        assert cond({"price_change_1d": 0.01}) is False

    def test_price_change_below_builder(self):
        from src.screener.scanner import MarketScanner
        cond = MarketScanner.price_change_below(-0.05)
        assert cond({"price_change_1d": -0.1}) is True
        assert cond({"price_change_1d": 0.01}) is False

    def test_history(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("test", lambda d: True)
        scanner.scan_once(["AAPL"])
        assert len(scanner.history) >= 1

    def test_scan_result_timestamp(self):
        from src.screener.scanner import ScanResult
        r = ScanResult(rule_name="test", symbol="AAPL", action="alert")
        assert r.timestamp > 0

    def test_run_continuous_limited(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("test", lambda d: True)
        results = scanner.run_continuous(["AAPL"], interval=0, max_iterations=2)
        assert len(results) >= 2

    def test_run_continuous_callback(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("test", lambda d: True)
        called = []
        scanner.run_continuous(["AAPL"], interval=0, max_iterations=1, callback=lambda r: called.append(len(r)))
        assert len(called) >= 1

    def test_multiple_rules(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("r1", lambda d: True)
        scanner.add_rule("r2", lambda d: True)
        results = scanner.scan_once(["AAPL"])
        rule_names = {r.rule_name for r in results}
        assert "r1" in rule_names
        assert "r2" in rule_names

    def test_multiple_symbols(self):
        from src.screener.scanner import MarketScanner
        scanner = MarketScanner(exchange_registry=FakeRegistry())
        scanner.add_rule("test", lambda d: True)
        results = scanner.scan_once(["AAPL", "MSFT", "GOOGL"])
        symbols = {r.symbol for r in results}
        assert len(symbols) == 3


# ===========================================================================
# Import / Module Tests
# ===========================================================================

class TestModuleImports:
    def test_import_advanced_screener(self):
        from src.screener import AdvancedScreener
        assert AdvancedScreener is not None

    def test_import_watchlist_manager(self):
        from src.screener import WatchlistManager
        assert WatchlistManager is not None

    def test_import_market_scanner(self):
        from src.screener import MarketScanner
        assert MarketScanner is not None

    def test_import_scan_result(self):
        from src.screener import ScanResult
        assert ScanResult is not None

    def test_import_watchlist_dataclass(self):
        from src.screener import Watchlist
        wl = Watchlist(name="test", symbols=["AAPL"])
        assert wl.name == "test"
