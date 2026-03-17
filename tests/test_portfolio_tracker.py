"""Tests for the portfolio tracker module."""

import json
import os
import tempfile

import pytest

from src.portfolio.tracker import PortfolioTracker, Holding, Alert


# ── helpers ─────────────────────────────────────────────────────

def _make_tracker(tmp_path, prices=None, name="main"):
    """Create a tracker with a temp file and mock price fetcher."""
    storage = os.path.join(str(tmp_path), "portfolio.json")
    mock_prices = prices or {}

    def fetcher(symbol):
        return mock_prices.get(symbol.upper())

    return PortfolioTracker(storage_path=storage, portfolio_name=name, price_fetcher=fetcher)


# ── add / remove ────────────────────────────────────────────────

class TestAddRemove:
    def test_add_new(self, tmp_path):
        t = _make_tracker(tmp_path)
        h = t.add("BTC", 0.5, buy_price=42000)
        assert h.symbol == "BTC"
        assert h.quantity == 0.5
        assert h.avg_cost == 42000

    def test_add_increases_quantity_and_avg_cost(self, tmp_path):
        t = _make_tracker(tmp_path)
        t.add("BTC", 1.0, buy_price=40000)
        h = t.add("BTC", 1.0, buy_price=50000)
        assert h.quantity == 2.0
        assert h.avg_cost == 45000.0

    def test_add_case_insensitive(self, tmp_path):
        t = _make_tracker(tmp_path)
        t.add("btc", 1.0, buy_price=100)
        h = t.add("BTC", 1.0, buy_price=200)
        assert h.quantity == 2.0

    def test_add_zero_quantity_raises(self, tmp_path):
        t = _make_tracker(tmp_path)
        with pytest.raises(ValueError, match="positive"):
            t.add("BTC", 0)

    def test_remove(self, tmp_path):
        t = _make_tracker(tmp_path)
        t.add("ETH", 10, buy_price=3000)
        h = t.remove("ETH", 3)
        assert h.quantity == 7.0

    def test_remove_all(self, tmp_path):
        t = _make_tracker(tmp_path)
        t.add("ETH", 5, buy_price=3000)
        h = t.remove("ETH", 5)
        assert h is None
        assert len(t.data.holdings) == 0

    def test_remove_nonexistent_raises(self, tmp_path):
        t = _make_tracker(tmp_path)
        with pytest.raises(ValueError, match="No holding"):
            t.remove("XYZ", 1)

    def test_persistence(self, tmp_path):
        storage = os.path.join(str(tmp_path), "pf.json")
        t1 = PortfolioTracker(storage_path=storage, price_fetcher=lambda s: None)
        t1.add("AAPL", 10, buy_price=150)

        t2 = PortfolioTracker(storage_path=storage, price_fetcher=lambda s: None)
        t2.load()
        assert len(t2.data.holdings) == 1
        assert t2.data.holdings[0].symbol == "AAPL"


# ── show / P&L ──────────────────────────────────────────────────

class TestShow:
    def test_show_with_prices(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000, "ETH": 3500})
        t.add("BTC", 1.0, buy_price=42000)
        t.add("ETH", 10.0, buy_price=3000)

        status = t.show()
        assert len(status["holdings"]) == 2
        assert status["total_value"] == 50000 + 35000
        assert status["total_pnl"] == (50000 - 42000) + (35000 - 30000)

    def test_show_empty(self, tmp_path):
        t = _make_tracker(tmp_path)
        status = t.show()
        assert status["holdings"] == []
        assert status["total_value"] == 0

    def test_pnl_pct(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"X": 200})
        t.add("X", 10, buy_price=100)
        status = t.show()
        assert abs(status["total_pnl_pct"] - 1.0) < 1e-9  # 100% gain


# ── allocation ──────────────────────────────────────────────────

class TestAllocation:
    def test_allocation_pct(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"A": 100, "B": 100})
        t.add("A", 3, buy_price=50)
        t.add("B", 1, buy_price=50)
        alloc = t.allocation()
        assert len(alloc) == 2
        total_pct = sum(a["pct"] for a in alloc)
        assert abs(total_pct - 100.0) < 0.01


# ── history ─────────────────────────────────────────────────────

class TestHistory:
    def test_snapshot(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000})
        t.add("BTC", 1.0, buy_price=42000)
        snap = t.snapshot()
        assert snap.total_value == 50000
        assert snap.holdings_count == 1

        history = t.get_history()
        assert len(history) == 1

    def test_snapshot_replaces_same_day(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000})
        t.add("BTC", 1.0, buy_price=42000)
        t.snapshot()
        t.snapshot()
        assert len(t.get_history()) == 1


# ── alerts ──────────────────────────────────────────────────────

class TestAlerts:
    def test_add_alert_above(self, tmp_path):
        t = _make_tracker(tmp_path)
        a = t.add_alert("BTC", above=50000)
        assert a.condition == "above"
        assert a.threshold == 50000

    def test_check_alerts_triggers(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 55000})
        t.add_alert("BTC", above=50000)
        triggered = t.check_alerts()
        assert len(triggered) == 1
        assert triggered[0]["price"] == 55000

    def test_check_alerts_no_trigger(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 45000})
        t.add_alert("BTC", above=50000)
        triggered = t.check_alerts()
        assert len(triggered) == 0

    def test_alert_below(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"ETH": 2000})
        t.add_alert("ETH", below=2500)
        triggered = t.check_alerts()
        assert len(triggered) == 1

    def test_alert_triggers_only_once(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 55000})
        t.add_alert("BTC", above=50000)
        t.check_alerts()
        triggered = t.check_alerts()
        assert len(triggered) == 0


# ── export ──────────────────────────────────────────────────────

class TestExport:
    def test_export_csv_holdings(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000})
        t.add("BTC", 1.0, buy_price=42000)
        csv_str = t.export_csv("holdings")
        assert "BTC" in csv_str
        assert "symbol" in csv_str  # header

    def test_export_csv_history(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000})
        t.add("BTC", 1.0, buy_price=42000)
        t.snapshot()
        csv_str = t.export_csv("history")
        assert "total_value" in csv_str

    def test_export_to_file(self, tmp_path):
        t = _make_tracker(tmp_path, prices={"BTC": 50000})
        t.add("BTC", 1.0, buy_price=42000)
        outpath = os.path.join(str(tmp_path), "out.csv")
        t.export_to_file(outpath)
        assert os.path.exists(outpath)
        with open(outpath) as f:
            content = f.read()
        assert "BTC" in content


# ── multiple portfolios ────────────────────────────────────────

class TestMultiplePortfolios:
    def test_separate_portfolios(self, tmp_path):
        storage = os.path.join(str(tmp_path), "pf.json")
        t1 = PortfolioTracker(storage_path=storage, portfolio_name="main", price_fetcher=lambda s: 100)
        t2 = PortfolioTracker(storage_path=storage, portfolio_name="defi", price_fetcher=lambda s: 100)

        t1.add("AAPL", 10, buy_price=150)
        t2.add("ETH", 5, buy_price=3000)

        # Reload
        t1.load()
        t2.load()
        assert len(t1.data.holdings) == 1
        assert t1.data.holdings[0].symbol == "AAPL"
        assert len(t2.data.holdings) == 1
        assert t2.data.holdings[0].symbol == "ETH"
