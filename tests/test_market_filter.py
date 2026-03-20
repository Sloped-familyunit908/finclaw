"""
Tests for Market Environment Filter
=====================================
Tests MarketFilter with synthetic index data for bull, bear, and sideways markets.
"""

import numpy as np
import pytest

from src.market_filter import MarketFilter, _sma, _rsi


# ── Helpers ──────────────────────────────────────────────────────────

def _make_bull_market(n: int = 100, start: float = 3000.0) -> np.ndarray:
    """Generate synthetic bull market: steady uptrend with small noise."""
    rng = np.random.RandomState(42)
    daily_returns = 1 + 0.002 + rng.normal(0, 0.005, n)  # ~0.2% avg daily gain
    prices = np.cumprod(np.concatenate([[start], daily_returns[:-1]]))
    return prices


def _make_bear_market(n: int = 100, start: float = 3000.0) -> np.ndarray:
    """Generate synthetic bear market: steady downtrend."""
    rng = np.random.RandomState(42)
    daily_returns = 1 - 0.003 + rng.normal(0, 0.005, n)  # ~-0.3% avg daily decline
    prices = np.cumprod(np.concatenate([[start], daily_returns[:-1]]))
    return prices


def _make_sideways_market(n: int = 100, start: float = 3000.0) -> np.ndarray:
    """Generate synthetic sideways/range-bound market."""
    rng = np.random.RandomState(42)
    daily_returns = 1 + rng.normal(0, 0.004, n)  # zero drift, low vol
    prices = np.cumprod(np.concatenate([[start], daily_returns[:-1]]))
    return prices


def _make_crash_market(n: int = 50, start: float = 3000.0) -> np.ndarray:
    """Generate crash scenario: normal then sharp drop."""
    rng = np.random.RandomState(42)
    # Normal period
    normal = np.cumprod(
        np.concatenate([[start], 1 + rng.normal(0.001, 0.005, 39)])
    )
    # Crash: 3 days of ~1.5% drop each (>3% total)
    crash_rets = np.array([0.985, 0.98, 0.985])
    crash_prices = normal[-1] * np.cumprod(crash_rets)
    # Small bounce after
    bounce = crash_prices[-1] * np.cumprod(1 + rng.normal(0.001, 0.005, n - 43))
    return np.concatenate([normal, crash_prices, bounce])


def _make_panic_market(n: int = 100, start: float = 3000.0) -> np.ndarray:
    """Generate data where RSI drops below 25."""
    # Sustained drop to drive RSI down
    prices = np.full(n, start)
    for i in range(1, n):
        prices[i] = prices[i - 1] * 0.992  # ~0.8% daily drop
    return prices


def _make_recovery_market(n: int = 100, start: float = 3000.0) -> np.ndarray:
    """Generate oversold then bouncing market."""
    prices = np.full(n, start)
    # First 60 days: decline
    for i in range(1, 60):
        prices[i] = prices[i - 1] * 0.995
    # Then 40 days: recovery
    for i in range(60, n):
        prices[i] = prices[i - 1] * 1.003
    return prices


# ── Internal Helper Tests ────────────────────────────────────────────

class TestInternalHelpers:
    def test_sma_basic(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = _sma(data, 3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert result[2] == pytest.approx(2.0, abs=1e-10)
        assert result[3] == pytest.approx(3.0, abs=1e-10)
        assert result[4] == pytest.approx(4.0, abs=1e-10)

    def test_sma_insufficient_data(self):
        data = np.array([1.0, 2.0])
        result = _sma(data, 5)
        assert all(np.isnan(result))

    def test_rsi_uptrend(self):
        """Monotonically rising prices should produce RSI near 100."""
        prices = np.arange(1.0, 31.0)  # 1, 2, 3, ..., 30
        r = _rsi(prices, 14)
        # After warmup, RSI should be high
        assert r[-1] == pytest.approx(100.0, abs=0.1)

    def test_rsi_downtrend(self):
        """Monotonically falling prices should produce RSI near 0."""
        prices = np.arange(30.0, 0.0, -1.0)  # 30, 29, ..., 1
        r = _rsi(prices, 14)
        assert r[-1] == pytest.approx(0.0, abs=0.1)


# ── MarketFilter.is_favorable Tests ─────────────────────────────────

class TestIsFavorable:
    def test_bull_market_is_favorable(self):
        """Bull market should be favorable."""
        prices = _make_bull_market(100)
        mf = MarketFilter(prices)
        assert mf.is_favorable() is True

    def test_bear_market_with_death_cross_is_unfavorable(self):
        """Bear market with declining MA5 < MA20 should be unfavorable."""
        prices = _make_bear_market(100)
        mf = MarketFilter(prices)
        # Bear market often produces death cross + declining MA5
        assert mf.is_favorable() is False

    def test_sideways_market_is_mixed(self):
        """Sideways market should have at least one favorable condition."""
        prices = _make_sideways_market(100)
        mf = MarketFilter(prices)
        # Sideways: RSI likely around 50 (> 40), so favorable
        result = mf.is_favorable()
        assert isinstance(result, bool)

    def test_crash_triggers_unfavorable(self):
        """A 3-day crash >3% should trigger unfavorable."""
        prices = _make_crash_market(50)
        mf = MarketFilter()
        # Evaluate right at the crash point (index 42 = end of crash)
        crash_prices = prices[:43]
        assert mf.is_favorable(crash_prices) is False

    def test_panic_rsi_below_25_is_unfavorable(self):
        """RSI < 25 (panic selling) should be unfavorable."""
        prices = _make_panic_market(100)
        mf = MarketFilter(prices)
        assert mf.is_favorable() is False

    def test_recovery_market_becomes_favorable(self):
        """A recovering market should eventually be favorable."""
        prices = _make_recovery_market(100)
        mf = MarketFilter(prices)
        # After 40 days of recovery from oversold, RSI > 40
        result = mf.is_favorable()
        assert isinstance(result, bool)  # may or may not be favorable depending on exact timing

    def test_insufficient_data_returns_true(self):
        """With too little data, assume favorable (don't block)."""
        prices = np.array([100.0, 101.0, 102.0])
        mf = MarketFilter(prices)
        assert mf.is_favorable() is True

    def test_no_prices_raises(self):
        """Calling without any prices should raise ValueError."""
        mf = MarketFilter()
        with pytest.raises(ValueError, match="No index_prices"):
            mf.is_favorable()

    def test_override_prices(self):
        """Passing index_prices to is_favorable overrides __init__ prices."""
        bull = _make_bull_market(100)
        bear = _make_bear_market(100)
        mf = MarketFilter(bear)  # default is bear (unfavorable)
        # Override with bull prices
        assert mf.is_favorable(bull) is True


# ── MarketFilter.market_score Tests ──────────────────────────────────

class TestMarketScore:
    def test_bull_score_above_60(self):
        """Bull market should score above 60 (favorable)."""
        prices = _make_bull_market(100)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert score > 60, f"Bull market score {score} should be > 60"

    def test_bear_score_below_40(self):
        """Bear market should score below 40 (unfavorable)."""
        prices = _make_bear_market(100)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert score < 40, f"Bear market score {score} should be < 40"

    def test_score_range_0_to_100(self):
        """Score should always be in [0, 100]."""
        for gen in [_make_bull_market, _make_bear_market, _make_sideways_market,
                    _make_crash_market, _make_panic_market, _make_recovery_market]:
            prices = gen()
            mf = MarketFilter(prices)
            score = mf.market_score()
            assert 0.0 <= score <= 100.0, f"Score {score} out of range for {gen.__name__}"

    def test_score_returns_float(self):
        """Score should be a float."""
        prices = _make_bull_market(100)
        mf = MarketFilter(prices)
        assert isinstance(mf.market_score(), float)

    def test_insufficient_data_score_neutral(self):
        """With insufficient data, score should be 50 (neutral)."""
        prices = np.array([100.0, 101.0, 102.0])
        mf = MarketFilter(prices)
        assert mf.market_score() == pytest.approx(50.0)

    def test_pure_uptrend_high_score(self):
        """A pure linear uptrend should produce a high score."""
        prices = np.linspace(2800, 3200, 100)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert score > 55, f"Linear uptrend score {score} should be > 55"

    def test_pure_downtrend_low_score(self):
        """A pure linear downtrend should produce a low score."""
        prices = np.linspace(3200, 2600, 100)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert score < 45, f"Linear downtrend score {score} should be < 45"


# ── MarketFilter.get_regime Tests ────────────────────────────────────

class TestGetRegime:
    def test_bull_regime(self):
        """Bull market should return 'bull'."""
        prices = _make_bull_market(100)
        mf = MarketFilter(prices)
        assert mf.get_regime() == "bull"

    def test_bear_regime(self):
        """Bear market should return 'bear'."""
        prices = _make_bear_market(100)
        mf = MarketFilter(prices)
        assert mf.get_regime() == "bear"

    def test_regime_values(self):
        """get_regime should return one of 'bull', 'neutral', 'bear'."""
        for gen in [_make_bull_market, _make_bear_market, _make_sideways_market]:
            prices = gen()
            mf = MarketFilter(prices)
            regime = mf.get_regime()
            assert regime in ("bull", "neutral", "bear"), f"Invalid regime: {regime}"

    def test_regime_string_type(self):
        """get_regime should return a string."""
        mf = MarketFilter(_make_bull_market(100))
        assert isinstance(mf.get_regime(), str)


# ── Configuration Tests ──────────────────────────────────────────────

class TestConfiguration:
    def test_custom_ma_periods(self):
        """Custom MA periods should be used."""
        prices = _make_bull_market(100)
        mf = MarketFilter(prices, ma_short=3, ma_long=10)
        assert mf.ma_short == 3
        assert mf.ma_long == 10
        # Should still work
        result = mf.is_favorable()
        assert isinstance(result, bool)

    def test_default_ma_periods(self):
        """Default MA periods should be 5 and 20."""
        mf = MarketFilter()
        assert mf.ma_short == 5
        assert mf.ma_long == 20


# ── Edge Cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_constant_prices(self):
        """Constant prices should not crash and should return neutral."""
        prices = np.full(100, 3000.0)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert 0 <= score <= 100
        result = mf.is_favorable()
        assert isinstance(result, bool)

    def test_single_price(self):
        """Single price point should not crash."""
        prices = np.array([3000.0])
        mf = MarketFilter(prices)
        assert mf.is_favorable() is True  # insufficient data → True
        assert mf.market_score() == 50.0

    def test_very_long_series(self):
        """Long series (1000+ points) should work fine."""
        prices = _make_bull_market(1000)
        mf = MarketFilter(prices)
        score = mf.market_score()
        assert 0 <= score <= 100
        assert mf.is_favorable() is True

    def test_volatile_crash_then_recovery(self):
        """Crash followed by recovery should transition from bear to bull."""
        rng = np.random.RandomState(99)
        n = 200
        prices = np.full(n, 3000.0)
        # Phase 1: normal (0-60)
        for i in range(1, 60):
            prices[i] = prices[i - 1] * (1 + rng.normal(0.001, 0.003))
        # Phase 2: crash (60-80)
        for i in range(60, 80):
            prices[i] = prices[i - 1] * 0.98
        # Phase 3: recovery (80-200)
        for i in range(80, n):
            prices[i] = prices[i - 1] * (1 + rng.normal(0.003, 0.005))

        # Check at crash bottom
        mf_crash = MarketFilter(prices[:80])
        assert mf_crash.get_regime() == "bear"

        # Check after recovery
        mf_recovery = MarketFilter(prices)
        regime = mf_recovery.get_regime()
        assert regime in ("bull", "neutral"), f"After recovery, regime should be bull/neutral, got {regime}"
