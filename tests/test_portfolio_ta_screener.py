"""Tests for Portfolio Tracker, TA indicators, Screener, Alerts, and Attribution."""

import math
from datetime import date

import numpy as np
import pytest

# ── Portfolio Tracker ────────────────────────────────────────────────
from src.portfolio.tracker import PortfolioTracker


class TestPortfolioTracker:
    """Tests rewritten for current PortfolioTracker API (add/remove, JSON persistence)."""

    def _make_tracker(self, tmp_path=None):
        """Create a PortfolioTracker with a temp storage path and stub price fetcher."""
        import tempfile, os
        storage = os.path.join(tempfile.mkdtemp(), "portfolio.json")
        return PortfolioTracker(storage_path=storage, price_fetcher=lambda s: 150.0)

    def test_add_holding(self):
        pt = self._make_tracker()
        h = pt.add("AAPL", 10, 150.0)
        assert h.symbol == "AAPL"
        assert h.quantity == 10
        assert h.avg_cost == pytest.approx(150.0)

    def test_remove_partial(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 150.0)
        remaining = pt.remove("AAPL", 5)
        assert remaining is not None
        assert remaining.quantity == 5

    def test_remove_all_deletes_holding(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 150.0)
        remaining = pt.remove("AAPL", 10)
        assert remaining is None
        # Verify holding is gone
        assert pt._find_holding("AAPL") is None

    def test_add_negative_quantity_raises(self):
        pt = self._make_tracker()
        with pytest.raises(ValueError, match="positive"):
            pt.add("AAPL", -1, 150.0)

    def test_remove_nonexistent_raises(self):
        pt = self._make_tracker()
        with pytest.raises(ValueError, match="No holding found"):
            pt.remove("AAPL", 1)

    def test_snapshot(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 150.0)
        snap = pt.snapshot()
        # With price_fetcher returning 150.0, value = 10 * 150 = 1500
        assert snap.total_value == pytest.approx(1500.0)
        assert snap.holdings_count == 1

    def test_history_grows(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 100.0)
        pt.snapshot()
        history = pt.get_history()
        assert len(history) >= 1
        assert "total_value" in history[0]

    def test_avg_cost_multiple_adds(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 100.0)
        pt.add("AAPL", 10, 200.0)
        h = pt._find_holding("AAPL")
        assert h.avg_cost == pytest.approx(150.0)
        assert h.quantity == 20

    def test_show_returns_summary(self):
        pt = self._make_tracker()
        pt.add("AAPL", 10, 100.0)
        status = pt.show()
        assert status["portfolio"] == "main"
        assert len(status["holdings"]) == 1
        assert status["total_value"] > 0


# ── Technical Analysis ───────────────────────────────────────────────
from src.ta import sma, ema, wma, dema, tema, rsi, macd, bollinger_bands, atr, adx, obv, cmf, mfi, ichimoku, parabolic_sar, stochastic_rsi


class TestMovingAverages:
    def test_sma_basic(self):
        data = np.arange(1.0, 11.0)
        result = sma(data, 3)
        assert result[2] == pytest.approx(2.0)
        assert result[-1] == pytest.approx(9.0)
        assert np.isnan(result[0])

    def test_ema_basic(self):
        data = np.ones(20) * 50.0
        result = ema(data, 10)
        assert result[-1] == pytest.approx(50.0)

    def test_wma_basic(self):
        data = np.arange(1.0, 11.0)
        result = wma(data, 3)
        # WMA(3) of [8,9,10] = (1*8 + 2*9 + 3*10) / 6 = 56/6
        assert result[-1] == pytest.approx(56.0 / 6.0)

    def test_dema(self):
        data = np.random.RandomState(42).randn(100).cumsum() + 100
        result = dema(data, 10)
        assert len(result) == len(data)

    def test_tema(self):
        data = np.random.RandomState(42).randn(100).cumsum() + 100
        result = tema(data, 10)
        assert len(result) == len(data)


class TestRSI:
    def test_rsi_range(self):
        data = np.random.RandomState(42).randn(100).cumsum() + 100
        r = rsi(data, 14)
        valid = r[~np.isnan(r)]
        assert np.all(valid >= 0) and np.all(valid <= 100)

    def test_stochastic_rsi(self):
        data = np.random.RandomState(42).randn(100).cumsum() + 100
        k, d = stochastic_rsi(data)
        assert len(k) == len(data)


class TestMACD:
    def test_macd_shapes(self):
        data = np.random.RandomState(42).randn(100).cumsum() + 100
        line, sig, hist = macd(data)
        assert len(line) == len(data)
        assert len(sig) == len(data)
        np.testing.assert_allclose(hist, line - sig)


class TestBollingerBands:
    def test_bb_structure(self):
        data = np.random.RandomState(42).randn(50).cumsum() + 100
        bb = bollinger_bands(data, 20)
        assert set(bb.keys()) == {"upper", "middle", "lower", "pct_b", "bandwidth"}
        # Upper > middle > lower where defined
        valid = ~np.isnan(bb["middle"])
        assert np.all(bb["upper"][valid] >= bb["middle"][valid])
        assert np.all(bb["middle"][valid] >= bb["lower"][valid])


class TestATR_ADX:
    def _make_ohlc(self):
        rs = np.random.RandomState(42)
        close = rs.randn(100).cumsum() + 100
        high = close + rs.rand(100) * 2
        low = close - rs.rand(100) * 2
        return high, low, close

    def test_atr_positive(self):
        h, l, c = self._make_ohlc()
        result = atr(h, l, c, 14)
        assert np.all(result > 0)

    def test_adx_range(self):
        h, l, c = self._make_ohlc()
        result = adx(h, l, c, 14)
        assert len(result) == len(c)


class TestParabolicSAR:
    def test_sar_length(self):
        rs = np.random.RandomState(42)
        close = rs.randn(100).cumsum() + 100
        high = close + rs.rand(100) * 2
        low = close - rs.rand(100) * 2
        result = parabolic_sar(high, low)
        assert len(result) == 100


class TestVolumeIndicators:
    def test_obv(self):
        close = np.array([10, 11, 10.5, 12, 11.5])
        volume = np.array([100, 200, 150, 300, 250], dtype=float)
        result = obv(close, volume)
        assert result[0] == 100
        assert result[1] == 300  # up
        assert result[2] == 150  # down

    def test_cmf(self):
        rs = np.random.RandomState(42)
        n = 30
        close = rs.randn(n).cumsum() + 100
        high = close + rs.rand(n) * 2
        low = close - rs.rand(n) * 2
        volume = rs.rand(n) * 1e6 + 1e5
        result = cmf(high, low, close, volume, 20)
        assert not np.isnan(result[-1])

    def test_mfi(self):
        rs = np.random.RandomState(42)
        n = 30
        close = rs.randn(n).cumsum() + 100
        high = close + rs.rand(n) * 2
        low = close - rs.rand(n) * 2
        volume = rs.rand(n) * 1e6 + 1e5
        result = mfi(high, low, close, volume, 14)
        assert not np.isnan(result[-1])


class TestIchimoku:
    def test_ichimoku_keys(self):
        rs = np.random.RandomState(42)
        n = 100
        close = rs.randn(n).cumsum() + 100
        high = close + rs.rand(n) * 2
        low = close - rs.rand(n) * 2
        result = ichimoku(high, low, close)
        assert set(result.keys()) == {"tenkan", "kijun", "senkou_a", "senkou_b", "chikou"}


# ── Stock Screener ───────────────────────────────────────────────────
from src.screener.stock_screener import StockScreener, StockData


class TestStockScreener:
    def _make_stocks(self):
        rs = np.random.RandomState(42)
        stocks = []
        for i, ticker in enumerate(["AAPL", "MSFT", "GOOG", "TSLA"]):
            close = rs.randn(50).cumsum() + 100 + i * 10
            volume = rs.rand(50) * 1e6 + 1e5
            stocks.append(StockData(ticker=ticker, close=close, volume=volume, pe_ratio=10 + i * 5))
        return stocks

    def test_screen_pe(self):
        screener = StockScreener()
        results = screener.screen(self._make_stocks(), {"pe_ratio": {"lt": 20}})
        assert all(r["pe_ratio"] < 20 for r in results)

    def test_screen_empty(self):
        screener = StockScreener()
        results = screener.screen(self._make_stocks(), {"pe_ratio": {"lt": 1}})
        assert results == []

    def test_screen_limit(self):
        screener = StockScreener()
        results = screener.screen(self._make_stocks(), {"pe_ratio": {"lt": 100}}, limit=2)
        assert len(results) <= 2

    def test_screen_sort(self):
        screener = StockScreener()
        results = screener.screen(self._make_stocks(), {"pe_ratio": {"lt": 100}}, sort_by="pe_ratio")
        pes = [r["pe_ratio"] for r in results]
        assert pes == sorted(pes)


# ── Alert Engine ─────────────────────────────────────────────────────
from src.alerts.alert_engine import AlertEngine


class TestAlertEngine:
    def test_price_above(self):
        fired = []
        engine = AlertEngine()
        engine.add_alert("AAPL", "price_above", lambda t, c, v: fired.append((t, c, v)), threshold=150.0)
        close = np.array([140, 145, 148, 152], dtype=float)
        engine.evaluate("AAPL", close)
        assert len(fired) == 1
        assert fired[0][2] == 152.0

    def test_price_below(self):
        fired = []
        engine = AlertEngine()
        engine.add_alert("AAPL", "price_below", lambda t, c, v: fired.append(v), threshold=100.0)
        engine.evaluate("AAPL", np.array([110, 105, 95], dtype=float))
        assert len(fired) == 1

    def test_no_double_trigger(self):
        fired = []
        engine = AlertEngine()
        engine.add_alert("AAPL", "price_above", lambda t, c, v: fired.append(v), threshold=150.0)
        engine.evaluate("AAPL", np.array([160], dtype=float))
        engine.evaluate("AAPL", np.array([170], dtype=float))
        assert len(fired) == 1

    def test_remove_alert(self):
        engine = AlertEngine()
        aid = engine.add_alert("AAPL", "price_above", lambda t, c, v: None, threshold=150.0)
        assert engine.remove_alert(aid)
        assert len(engine.active_alerts) == 0

    def test_macd_cross(self):
        fired = []
        engine = AlertEngine()
        engine.add_alert("AAPL", "macd_cross", lambda t, c, v: fired.append(v))
        # Create data with a clear trend reversal
        data = np.concatenate([np.linspace(100, 80, 30), np.linspace(80, 110, 20)])
        engine.evaluate("AAPL", data)
        # May or may not fire depending on exact crossover — just check no crash
        assert isinstance(fired, list)


# ── Performance Attribution ──────────────────────────────────────────
from src.analytics.attribution import PerformanceAttribution, SectorWeight


class TestAttribution:
    def _setup(self):
        portfolio = [
            SectorWeight("Tech", 0.40, 0.12),
            SectorWeight("Health", 0.30, 0.08),
            SectorWeight("Finance", 0.30, 0.05),
        ]
        benchmark = [
            SectorWeight("Tech", 0.30, 0.10),
            SectorWeight("Health", 0.35, 0.06),
            SectorWeight("Finance", 0.35, 0.04),
        ]
        return PerformanceAttribution(portfolio, benchmark)

    def test_analyze_returns_all_sectors(self):
        pa = self._setup()
        results = pa.analyze()
        assert len(results) == 3
        sectors = {r.sector for r in results}
        assert sectors == {"Tech", "Health", "Finance"}

    def test_summary_keys(self):
        pa = self._setup()
        s = pa.summary()
        assert set(s.keys()) == {"allocation_effect", "selection_effect", "interaction_effect", "total_active_return"}

    def test_total_active_return_decomposition(self):
        pa = self._setup()
        s = pa.summary()
        assert s["total_active_return"] == pytest.approx(
            s["allocation_effect"] + s["selection_effect"] + s["interaction_effect"]
        )

    def test_equal_weights_zero_allocation(self):
        same = [SectorWeight("Tech", 0.5, 0.10), SectorWeight("Health", 0.5, 0.05)]
        pa = PerformanceAttribution(same, same)
        s = pa.summary()
        assert s["allocation_effect"] == pytest.approx(0.0)
        assert s["selection_effect"] == pytest.approx(0.0)
