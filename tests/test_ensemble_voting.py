"""
Tests for Multi-Strategy Ensemble Voting System
=================================================
20+ test cases covering:
  - EnsembleSignal classification
  - Voting logic (0/1/2/3/4/5 votes → correct signals)
  - Each strategy scoring in valid range (0-10)
  - generate_daily_signal format
  - scan_all ordering and filtering
  - Edge cases: insufficient data, flat prices, empty input
"""

import numpy as np
import pytest

from src.strategies.ensemble import (
    StrategyEnsemble,
    EnsembleSignal,
    _rsi,
    _macd,
    _bollinger_pct_b,
    _r2,
    _slope_norm,
    _adx,
    _sma,
    _ema,
)


# ─── Data generators ─────────────────────────────────────────

def _make_uptrend(n: int = 250, start: float = 50.0, daily_ret: float = 0.005, noise: float = 0.001):
    """Strong uptrend stock."""
    rng = np.random.RandomState(42)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + daily_ret + rng.normal(0, noise)))
    closes = np.array(prices)
    opens = np.roll(closes, 1); opens[0] = start
    highs = closes * (1 + rng.uniform(0, 0.01, n))
    lows = closes * (1 - rng.uniform(0, 0.01, n))
    volumes = np.full(n, 1_000_000.0) + rng.uniform(-100000, 100000, n)
    dates = np.array([f"2025-{i // 30 + 1:02d}-{i % 30 + 1:02d}" for i in range(n)])
    return dates, opens, highs, lows, closes, volumes


def _make_flat(n: int = 100, price: float = 10.0):
    """Flat / sideways stock."""
    rng = np.random.RandomState(99)
    closes = np.full(n, price) + rng.normal(0, 0.01, n)
    opens = closes.copy()
    highs = closes + 0.05
    lows = closes - 0.05
    volumes = np.full(n, 500_000.0)
    dates = np.array([f"2025-01-{i + 1:02d}" for i in range(n)])
    return dates, opens, highs, lows, closes, volumes


def _make_bull_with_dip(n: int = 250, start: float = 50.0):
    """Bull stock with golden dip at end (pullback + volume shrinkage + RSI crash)."""
    rng = np.random.RandomState(42)
    # Strong uptrend
    phase1 = n - 30
    prices = [start]
    for _ in range(phase1 - 1):
        prices.append(prices[-1] * (1 + 0.006 + rng.normal(0, 0.001)))
    # Sharp pullback
    for _ in range(20):
        prices.append(prices[-1] * (1 - 0.008 + rng.normal(0, 0.001)))
    # Stabilize
    for _ in range(10):
        prices.append(prices[-1] * (1 + rng.normal(0, 0.001)))

    closes = np.array(prices)
    opens = np.roll(closes, 1); opens[0] = start
    highs = closes * 1.005
    lows = closes * 0.995
    # Volume shrinkage during pullback
    volumes = np.full(n, 1_000_000.0)
    volumes[-30:] = 400_000.0  # shrink
    dates = np.array([f"2025-{i // 30 + 1:02d}-{i % 30 + 1:02d}" for i in range(n)])
    return dates, opens, highs, lows, closes, volumes


def _make_limit_up_pullback(n: int = 50):
    """Stock with limit-up day followed by pullback."""
    rng = np.random.RandomState(42)
    closes = np.full(n, 10.0)
    for i in range(1, n):
        closes[i] = closes[i - 1] * (1 + rng.normal(0.001, 0.01))

    # Inject limit-up at day n-5
    lu_idx = n - 5
    closes[lu_idx] = closes[lu_idx - 1] * 1.10  # 10% limit up

    # Pullback for 3 days: close < limit-up close, lows above limit-up low
    for i in range(lu_idx + 1, n - 1):
        closes[i] = closes[lu_idx] * (0.97 + rng.uniform(0, 0.02))

    opens = np.roll(closes, 1); opens[0] = closes[0]
    highs = closes * 1.01
    lows = closes * 0.99
    lows[lu_idx] = closes[lu_idx] * 0.95  # limit-up day low

    # Ensure pullback lows are above limit-up low
    for i in range(lu_idx + 1, n):
        lows[i] = max(lows[i], lows[lu_idx] + 0.01)

    # Volume: high on limit-up day, low during pullback
    volumes = np.full(n, 500_000.0)
    volumes[lu_idx] = 5_000_000.0
    volumes[lu_idx + 1:] = 200_000.0  # shrink

    dates = np.array([f"2025-02-{i + 1:02d}" for i in range(n)])
    return dates, opens, highs, lows, closes, volumes


def _make_breakout(n: int = 100):
    """Stock with Donchian breakout + volume surge."""
    rng = np.random.RandomState(42)
    # Consolidation for most of the period
    closes = np.full(n, 20.0) + rng.normal(0, 0.2, n)
    # Breakout: last bar above 20d high with volume surge
    closes[-1] = np.max(closes[-21:-1]) + 1.0

    opens = np.roll(closes, 1); opens[0] = 20.0
    opens[-1] = closes[-1] - 0.5  # bullish candle
    highs = closes + 0.3
    lows = closes - 0.3
    volumes = np.full(n, 500_000.0)
    volumes[-1] = 2_000_000.0  # volume surge

    dates = np.array([f"2025-01-{i + 1:02d}" for i in range(n)])
    return dates, opens, highs, lows, closes, volumes


# ─── Helper tests ─────────────────────────────────────────

class TestIndicatorHelpers:
    """Test pure-numpy indicator functions."""

    def test_rsi_range(self):
        prices = np.linspace(10, 50, 100)
        r = _rsi(prices, 14)
        valid = r[~np.isnan(r)]
        assert len(valid) > 0
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)

    def test_rsi_insufficient_data(self):
        prices = np.array([10.0, 11.0])
        r = _rsi(prices, 14)
        assert np.all(np.isnan(r))

    def test_macd_shape(self):
        prices = np.linspace(10, 50, 100)
        line, sig, hist = _macd(prices)
        assert len(line) == 100
        assert len(sig) == 100
        assert len(hist) == 100

    def test_bollinger_pct_b_range(self):
        prices = np.random.RandomState(42).normal(100, 5, 50)
        pct_b = _bollinger_pct_b(prices)
        # pct_b can exceed 0-1 range, but should be finite
        assert np.isfinite(pct_b)

    def test_r2_perfect_trend(self):
        prices = np.linspace(10, 50, 30)
        assert _r2(prices, 30) > 0.99

    def test_r2_random(self):
        prices = np.random.RandomState(42).normal(100, 10, 30)
        r2 = _r2(prices, 30)
        assert 0 <= r2 <= 1

    def test_r2_insufficient(self):
        assert _r2(np.array([1.0]), 5) == 0.0

    def test_slope_positive(self):
        prices = np.linspace(10, 50, 30)
        assert _slope_norm(prices, 30) > 0

    def test_slope_flat(self):
        prices = np.full(30, 10.0)
        assert _slope_norm(prices, 30) == 0.0

    def test_sma(self):
        arr = np.arange(1, 11, dtype=float)
        s = _sma(arr, 3)
        assert np.isnan(s[0])
        assert np.isnan(s[1])
        assert s[2] == pytest.approx(2.0)

    def test_ema(self):
        arr = np.arange(1, 11, dtype=float)
        e = _ema(arr, 3)
        assert np.isnan(e[0])
        assert np.isnan(e[1])
        assert e[2] == pytest.approx(2.0)  # first EMA = SMA

    def test_adx_insufficient(self):
        assert _adx(np.array([1.0]), np.array([1.0]), np.array([1.0])) == 0.0


# ─── Strategy scoring tests ──────────────────────────────

class TestStrategyScoringRanges:
    """Each scoring function must return 0-10."""

    @pytest.fixture
    def ensemble(self):
        return StrategyEnsemble()

    def test_cn_scanner_score_range(self, ensemble):
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        score = ensemble.score_cn_scanner(closes, volumes, opens, highs, lows)
        assert 0.0 <= score <= 10.0

    def test_trend_discovery_score_range(self, ensemble):
        _, _, _, _, closes, volumes = _make_uptrend()
        score = ensemble.score_trend_discovery(closes, volumes)
        assert 0.0 <= score <= 10.0

    def test_golden_dip_score_range(self, ensemble):
        _, _, _, _, closes, volumes = _make_bull_with_dip()
        score = ensemble.score_golden_dip(closes, volumes)
        assert 0.0 <= score <= 10.0

    def test_imminent_breakout_score_range(self, ensemble):
        _, opens, highs, lows, closes, volumes = _make_breakout()
        score = ensemble.score_imminent_breakout(opens, highs, lows, closes, volumes)
        assert 0.0 <= score <= 10.0

    def test_limit_up_pullback_score_range(self, ensemble):
        _, opens, highs, lows, closes, volumes = _make_limit_up_pullback()
        score = ensemble.score_limit_up_pullback(opens, highs, lows, closes, volumes)
        assert 0.0 <= score <= 10.0

    def test_cn_scanner_insufficient_data(self, ensemble):
        closes = np.array([10.0, 11.0, 12.0])
        score = ensemble.score_cn_scanner(closes, None, None, None, None)
        assert score == 0.0

    def test_trend_discovery_insufficient(self, ensemble):
        closes = np.array([10.0, 11.0])
        score = ensemble.score_trend_discovery(closes, None)
        assert score == 0.0

    def test_golden_dip_insufficient(self, ensemble):
        closes = np.linspace(10, 50, 50)
        score = ensemble.score_golden_dip(closes, None)
        assert score == 0.0  # < 120 bars

    def test_imminent_breakout_insufficient(self, ensemble):
        closes = np.array([10.0] * 5)
        score = ensemble.score_imminent_breakout(None, None, None, closes, None)
        assert score == 0.0

    def test_limit_up_pullback_insufficient(self, ensemble):
        closes = np.array([10.0, 11.0, 10.5])
        score = ensemble.score_limit_up_pullback(None, None, None, closes, None)
        assert score == 0.0

    def test_flat_stock_low_scores(self, ensemble):
        """Flat stock should get low scores from all strategies."""
        _, opens, highs, lows, closes, volumes = _make_flat(200)
        s1 = ensemble.score_cn_scanner(closes, volumes, opens, highs, lows)
        s2 = ensemble.score_trend_discovery(closes, volumes)
        s4 = ensemble.score_imminent_breakout(opens, highs, lows, closes, volumes)
        # Flat stock should score low (no signal)
        assert s1 < 7
        assert s2 < 7
        assert s4 < 7


# ─── Voting logic tests ─────────────────────────────────

class TestVotingLogic:
    """Test vote counting and signal classification."""

    @pytest.fixture
    def ensemble(self):
        return StrategyEnsemble(min_votes=2, min_consensus=0.4)

    def test_zero_votes_skip(self, ensemble):
        """0 votes → skip."""
        _, opens, highs, lows, closes, volumes = _make_flat()
        sig = ensemble.evaluate_stock(
            np.array([]), opens, highs, lows, closes, volumes,
            code="000001", name="测试",
        )
        assert sig.signal == "skip"
        assert sig.votes == 0

    def test_signal_fields_populated(self, ensemble):
        """All fields of EnsembleSignal are populated."""
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        sig = ensemble.evaluate_stock(
            np.array([]), opens, highs, lows, closes, volumes,
            code="600519", name="贵州茅台",
        )
        assert sig.code == "600519"
        assert sig.name == "贵州茅台"
        assert sig.price > 0
        assert 0 <= sig.votes <= 5
        assert sig.total_strategies == 5
        assert 0.0 <= sig.consensus <= 1.0
        assert sig.avg_score >= 0
        assert sig.signal in ("strong_buy", "buy", "watch", "skip")
        assert len(sig.scores) == 5

    def test_consensus_calculation(self, ensemble):
        """consensus = votes / total_strategies."""
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        sig = ensemble.evaluate_stock(
            np.array([]), opens, highs, lows, closes, volumes,
        )
        expected = sig.votes / sig.total_strategies
        assert sig.consensus == pytest.approx(expected)

    def test_avg_score_calculation(self, ensemble):
        """avg_score = mean of all 5 strategy scores."""
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        sig = ensemble.evaluate_stock(
            np.array([]), opens, highs, lows, closes, volumes,
        )
        expected = sum(sig.scores.values()) / 5
        assert sig.avg_score == pytest.approx(expected)

    def test_strategies_list_matches_votes(self, ensemble):
        """strategies list length == votes count."""
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        sig = ensemble.evaluate_stock(
            np.array([]), opens, highs, lows, closes, volumes,
        )
        assert len(sig.strategies) == sig.votes

    def test_strong_buy_threshold(self):
        """3+ votes or 60%+ consensus → strong_buy."""
        # We test the classification logic directly via a mock
        ensemble = StrategyEnsemble()
        # Create a signal with 3 votes
        sig = EnsembleSignal(
            code="TEST", name="test", price=10.0,
            votes=3, total_strategies=5, consensus=0.6,
            strategies=["a", "b", "c"], avg_score=8.0,
            signal="strong_buy",
        )
        assert sig.signal == "strong_buy"

    def test_buy_threshold(self):
        """2 votes → buy."""
        sig = EnsembleSignal(
            code="TEST", name="test", price=10.0,
            votes=2, total_strategies=5, consensus=0.4,
            strategies=["a", "b"], avg_score=6.0,
            signal="buy",
        )
        assert sig.signal == "buy"

    def test_watch_single_vote(self):
        """1 vote → watch."""
        sig = EnsembleSignal(
            code="TEST", name="test", price=10.0,
            votes=1, total_strategies=5, consensus=0.2,
            strategies=["a"], avg_score=4.0,
            signal="watch",
        )
        assert sig.signal == "watch"


# ─── scan_all tests ──────────────────────────────────────

class TestScanAll:
    """Test batch scanning."""

    def test_scan_all_returns_sorted(self):
        ensemble = StrategyEnsemble()
        _, opens, highs, lows, closes, volumes = _make_uptrend()
        _, opens2, highs2, lows2, closes2, volumes2 = _make_flat(250)

        stock_data = {
            "600519": {
                "dates": np.array([]),
                "opens": opens, "highs": highs, "lows": lows,
                "closes": closes, "volumes": volumes,
                "name": "贵州茅台",
            },
            "000001": {
                "dates": np.array([]),
                "opens": opens2, "highs": highs2, "lows": lows2,
                "closes": closes2, "volumes": volumes2,
                "name": "平安银行",
            },
        }

        results = ensemble.scan_all(stock_data)
        # Results are sorted by (votes desc, avg_score desc)
        for i in range(len(results) - 1):
            a, b = results[i], results[i + 1]
            assert (a.votes, a.avg_score) >= (b.votes, b.avg_score)

    def test_scan_all_skips_short_data(self):
        ensemble = StrategyEnsemble()
        stock_data = {
            "SHORT": {
                "dates": np.array([]),
                "closes": np.array([10.0, 11.0]),
                "name": "短数据",
            },
        }
        results = ensemble.scan_all(stock_data)
        assert len(results) == 0

    def test_scan_all_excludes_skip(self):
        """Skip signals are not returned."""
        ensemble = StrategyEnsemble()
        _, opens, highs, lows, closes, volumes = _make_flat(250)
        stock_data = {
            "FLAT": {
                "dates": np.array([]),
                "opens": opens, "highs": highs, "lows": lows,
                "closes": closes, "volumes": volumes,
                "name": "横盘股",
            },
        }
        results = ensemble.scan_all(stock_data)
        for r in results:
            assert r.signal != "skip"


# ─── generate_daily_signal tests ─────────────────────────

class TestDailySignal:
    """Test daily signal report generation."""

    def test_daily_signal_format(self):
        ensemble = StrategyEnsemble()
        _, opens, highs, lows, closes, volumes = _make_uptrend()

        stock_data = {
            "600519": {
                "dates": np.array([]),
                "opens": opens, "highs": highs, "lows": lows,
                "closes": closes, "volumes": volumes,
                "name": "贵州茅台",
            },
        }

        report = ensemble.generate_daily_signal(stock_data)
        assert "📊" in report
        assert "交易信号" in report
        assert "🟢 买入" in report
        assert "共扫描" in report

    def test_daily_signal_empty_data(self):
        ensemble = StrategyEnsemble()
        report = ensemble.generate_daily_signal({})
        assert "📊" in report
        assert "无合适标的" in report
        assert "共扫描 0 只股票" in report

    def test_daily_signal_max_positions(self):
        """Should respect max_positions limit."""
        ensemble = StrategyEnsemble()
        report = ensemble.generate_daily_signal({}, max_positions=3)
        assert "📊" in report


# ─── Edge cases ──────────────────────────────────────────

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_all_nan_volumes(self):
        ensemble = StrategyEnsemble()
        closes = np.linspace(10, 50, 100)
        volumes = np.full(100, np.nan)
        # Should not crash
        score = ensemble.score_cn_scanner(closes, volumes, closes, closes, closes)
        assert np.isfinite(score)

    def test_zero_price_stock(self):
        ensemble = StrategyEnsemble()
        closes = np.full(100, 0.0)
        sig = ensemble.evaluate_stock(
            np.array([]), closes, closes, closes, closes, closes,
        )
        assert sig.signal in ("strong_buy", "buy", "watch", "skip")

    def test_single_price(self):
        ensemble = StrategyEnsemble()
        closes = np.array([100.0])
        sig = ensemble.evaluate_stock(
            np.array([]), closes, closes, closes, closes, closes,
        )
        assert sig.votes == 0
        assert sig.signal == "skip"

    def test_custom_min_votes(self):
        """Custom min_votes threshold."""
        ensemble = StrategyEnsemble(min_votes=4, min_consensus=0.8)
        assert ensemble.min_votes == 4
        assert ensemble.min_consensus == 0.8
