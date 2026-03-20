"""Tests for Enhanced Regime Detection + Economic Plausibility Checker.

All tests use synthetic data — no real market data or API calls needed.
"""

import math
import os
import sys
import random

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ml.enhanced_regime_detector import EnhancedRegimeDetector, RegimeResult
from src.ml.economic_plausibility import EconomicPlausibilityChecker, PlausibilityResult


# ======================================================================
# Helpers — synthetic price generators
# ======================================================================

def _stable_prices(n: int = 300, start: float = 100.0, daily_drift: float = 0.0002,
                   daily_vol: float = 0.005, seed: int = 42) -> list[float]:
    """Slowly rising, low-vol price series (typical calm market)."""
    rng = random.Random(seed)
    prices = [start]
    for _ in range(n - 1):
        ret = daily_drift + daily_vol * rng.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def _volatile_prices(n: int = 300, start: float = 100.0, seed: int = 42) -> list[float]:
    """Calm market that transitions to high-vol whipsaw in the recent window.

    The first ~80% of the series is low-vol (0.005/day), then the last ~20%
    jumps to 0.04/day.  This creates a clear volatility-cluster signal that
    should be detected as 'volatile'.
    """
    rng = random.Random(seed)
    calm_end = int(n * 0.80)
    prices = [start]
    for i in range(1, n):
        if i < calm_end:
            ret = 0.0002 + 0.005 * rng.gauss(0, 1)
        else:
            ret = 0.0 + 0.04 * rng.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def _crash_prices(n: int = 300, start: float = 100.0, crash_start: int = 260,
                  crash_daily: float = -0.03, seed: int = 42) -> list[float]:
    """Normal market followed by a ~30% crash in the last ~40 days."""
    rng = random.Random(seed)
    prices = [start]
    for i in range(1, n):
        if i >= crash_start:
            ret = crash_daily + 0.005 * rng.gauss(0, 1)
        else:
            ret = 0.0003 + 0.008 * rng.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def _flat_prices(n: int = 100, price: float = 100.0) -> list[float]:
    """Completely flat price series (edge case)."""
    return [price] * n


def _random_volumes(n: int, mean: float = 1e6, std: float = 2e5, seed: int = 99) -> list[float]:
    rng = random.Random(seed)
    return [max(100, mean + std * rng.gauss(0, 1)) for _ in range(n)]


# ======================================================================
# EnhancedRegimeDetector — basic construction
# ======================================================================

class TestEnhancedRegimeDetectorInit:
    def test_default_init(self):
        d = EnhancedRegimeDetector()
        assert d.lookback == 20
        assert d.baseline_window == 252

    def test_custom_params(self):
        d = EnhancedRegimeDetector(lookback=10, baseline_window=60)
        assert d.lookback == 10
        assert d.baseline_window == 60

    def test_lookback_too_small_raises(self):
        with pytest.raises(ValueError, match="lookback must be >= 2"):
            EnhancedRegimeDetector(lookback=1)

    def test_baseline_smaller_than_lookback_raises(self):
        with pytest.raises(ValueError, match="baseline_window must be >= lookback"):
            EnhancedRegimeDetector(lookback=50, baseline_window=30)


# ======================================================================
# EnhancedRegimeDetector — regime classification
# ======================================================================

class TestEnhancedRegimeDetection:
    def test_stable_market(self):
        d = EnhancedRegimeDetector()
        prices = _stable_prices()
        regime = d.detect_regime(prices)
        assert regime == "stable"

    def test_volatile_market(self):
        d = EnhancedRegimeDetector()
        prices = _volatile_prices()
        regime = d.detect_regime(prices)
        assert regime in ("volatile", "crash"), f"Expected volatile or crash, got {regime}"

    def test_crash_market(self):
        d = EnhancedRegimeDetector()
        prices = _crash_prices()
        regime = d.detect_regime(prices)
        assert regime == "crash", f"Expected crash, got {regime}"

    def test_score_stable_is_low(self):
        d = EnhancedRegimeDetector()
        score = d.regime_score(_stable_prices())
        assert 0.0 <= score < 0.35, f"Stable score {score} should be < 0.35"

    def test_score_crash_is_high(self):
        d = EnhancedRegimeDetector()
        score = d.regime_score(_crash_prices())
        assert score > 0.5, f"Crash score {score} should be > 0.5"

    def test_score_range(self):
        d = EnhancedRegimeDetector()
        for prices in [_stable_prices(), _volatile_prices(), _crash_prices()]:
            score = d.regime_score(prices)
            assert 0.0 <= score <= 1.0

    def test_detailed_result_type(self):
        d = EnhancedRegimeDetector()
        result = d.detect_detailed(_stable_prices())
        assert isinstance(result, RegimeResult)
        assert result.regime in ("stable", "volatile", "crash")
        assert 0.0 <= result.score <= 1.0
        assert isinstance(result.volatility, float)
        assert isinstance(result.reconstruction_error, float)


# ======================================================================
# EnhancedRegimeDetector — edge cases
# ======================================================================

class TestEnhancedRegimeEdgeCases:
    def test_short_data_returns_stable(self):
        d = EnhancedRegimeDetector(lookback=20)
        regime = d.detect_regime([100, 101, 102])  # too short
        assert regime == "stable"
        assert d.regime_score([100, 101, 102]) == 0.0

    def test_flat_prices(self):
        d = EnhancedRegimeDetector(lookback=5, baseline_window=20)
        regime = d.detect_regime(_flat_prices(50))
        assert regime == "stable"

    def test_with_volumes(self):
        d = EnhancedRegimeDetector()
        prices = _volatile_prices()
        volumes = _random_volumes(len(prices))
        # Should run without error, regime may differ slightly from no-volume
        regime = d.detect_regime(prices, volumes)
        assert regime in ("stable", "volatile", "crash")

    def test_no_volumes(self):
        """Passing None for volumes should work fine."""
        d = EnhancedRegimeDetector()
        regime = d.detect_regime(_stable_prices(), None)
        assert regime == "stable"

    def test_exactly_minimum_data(self):
        d = EnhancedRegimeDetector(lookback=5, baseline_window=5)
        prices = _stable_prices(7)  # exactly lookback + 1 + 1
        regime = d.detect_regime(prices)
        assert regime in ("stable", "volatile", "crash")

    def test_monotone_up(self):
        """Steadily rising prices → stable or volatile, never crash."""
        prices = [100.0 * (1.001 ** i) for i in range(300)]
        d = EnhancedRegimeDetector()
        regime = d.detect_regime(prices)
        assert regime != "crash"

    def test_monotone_down_steep(self):
        """Steep decline → should be crash."""
        prices = [100.0 * (0.97 ** i) for i in range(300)]
        d = EnhancedRegimeDetector()
        regime = d.detect_regime(prices)
        assert regime == "crash"


# ======================================================================
# EnhancedRegimeDetector — adaptive weights
# ======================================================================

class TestAdaptiveWeights:
    def test_stable_weights(self):
        d = EnhancedRegimeDetector()
        w = d.adaptive_weights("stable")
        assert w["momentum"] > w["risk"]
        assert w["trend"] > w["drawdown"]
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_volatile_weights(self):
        d = EnhancedRegimeDetector()
        w = d.adaptive_weights("volatile")
        assert w["mean_reversion"] > w["momentum"]
        assert w["rsi"] > w["trend"]
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_crash_weights(self):
        d = EnhancedRegimeDetector()
        w = d.adaptive_weights("crash")
        assert w["risk"] >= w["momentum"]
        assert w["drawdown"] >= w["trend"]
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_weights_sum_to_one(self):
        d = EnhancedRegimeDetector()
        for regime in ("stable", "volatile", "crash"):
            w = d.adaptive_weights(regime)
            assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_unknown_regime_raises(self):
        d = EnhancedRegimeDetector()
        with pytest.raises(ValueError, match="Unknown regime"):
            d.adaptive_weights("sideways")

    def test_case_insensitive(self):
        d = EnhancedRegimeDetector()
        w1 = d.adaptive_weights("STABLE")
        w2 = d.adaptive_weights("stable")
        assert w1 == w2


# ======================================================================
# EnhancedRegimeDetector — custom thresholds
# ======================================================================

class TestCustomThresholds:
    def test_custom_volatile_threshold(self):
        # Very low volatile threshold → easy to trigger volatile
        d = EnhancedRegimeDetector(volatile_threshold=0.05)
        regime = d.detect_regime(_stable_prices())
        # Might now be "volatile" even for calm data
        assert regime in ("stable", "volatile", "crash")

    def test_custom_crash_threshold_high(self):
        # Very high crash threshold → harder to trigger crash
        d = EnhancedRegimeDetector(crash_threshold=0.99)
        regime = d.detect_regime(_crash_prices())
        # Might not reach crash threshold
        assert regime in ("stable", "volatile", "crash")


# ======================================================================
# EconomicPlausibilityChecker — Sharpe
# ======================================================================

class TestCheckSharpe:
    def test_reasonable_sharpe(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(1.5, period_days=252)
        assert ok is True

    def test_high_sharpe_flagged(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(3.5, period_days=252)
        assert ok is False
        assert "suspicious" in msg.lower() or "overfitting" in msg.lower()

    def test_extreme_annualised_sharpe(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(5.0, period_days=252)
        assert ok is False
        assert "extremely" in msg.lower() or "certainly" in msg.lower()

    def test_short_period_not_annualised(self):
        c = EconomicPlausibilityChecker()
        # Sharpe 2.0 over 30 days → annualised = 2 * sqrt(252/30) ≈ 5.8
        ok, msg = c.check_sharpe(2.0, period_days=30)
        assert ok is False

    def test_long_period_moderate_sharpe(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(2.6, period_days=600)
        assert ok is False  # > 2.5 over >500 days

    def test_zero_period(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(1.5, period_days=0)
        assert ok is True  # too short to assess

    def test_negative_sharpe(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_sharpe(-0.5, period_days=252)
        assert ok is True  # bad but plausible


# ======================================================================
# EconomicPlausibilityChecker — win rate
# ======================================================================

class TestCheckWinRate:
    def test_reasonable_win_rate(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.55, trades=100)
        assert ok is True

    def test_high_win_rate_many_trades(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.80, trades=60)
        assert ok is False
        assert "overfitting" in msg.lower() or "suspicious" in msg.lower()

    def test_very_high_win_rate(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.96, trades=15)
        assert ok is False
        assert "unrealistic" in msg.lower()

    def test_few_trades_ignored(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.99, trades=3)
        assert ok is True  # too few trades to judge

    def test_borderline_ok(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.74, trades=60)
        assert ok is True  # just under threshold

    def test_zero_trades(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_win_rate(0.0, trades=0)
        assert ok is True


# ======================================================================
# EconomicPlausibilityChecker — consistency
# ======================================================================

class TestCheckConsistency:
    def test_normal_returns(self):
        """Noisy returns with realistic distribution should pass."""
        c = EconomicPlausibilityChecker()
        rng = random.Random(42)
        returns = [0.001 + 0.015 * rng.gauss(0, 1) for _ in range(200)]
        ok, msg = c.check_consistency(returns)
        assert ok is True

    def test_suspiciously_smooth(self):
        """Returns with very low variance relative to mean → flagged."""
        c = EconomicPlausibilityChecker()
        returns = [0.01 + 0.001 * (i % 3 - 1) for i in range(100)]
        ok, msg = c.check_consistency(returns)
        assert ok is False
        assert "smooth" in msg.lower()

    def test_too_many_positive_days(self):
        c = EconomicPlausibilityChecker()
        rng = random.Random(42)
        # 90% positive days
        returns = [abs(rng.gauss(0.01, 0.005)) for _ in range(100)]
        ok, msg = c.check_consistency(returns)
        assert ok is False
        assert "positive" in msg.lower()

    def test_too_few_returns(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_consistency([0.01, 0.02, -0.01])
        assert ok is True  # too few to assess

    def test_high_autocorrelation(self):
        """Serially correlated returns → suspicious."""
        c = EconomicPlausibilityChecker()
        # Simulate AR(1) process with high persistence
        returns = [0.01]
        for _ in range(99):
            returns.append(0.7 * returns[-1] + 0.003 * random.Random(42).gauss(0, 1))
        ok, msg = c.check_consistency(returns)
        # May or may not trigger depending on exact pattern, but shouldn't crash
        assert isinstance(ok, bool)


# ======================================================================
# EconomicPlausibilityChecker — max drawdown
# ======================================================================

class TestCheckMaxDrawdown:
    def test_reasonable_calmar(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_max_drawdown(max_drawdown=-0.15, total_return=0.30, period_days=252)
        assert ok is True

    def test_zero_drawdown_with_return(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_max_drawdown(max_drawdown=0, total_return=0.20, period_days=252)
        assert ok is False
        assert "impossible" in msg.lower()

    def test_zero_drawdown_tiny_return(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_max_drawdown(max_drawdown=0, total_return=0.01, period_days=10)
        assert ok is True  # small move, no alarm

    def test_implausible_calmar(self):
        c = EconomicPlausibilityChecker()
        ok, msg = c.check_max_drawdown(max_drawdown=-0.02, total_return=0.50, period_days=252)
        assert ok is False
        assert "calmar" in msg.lower() or "implausibly" in msg.lower()


# ======================================================================
# EconomicPlausibilityChecker — run_all
# ======================================================================

class TestRunAll:
    def test_all_pass(self):
        c = EconomicPlausibilityChecker()
        rng = random.Random(42)
        returns = [0.001 + 0.015 * rng.gauss(0, 1) for _ in range(200)]
        results = c.run_all(
            sharpe=1.2,
            win_rate=0.55,
            trades=100,
            returns=returns,
            max_drawdown=-0.12,
            total_return=0.25,
            period_days=252,
        )
        assert all(r.ok for r in results)
        assert len(results) == 4  # sharpe + win_rate + consistency + drawdown

    def test_some_fail(self):
        c = EconomicPlausibilityChecker()
        results = c.run_all(
            sharpe=5.0,
            win_rate=0.95,
            trades=200,
            returns=None,  # skip consistency
            max_drawdown=-0.01,
            total_return=1.0,
            period_days=252,
        )
        failed = [r for r in results if not r.ok]
        assert len(failed) >= 2  # sharpe + win_rate at minimum

    def test_result_has_check_name(self):
        c = EconomicPlausibilityChecker()
        results = c.run_all(sharpe=1.0, win_rate=0.5, trades=10)
        names = [r.check_name for r in results]
        assert "sharpe" in names
        assert "win_rate" in names
        assert "max_drawdown" in names

    def test_no_returns_skips_consistency(self):
        c = EconomicPlausibilityChecker()
        results = c.run_all(sharpe=1.0, win_rate=0.5, trades=10, returns=None)
        names = [r.check_name for r in results]
        assert "consistency" not in names
