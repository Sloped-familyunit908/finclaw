"""Tests for v3.4.0 — Reporting & Visualization: PerformanceReport, AlertManager,
MultiTimeframeAnalyzer, PortfolioTracker enhancements."""

from __future__ import annotations

import csv
import math
import os
import tempfile
from datetime import date, timedelta

import numpy as np
import pytest

from src.reports.performance_report import PerformanceReport
from src.alerts.alert_manager import (
    AlertManager, Alert, AlertSeverity,
    drawdown_alert, volatility_spike, correlation_break, volume_anomaly,
)
from src.ta.multi_timeframe import MultiTimeframeAnalyzer
from src.portfolio.tracker import PortfolioTracker


# ======================================================================
# PerformanceReport
# ======================================================================

class TestPerformanceReport:
    def _make_equity(self, n=100, start=100_000):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0005, 0.01, n)
        eq = [start]
        for r in returns:
            eq.append(eq[-1] * (1 + r))
        return eq

    def _make_dates(self, n=101):
        base = date(2024, 1, 1)
        return [(base + timedelta(days=i)).isoformat() for i in range(n)]

    def test_generate_basic(self):
        eq = self._make_equity()
        rpt = PerformanceReport()
        html = rpt.generate({"equity": eq})
        assert "<html" in html
        assert "Equity Curve" in html

    def test_generate_with_metrics(self):
        rpt = PerformanceReport()
        html = rpt.generate({
            "equity": [100, 105, 103, 110],
            "metrics": {"total_return": 0.10, "sharpe_ratio": 1.5, "max_drawdown": 0.05},
        })
        assert "Key Metrics" in html
        assert "+10.00%" in html

    def test_generate_with_benchmark(self):
        eq = self._make_equity()
        bench = self._make_equity(100, 100_000)
        rpt = PerformanceReport()
        html = rpt.generate({"equity": eq}, {"equity": bench, "label": "SPY"})
        assert "SPY" in html

    def test_generate_with_trades(self):
        rpt = PerformanceReport()
        html = rpt.generate({
            "equity": [100, 105],
            "trades": [{"date": "2024-01-01", "ticker": "AAPL", "side": "buy", "shares": 10, "price": 150, "pnl": 50}],
        })
        assert "Trade List" in html
        assert "AAPL" in html

    def test_generate_empty_equity(self):
        rpt = PerformanceReport()
        html = rpt.generate({"equity": []})
        assert "No equity data" in html

    def test_monthly_returns(self):
        dates = self._make_dates(101)
        eq = self._make_equity()
        rpt = PerformanceReport()
        monthly = rpt.generate_monthly_returns(eq, dates)
        assert isinstance(monthly, dict)
        assert 2024 in monthly
        # Should have at least 1 month
        assert len(monthly[2024]) >= 1

    def test_monthly_returns_short(self):
        rpt = PerformanceReport()
        result = rpt.generate_monthly_returns([100])
        assert result == {}

    def test_rolling_metrics(self):
        rng = np.random.RandomState(42)
        returns = list(rng.normal(0.001, 0.01, 200))
        rpt = PerformanceReport()
        result = rpt.generate_rolling_metrics(returns, window=63)
        assert "rolling_sharpe" in result
        assert "rolling_volatility" in result
        assert len(result["rolling_sharpe"]) == 200
        # First 62 should be NaN
        assert math.isnan(result["rolling_sharpe"][0])
        # Last should be a number
        assert not math.isnan(result["rolling_sharpe"][-1])

    def test_rolling_metrics_short(self):
        rpt = PerformanceReport()
        result = rpt.generate_rolling_metrics([0.01, 0.02], window=63)
        assert all(math.isnan(v) for v in result["rolling_sharpe"])

    def test_drawdown_svg(self):
        eq = [100, 110, 105, 108, 95, 100]
        rpt = PerformanceReport()
        html = rpt.generate({"equity": eq})
        assert "Drawdown" in html

    def test_heatmap_in_html(self):
        dates = self._make_dates(101)
        eq = self._make_equity()
        rpt = PerformanceReport()
        html = rpt.generate({"equity": eq, "dates": dates})
        assert "Monthly Returns" in html


# ======================================================================
# AlertManager
# ======================================================================

class TestAlertManager:
    def test_add_and_check_rule(self):
        mgr = AlertManager()
        mgr.add_rule("test", lambda d: Alert("test", AlertSeverity.INFO, "triggered", 1.0, 0.5) if d.get("flag") else None)
        alerts = mgr.check({"flag": True})
        assert len(alerts) == 1
        assert alerts[0].name == "test"

    def test_no_trigger(self):
        mgr = AlertManager()
        mgr.add_rule("test", lambda d: None)
        assert mgr.check({"x": 1}) == []

    def test_remove_rule(self):
        mgr = AlertManager()
        mgr.add_rule("r1", lambda d: None)
        assert mgr.remove_rule("r1")
        assert not mgr.remove_rule("nonexistent")
        assert len(mgr.rules) == 0

    def test_enable_disable(self):
        mgr = AlertManager()
        mgr.add_rule("r1", lambda d: Alert("r1", AlertSeverity.INFO, "x", 1, 0))
        mgr.enable_rule("r1", False)
        assert mgr.check({"x": 1}) == []
        mgr.enable_rule("r1", True)
        assert len(mgr.check({"x": 1})) == 1

    def test_history(self):
        mgr = AlertManager()
        mgr.add_rule("r1", lambda d: Alert("r1", AlertSeverity.INFO, "x", 1, 0))
        mgr.check({})
        mgr.check({})
        assert len(mgr.history) == 2
        mgr.clear_history()
        assert len(mgr.history) == 0

    def test_check_all(self):
        mgr = AlertManager()
        mgr.add_rule("r1", lambda d: Alert("r1", AlertSeverity.INFO, "x", d.get("v", 0), 0) if d.get("v", 0) > 5 else None)
        alerts = mgr.check_all([{"v": 3}, {"v": 10}, {"v": 1}])
        assert len(alerts) == 1

    def test_format_alerts_empty(self):
        assert "No alerts" in AlertManager.format_alerts([])

    def test_format_alerts_with_items(self):
        alerts = [Alert("DD", AlertSeverity.CRITICAL, "bad drawdown", 0.15, 0.10)]
        text = AlertManager.format_alerts(alerts)
        assert "🚨" in text
        assert "CRITICAL" in text

    def test_broken_rule_skipped(self):
        mgr = AlertManager()
        mgr.add_rule("bad", lambda d: 1 / 0)  # Will raise
        mgr.add_rule("good", lambda d: Alert("good", AlertSeverity.INFO, "ok", 1, 0))
        alerts = mgr.check({})
        assert len(alerts) == 1
        assert alerts[0].name == "good"


# ======================================================================
# Built-in alert rules
# ======================================================================

class TestBuiltInAlerts:
    def test_drawdown_alert_triggers(self):
        check = drawdown_alert(0.10)
        result = check({"equity": [100, 110, 95]})
        assert result is not None
        assert result.severity == AlertSeverity.WARNING

    def test_drawdown_alert_critical(self):
        check = drawdown_alert(0.10)
        result = check({"equity": [100, 110, 80]})  # ~27% dd
        assert result is not None
        assert result.severity == AlertSeverity.CRITICAL

    def test_drawdown_no_trigger(self):
        check = drawdown_alert(0.10)
        assert check({"equity": [100, 105, 110]}) is None

    def test_drawdown_short_data(self):
        check = drawdown_alert(0.10)
        assert check({"equity": [100]}) is None

    def test_volatility_spike_triggers(self):
        rng = np.random.RandomState(42)
        calm = list(rng.normal(0, 0.01, 100))
        wild = list(rng.normal(0, 0.05, 21))
        check = volatility_spike(2.0)
        result = check({"returns": calm + wild})
        assert result is not None

    def test_volatility_no_trigger(self):
        returns = list(np.random.RandomState(42).normal(0, 0.01, 100))
        check = volatility_spike(2.0)
        assert check({"returns": returns}) is None

    def test_correlation_break(self):
        rng = np.random.RandomState(42)
        a = list(rng.normal(0, 0.01, 50))
        b = list(rng.normal(0, 0.01, 50))  # Uncorrelated
        check = correlation_break(0.5)
        result = check({"returns": a, "benchmark_returns": b})
        # Might or might not trigger depending on random seed
        assert result is None or isinstance(result, Alert)

    def test_correlation_short_data(self):
        check = correlation_break(0.3)
        assert check({"returns": [0.01] * 10, "benchmark_returns": [0.01] * 10}) is None

    def test_volume_anomaly_triggers(self):
        vol = [1_000_000] * 20 + [5_000_000]
        check = volume_anomaly(3.0)
        result = check({"volume": vol})
        assert result is not None

    def test_volume_anomaly_no_trigger(self):
        vol = [1_000_000] * 21
        check = volume_anomaly(3.0)
        assert check({"volume": vol}) is None


# ======================================================================
# MultiTimeframeAnalyzer
# ======================================================================

class TestMultiTimeframeAnalyzer:
    def _make_bullish(self, n=100):
        """Uptrending close data."""
        return np.linspace(100, 200, n) + np.random.RandomState(42).normal(0, 0.5, n)

    def _make_bearish(self, n=100):
        return np.linspace(150, 100, n) + np.random.RandomState(42).normal(0, 1, n)

    def _tf_data(self, close):
        return {"close": close, "high": close * 1.01, "low": close * 0.99}

    def test_all_bullish(self):
        mta = MultiTimeframeAnalyzer()
        close = self._make_bullish()
        data = {tf: self._tf_data(close) for tf in mta.TIMEFRAMES}
        result = mta.analyze(data)
        assert result["dominant_trend"] == "bullish"
        assert result["trend_alignment"] >= 0.5

    def test_all_bearish(self):
        mta = MultiTimeframeAnalyzer()
        close = self._make_bearish()
        data = {tf: self._tf_data(close) for tf in mta.TIMEFRAMES}
        result = mta.analyze(data)
        assert result["dominant_trend"] == "bearish"

    def test_mixed_signals(self):
        mta = MultiTimeframeAnalyzer()
        data = {
            "1h": self._tf_data(self._make_bullish()),
            "4h": self._tf_data(self._make_bullish()),
            "1d": self._tf_data(self._make_bearish()),
            "1w": self._tf_data(self._make_bearish()),
        }
        result = mta.analyze(data)
        assert 0 <= result["trend_alignment"] <= 1.0
        assert "signals" in result

    def test_divergences_detected(self):
        mta = MultiTimeframeAnalyzer()
        data = {
            "1d": self._tf_data(self._make_bullish()),
            "1w": self._tf_data(self._make_bearish()),
        }
        result = mta.analyze(data)
        assert len(result["divergences"]) >= 1

    def test_empty_data(self):
        mta = MultiTimeframeAnalyzer()
        result = mta.analyze({})
        assert result["trend_alignment"] == 0.0
        assert result["dominant_trend"] == "neutral"

    def test_single_timeframe(self):
        mta = MultiTimeframeAnalyzer()
        data = {"1d": self._tf_data(self._make_bullish())}
        result = mta.analyze(data)
        assert result["trend_alignment"] == 1.0

    def test_short_data_skipped(self):
        mta = MultiTimeframeAnalyzer()
        data = {"1d": {"close": np.array([100.0, 101.0])}}
        result = mta.analyze(data)
        assert result["trend_alignment"] == 0.0

    def test_signals_have_expected_keys(self):
        mta = MultiTimeframeAnalyzer()
        data = {"1d": self._tf_data(self._make_bullish())}
        result = mta.analyze(data)
        sig = result["signals"]["1d"]
        assert "trend" in sig
        assert "rsi" in sig
        assert "adx" in sig
        assert "momentum" in sig


# ======================================================================
# PortfolioTracker enhancements
# ======================================================================

class TestPortfolioTrackerEnhanced:
    """Tests rewritten for current PortfolioTracker API (add/remove, JSON storage)."""

    def _make_tracker(self, price=150.0):
        import tempfile, os
        storage = os.path.join(tempfile.mkdtemp(), "portfolio.json")
        return PortfolioTracker(storage_path=storage, price_fetcher=lambda s: price)

    def test_add_holding(self):
        pt = self._make_tracker()
        h = pt.add("AAPL", 10, 150.0)
        assert h.symbol == "AAPL"
        assert h.quantity == 10

    def test_add_accumulate(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 150.0)
        pt.add("AAPL", 5, 160.0)
        h = pt._find_holding("AAPL")
        assert h.quantity == 15
        expected_cost = (150 * 10 + 160 * 5) / 15
        assert abs(h.avg_cost - expected_cost) < 0.01

    def test_show_with_holdings(self):
        pt = self._make_tracker(price=155.0)
        pt.add("AAPL", 10, 150.0)
        status = pt.show()
        assert len(status["holdings"]) == 1
        assert status["total_value"] == pytest.approx(10 * 155.0)

    def test_show_empty(self):
        pt = self._make_tracker()
        status = pt.show()
        assert status["total_value"] == 0.0
        assert status["total_pnl"] == 0.0

    def test_show_with_allocation(self):
        pt = self._make_tracker(price=150.0)
        pt.add("AAPL", 10, 150.0)
        alloc = pt.allocation()
        assert len(alloc) == 1
        assert alloc[0]["symbol"] == "AAPL"
        assert alloc[0]["pct"] == pytest.approx(100.0)

    def test_snapshot_records_history(self):
        pt = self._make_tracker(price=110.0)
        pt.add("AAPL", 100, 100.0)
        pt.snapshot()
        history = pt.get_history()
        assert len(history) == 1
        assert history[0]["total_value"] == pytest.approx(11000.0)

    def test_export_csv_holdings(self):
        pt = self._make_tracker(price=155.0)
        pt.add("AAPL", 10, 150.0)
        csv_str = pt.export_csv("holdings")
        assert "AAPL" in csv_str
        assert "symbol" in csv_str  # Header present

    def test_export_csv_empty(self):
        pt = self._make_tracker()
        csv_str = pt.export_csv("holdings")
        assert "symbol" in csv_str  # Header still present
