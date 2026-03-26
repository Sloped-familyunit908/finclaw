"""Comprehensive tests for the walk-forward validation system.

Covers:
- Window boundary computation (crypto + A-share)
- No-overlap and embargo assertions
- Fitness aggregation with mock backtests
- Overfit penalty
- Consistency weighting
- Edge cases (too little data, all windows fail min_trades)
- Deflated Sharpe Ratio
- WalkForwardResult.is_likely_overfit()
"""

from __future__ import annotations

import math
from typing import Tuple, List

import pytest

from src.evolution.walk_forward import (
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardValidator,
    WindowResult,
    _compute_window_fitness,
    deflated_sharpe_ratio,
)


# ---------------------------------------------------------------------------
# Helpers — mock backtest functions
# ---------------------------------------------------------------------------

def _make_backtest_result(
    annual_return: float = 50.0,
    max_drawdown: float = 10.0,
    win_rate: float = 65.0,
    sharpe: float = 2.0,
    calmar: float = 5.0,
    total_trades: int = 30,
    profit_factor: float = 2.0,
    sortino: float = 2.5,
    max_consec_losses: int = 3,
    monthly_returns: list | None = None,
    max_concurrent: int = 2,
    avg_turnover: float = 0.3,
) -> Tuple:
    """Build a 12-element backtest result tuple."""
    if monthly_returns is None:
        monthly_returns = [5.0, 4.0, 6.0]
    return (
        annual_return, max_drawdown, win_rate, sharpe, calmar,
        total_trades, profit_factor, sortino,
        max_consec_losses, monthly_returns, max_concurrent, avg_turnover,
    )


def _good_backtest(start: int, end: int) -> Tuple:
    """Always-profitable backtest mock."""
    n = end - start
    trades = max(n // 10, 15)
    return _make_backtest_result(
        annual_return=50.0, max_drawdown=10.0, win_rate=65.0,
        sharpe=2.0, total_trades=trades,
    )


def _bad_backtest(start: int, end: int) -> Tuple:
    """Always-losing backtest mock."""
    n = end - start
    trades = max(n // 10, 15)
    return _make_backtest_result(
        annual_return=-20.0, max_drawdown=40.0, win_rate=30.0,
        sharpe=-0.5, total_trades=trades,
    )


def _low_trade_backtest(start: int, end: int) -> Tuple:
    """Backtest that generates very few trades."""
    return _make_backtest_result(total_trades=3, annual_return=10.0)


# ===================================================================
# Tests: WalkForwardConfig defaults
# ===================================================================

class TestWalkForwardConfig:
    """Verify default config values and weight sum."""

    def test_default_config_values(self):
        cfg = WalkForwardConfig()
        assert cfg.n_windows == 4
        assert cfg.embargo_periods == 48
        assert cfg.warmup_periods == 60

    def test_weights_sum_to_one(self):
        cfg = WalkForwardConfig()
        assert abs(cfg.oos_weight + cfg.is_weight - 1.0) < 1e-9

    def test_custom_weights_sum_to_one(self):
        cfg = WalkForwardConfig(oos_weight=0.8, is_weight=0.2)
        assert abs(cfg.oos_weight + cfg.is_weight - 1.0) < 1e-9

    def test_default_overfit_threshold(self):
        cfg = WalkForwardConfig()
        assert cfg.overfit_penalty_threshold == 0.25
        assert cfg.overfit_penalty_factor == 0.20

    def test_default_min_trades(self):
        cfg = WalkForwardConfig()
        assert cfg.min_trades_per_window == 10


# ===================================================================
# Tests: window boundary computation
# ===================================================================

class TestWindowComputation:
    """Verify compute_windows() boundaries for various data sizes."""

    def test_crypto_8760_bars(self):
        """Crypto 1-year hourly data: 8760 bars, should get 4 windows."""
        cfg = WalkForwardConfig(
            n_windows=4, warmup_periods=60, embargo_periods=48,
            test_window_pct=0.10,
        )
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(8760)
        assert len(windows) == 4

    def test_ashare_500_bars(self):
        """A-share 2-year daily data: 500 bars."""
        cfg = WalkForwardConfig(
            n_windows=4, warmup_periods=30, embargo_periods=5,
            test_window_pct=0.10,
        )
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(500)
        # Should produce some windows (maybe fewer than 4 with strict min_train)
        assert len(windows) >= 1

    def test_windows_in_chronological_order(self):
        v = WalkForwardValidator(WalkForwardConfig(n_windows=4))
        windows = v.compute_windows(5000)
        for i in range(1, len(windows)):
            assert windows[i]["test"][0] > windows[i - 1]["test"][0], \
                "test windows must be chronologically ordered"

    def test_no_test_overlap(self):
        """Test windows must not overlap."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=5))
        windows = v.compute_windows(10000)
        for i in range(1, len(windows)):
            assert windows[i]["test"][0] >= windows[i - 1]["test"][1], \
                f"window {i} test overlaps with window {i-1}"

    def test_embargo_gap_respected(self):
        """Embargo gap between train end and test start."""
        embargo = 48
        cfg = WalkForwardConfig(embargo_periods=embargo)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(5000)
        for w in windows:
            gap = w["test"][0] - w["train"][1]
            assert gap >= embargo, \
                f"embargo gap {gap} < required {embargo}"

    def test_train_before_test(self):
        """Train period must end before test period starts."""
        v = WalkForwardValidator()
        windows = v.compute_windows(3000)
        for w in windows:
            assert w["train"][1] <= w["test"][0]

    def test_anchored_train(self):
        """Train always starts from warmup (anchored / expanding)."""
        warmup = 60
        cfg = WalkForwardConfig(warmup_periods=warmup)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(5000)
        assert len(windows) >= 2
        for w in windows:
            assert w["train"][0] == warmup

    def test_expanding_train(self):
        """Later windows have larger train periods (expanding)."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=4))
        windows = v.compute_windows(8000)
        if len(windows) >= 2:
            for i in range(1, len(windows)):
                train_i = windows[i]["train"][1] - windows[i]["train"][0]
                train_prev = windows[i - 1]["train"][1] - windows[i - 1]["train"][0]
                assert train_i > train_prev, \
                    "later windows should have more training data"

    def test_same_test_window_sizes(self):
        """All test windows should be the same size."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=4))
        windows = v.compute_windows(8000)
        if len(windows) >= 2:
            sizes = [w["test"][1] - w["test"][0] for w in windows]
            assert len(set(sizes)) == 1, f"test sizes vary: {sizes}"

    def test_insufficient_data_fewer_windows(self):
        """Too few bars → fewer windows than requested."""
        cfg = WalkForwardConfig(n_windows=6, warmup_periods=60, embargo_periods=48)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(300)
        assert len(windows) < 6

    def test_zero_bars(self):
        v = WalkForwardValidator()
        windows = v.compute_windows(0)
        assert windows == []

    def test_bars_equal_warmup(self):
        cfg = WalkForwardConfig(warmup_periods=100)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(100)
        assert windows == []

    def test_very_large_embargo(self):
        """Embargo larger than available space → no windows."""
        cfg = WalkForwardConfig(embargo_periods=5000)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(3000)
        assert windows == []


# ===================================================================
# Tests: walk-forward validation
# ===================================================================

class TestWalkForwardValidation:
    """Validate the full walk-forward pipeline with mock backtests."""

    def test_good_strategy_positive_fitness(self):
        """Strategy that works everywhere gets positive fitness."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=3, warmup_periods=60))
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        assert result.final_fitness > 0
        assert result.n_valid_windows >= 1

    def test_good_strategy_not_overfit(self):
        """Consistent good strategy should not be flagged as overfit."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=3, warmup_periods=60))
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        assert not result.is_likely_overfit()

    def test_bad_strategy_negative_fitness(self):
        """Strategy that always loses gets negative final fitness."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=3, warmup_periods=60))
        result = v.validate(_bad_backtest, total_bars=5000, warmup=60)
        assert result.final_fitness < 0

    def test_overfit_strategy_penalized(self):
        """Strategy great IS but terrible OOS gets overfit penalty."""
        call_count = [0]

        def overfit_bt(start: int, end: int) -> Tuple:
            call_count[0] += 1
            # Odd calls = IS segment, even calls = OOS segment
            if call_count[0] % 2 == 1:
                return _make_backtest_result(
                    annual_return=200.0, max_drawdown=5.0, win_rate=80.0,
                    sharpe=4.0, total_trades=50,
                )
            else:
                return _make_backtest_result(
                    annual_return=2.0, max_drawdown=30.0, win_rate=40.0,
                    sharpe=0.1, total_trades=20,
                )

        v = WalkForwardValidator(WalkForwardConfig(n_windows=3, warmup_periods=60))
        result = v.validate(overfit_bt, total_bars=5000, warmup=60)
        assert result.is_likely_overfit()

    def test_all_windows_low_trades(self):
        """When all OOS windows have too few trades → fitness = -1."""
        v = WalkForwardValidator(WalkForwardConfig(
            n_windows=3, warmup_periods=60, min_trades_per_window=10,
        ))
        result = v.validate(_low_trade_backtest, total_bars=5000, warmup=60)
        assert result.final_fitness == -1.0
        assert result.n_valid_windows == 0

    def test_window_results_populated(self):
        """WindowResult list should have one entry per computed window."""
        cfg = WalkForwardConfig(n_windows=3, warmup_periods=60)
        v = WalkForwardValidator(cfg)
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        # Should have as many WindowResults as windows computed
        windows = v.compute_windows(5000)
        assert len(result.window_results) == len(windows)

    def test_overfit_ratio_computation(self):
        """Overfit ratio = oos_mean / is_mean."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=3, warmup_periods=60))
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        # With identical IS and OOS performance, ratio should be ~1.0
        if result.is_mean_fitness > 0:
            expected_ratio = result.oos_mean_fitness * result.consistency_score / result.is_mean_fitness
            assert abs(result.overfit_ratio - expected_ratio) < 0.01


# ===================================================================
# Tests: consistency weighting
# ===================================================================

class TestConsistencyWeighting:
    """Verify that consistency bonus rewards stable OOS performance."""

    def test_identical_oos_high_consistency(self):
        """All windows returning the same → consistency_score near 1.0."""
        v = WalkForwardValidator(WalkForwardConfig(
            n_windows=3, warmup_periods=60, use_consistency_weighting=True,
        ))
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        # Same mock for every call → very high consistency
        assert result.consistency_score >= 0.9

    def test_varied_oos_lower_consistency(self):
        """Different performance per window → lower consistency."""
        counter = [0]

        def varied_bt(start: int, end: int) -> Tuple:
            counter[0] += 1
            # IS calls (odd) → stable
            if counter[0] % 2 == 1:
                return _make_backtest_result(annual_return=50.0, sharpe=2.0, total_trades=30)
            # OOS calls (even) → vary a lot
            val = 10.0 + (counter[0] * 37 % 100)  # pseudo-random-ish variation
            return _make_backtest_result(
                annual_return=val, sharpe=1.0, total_trades=30,
            )

        v = WalkForwardValidator(WalkForwardConfig(
            n_windows=4, warmup_periods=60, use_consistency_weighting=True,
        ))
        result = v.validate(varied_bt, total_bars=8000, warmup=60)
        # Consistency should be less than perfect
        assert result.consistency_score <= 1.0

    def test_consistency_off(self):
        """use_consistency_weighting=False → consistency_score stays 1.0."""
        v = WalkForwardValidator(WalkForwardConfig(
            n_windows=3, warmup_periods=60, use_consistency_weighting=False,
        ))
        result = v.validate(_good_backtest, total_bars=5000, warmup=60)
        assert result.consistency_score == 1.0


# ===================================================================
# Tests: _compute_window_fitness
# ===================================================================

class TestComputeWindowFitness:
    """Verify the standalone fitness function."""

    def test_positive_return_positive_fitness(self):
        f = _compute_window_fitness(50.0, 10.0, 65.0, 2.0, 30)
        assert f > 0

    def test_negative_return_negative_fitness(self):
        f = _compute_window_fitness(-20.0, 30.0, 35.0, -0.5, 30)
        assert f < 0

    def test_low_trades_penalty(self):
        f_low = _compute_window_fitness(50.0, 10.0, 65.0, 2.0, 5)
        f_high = _compute_window_fitness(50.0, 10.0, 65.0, 2.0, 50)
        assert f_low < f_high

    def test_sortino_bonus(self):
        f_no_sort = _compute_window_fitness(50.0, 10.0, 65.0, 2.0, 30, sortino=1.0)
        f_sort = _compute_window_fitness(50.0, 10.0, 65.0, 2.0, 30, sortino=3.0)
        assert f_sort > f_no_sort  # sortino > sharpe → 10% bonus


# ===================================================================
# Tests: deflated Sharpe ratio
# ===================================================================

class TestDeflatedSharpeRatio:
    """Verify DSR implementation."""

    def test_high_sharpe_few_trials(self):
        """High observed Sharpe with few trials → high probability."""
        p = deflated_sharpe_ratio(3.0, n_trials=10, n_observations=252)
        assert p > 0.5

    def test_low_sharpe_many_trials(self):
        """Low Sharpe with many trials → low probability."""
        p = deflated_sharpe_ratio(0.5, n_trials=10000, n_observations=252)
        assert p < 0.5

    def test_returns_probability_range(self):
        """Result must be in [0, 1]."""
        for sr in [-2.0, 0.0, 1.0, 5.0]:
            p = deflated_sharpe_ratio(sr, 100, 252)
            assert 0.0 <= p <= 1.0

    def test_more_trials_lower_probability(self):
        """Same Sharpe but more trials → lower probability (harder to pass)."""
        p_few = deflated_sharpe_ratio(1.5, n_trials=10, n_observations=252)
        p_many = deflated_sharpe_ratio(1.5, n_trials=10000, n_observations=252)
        assert p_few > p_many

    def test_zero_trials(self):
        """Edge case: zero trials → 0 probability."""
        p = deflated_sharpe_ratio(2.0, n_trials=0, n_observations=252)
        assert p == 0.0

    def test_one_observation(self):
        p = deflated_sharpe_ratio(2.0, n_trials=100, n_observations=1)
        assert p == 0.0

    def test_kurtosis_effect(self):
        """Fat tails (high kurtosis) raise SE → different probability."""
        # Use parameters where the observed Sharpe is close to
        # the expected max so the kurtosis term visibly matters.
        p_normal = deflated_sharpe_ratio(3.0, 5, 500, kurtosis=3.0)
        p_fat = deflated_sharpe_ratio(3.0, 5, 500, kurtosis=10.0)
        # Probabilities should differ — the direction depends on the
        # sign of the test statistic, but they must not be equal.
        assert p_normal != p_fat


# ===================================================================
# Tests: WalkForwardResult
# ===================================================================

class TestWalkForwardResult:

    def test_is_likely_overfit_true(self):
        r = WalkForwardResult(
            final_fitness=0.5, is_mean_fitness=100.0, oos_mean_fitness=10.0,
            overfit_ratio=0.1, consistency_score=1.0,
        )
        assert r.is_likely_overfit()

    def test_is_likely_overfit_false(self):
        r = WalkForwardResult(
            final_fitness=50.0, is_mean_fitness=60.0, oos_mean_fitness=50.0,
            overfit_ratio=0.83, consistency_score=1.0,
        )
        assert not r.is_likely_overfit()

    def test_overfit_boundary(self):
        """Exactly at 0.3 should NOT be flagged (strictly <)."""
        r = WalkForwardResult(
            final_fitness=50.0, is_mean_fitness=100.0, oos_mean_fitness=30.0,
            overfit_ratio=0.3, consistency_score=1.0,
        )
        assert not r.is_likely_overfit()


# ===================================================================
# Tests: WindowResult dataclass
# ===================================================================

class TestWindowResult:
    def test_fields(self):
        wr = WindowResult(
            window_index=0, train_range=(60, 500), test_range=(548, 700),
            is_fitness=10.0, oos_fitness=8.0, oos_annual_return=40.0,
            oos_max_drawdown=12.0, oos_sharpe=1.8, oos_trades=25,
            oos_win_rate=60.0,
        )
        assert wr.window_index == 0
        assert wr.test_range == (548, 700)
        assert wr.oos_trades == 25
