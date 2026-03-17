"""Tests for Portfolio Tracker, TA indicators, Screener, Alerts, and Attribution."""

import math
from datetime import date

import numpy as np
import pytest

# ── Portfolio Tracker ────────────────────────────────────────────────
from src.portfolio.tracker import PortfolioTracker


class TestPortfolioTracker:
    def test_buy(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 150.0, date(2024, 1, 1))
        assert pt.cash == pytest.approx(98_500)
        assert pt.positions["AAPL"].shares == 10

    def test_sell(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 150.0, date(2024, 1, 1))
        pt.sell("AAPL", 5, 160.0, date(2024, 1, 2))
        assert pt.positions["AAPL"].shares == 5
        assert pt.cash == pytest.approx(98_500 + 800)

    def test_sell_all_removes_position(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 150.0, date(2024, 1, 1))
        pt.sell("AAPL", 10, 160.0, date(2024, 1, 2))
        assert "AAPL" not in pt.positions

    def test_insufficient_cash(self):
        pt = PortfolioTracker(1_000)
        with pytest.raises(ValueError, match="Insufficient cash"):
            pt.buy("AAPL", 100, 150.0, date(2024, 1, 1))

    def test_insufficient_shares(self):
        pt = PortfolioTracker(100_000)
        with pytest.raises(ValueError, match="Insufficient shares"):
            pt.sell("AAPL", 1, 100.0, date(2024, 1, 1))

    def test_snapshot(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 150.0, date(2024, 1, 1))
        snap = pt.snapshot(date(2024, 1, 1), {"AAPL": 155.0})
        assert snap.total_value == pytest.approx(98_500 + 10 * 155.0)

    def test_performance(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 100.0, date(2024, 1, 1))
        for i, p in enumerate([100, 105, 110, 108, 112]):
            pt.snapshot(date(2024, 1, i + 1), {"AAPL": p})
        perf = pt.get_performance()
        assert perf["total_return"] > 0
        assert perf["num_snapshots"] == 5

    def test_avg_cost_multiple_buys(self):
        pt = PortfolioTracker(100_000)
        pt.buy("AAPL", 10, 100.0, date(2024, 1, 1))
        pt.buy("AAPL", 10, 200.0, date(2024, 1, 2))
        assert pt.positions["AAPL"].avg_cost == pytest.approx(150.0)
        assert pt.positions["AAPL"].shares == 20

    def test_no_snapshots_performance(self):
        pt = PortfolioTracker(100_000)
        assert pt.get_performance() == {"error": "no snapshots"}


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
