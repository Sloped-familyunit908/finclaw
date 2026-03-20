"""Tests for src.indicators.alpha_factors — Qlib-inspired alpha factors."""

import math
import sys
import os

import numpy as np
import pytest

# Ensure the project src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from indicators.alpha_factors import (
    beta,
    rsqr,
    corr_price_volume,
    aroon,
    trend_quality,
    _rolling_linear_regression,
)


# ── helpers ──────────────────────────────────────────────────────────

def _assert_nan_prefix(arr: np.ndarray, count: int):
    """First *count* elements should be NaN."""
    for i in range(count):
        assert np.isnan(arr[i]), f"arr[{i}] = {arr[i]}, expected NaN"


def _assert_finite_suffix(arr: np.ndarray, start: int):
    """Elements from *start* onward should be finite."""
    for i in range(start, len(arr)):
        assert np.isfinite(arr[i]), f"arr[{i}] = {arr[i]}, expected finite"


# ══════════════════════════════════════════════════════════════════════
# BETA
# ══════════════════════════════════════════════════════════════════════

class TestBeta:
    """BETA: normalised linear-regression slope."""

    def test_uptrend_positive(self):
        """Monotonically rising close → positive BETA."""
        close = np.arange(1.0, 31.0)  # 1, 2, …, 30
        result = beta(close, window=20)
        _assert_nan_prefix(result, 19)
        assert np.all(result[19:] > 0), "BETA should be positive for uptrend"

    def test_downtrend_negative(self):
        """Monotonically falling close → negative BETA."""
        close = np.arange(30.0, 0.0, -1.0)
        result = beta(close, window=20)
        _assert_nan_prefix(result, 19)
        assert np.all(result[19:] < 0), "BETA should be negative for downtrend"

    def test_constant_series_zero(self):
        """Constant price → BETA = 0."""
        close = np.full(30, 100.0)
        result = beta(close, window=20)
        _assert_nan_prefix(result, 19)
        np.testing.assert_allclose(result[19:], 0.0, atol=1e-12)

    def test_arithmetic_sequence_known_value(self):
        """Arithmetic sequence 0, 1, 2, … → slope = 1 → beta = slope / close.

        For close = [0,1,2,…], at position k (window w):
            slope = 1  (perfect linear fit with increment 1)
            beta  = 1/close[k]
        """
        close = np.arange(0.0, 40.0)
        result = beta(close, window=5)
        # At index 4: close=4, slope=1, beta=1/4=0.25
        assert abs(result[4] - 1.0 / 4.0) < 1e-6
        # At index 10: close=10, slope=1, beta=0.1
        assert abs(result[10] - 1.0 / 10.0) < 1e-6

    def test_cross_validate_with_polyfit(self):
        """Cross-validate rolling slope against np.polyfit."""
        rng = np.random.default_rng(42)
        close = np.cumsum(rng.standard_normal(50)) + 100
        window = 10
        result = beta(close, window=window)

        for k in range(window - 1, len(close)):
            seg = close[k - window + 1: k + 1]
            x = np.arange(window, dtype=float)
            coeffs = np.polyfit(x, seg, 1)
            expected_slope = coeffs[0]
            expected_beta = expected_slope / close[k]
            np.testing.assert_allclose(result[k], expected_beta, rtol=1e-6,
                                       err_msg=f"Mismatch at index {k}")

    def test_empty_array(self):
        """Empty input → empty output."""
        result = beta(np.array([]), window=5)
        assert len(result) == 0

    def test_short_array(self):
        """Array shorter than window → all NaN."""
        close = np.array([1.0, 2.0, 3.0])
        result = beta(close, window=10)
        assert np.all(np.isnan(result))

    def test_nan_prefix_length(self):
        """First window-1 values must be NaN."""
        close = np.arange(1.0, 26.0)
        for w in [5, 10, 20]:
            result = beta(close, window=w)
            _assert_nan_prefix(result, w - 1)
            _assert_finite_suffix(result, w - 1)


# ══════════════════════════════════════════════════════════════════════
# RSQR
# ══════════════════════════════════════════════════════════════════════

class TestRsqr:
    """RSQR: R-squared of rolling linear regression."""

    def test_perfect_linear_r2_one(self):
        """Perfect linear series → R² = 1.0."""
        close = np.arange(1.0, 31.0)
        result = rsqr(close, window=20)
        _assert_nan_prefix(result, 19)
        np.testing.assert_allclose(result[19:], 1.0, atol=1e-8)

    def test_range_zero_one(self):
        """R² must always be in [0, 1]."""
        rng = np.random.default_rng(123)
        close = np.cumsum(rng.standard_normal(100)) + 100
        result = rsqr(close, window=10)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0.0), "R² should be >= 0"
        assert np.all(valid <= 1.0), "R² should be <= 1"

    def test_constant_series_r2_one(self):
        """Constant series → R² = 1 (zero residual)."""
        close = np.full(30, 42.0)
        result = rsqr(close, window=10)
        _assert_nan_prefix(result, 9)
        np.testing.assert_allclose(result[9:], 1.0, atol=1e-10)

    def test_noisy_data_lower_r2(self):
        """Adding noise should lower R² compared to a clean line."""
        clean = np.linspace(10, 20, 40)
        noisy = clean + np.random.default_rng(0).standard_normal(40) * 3
        r2_clean = rsqr(clean, window=10)
        r2_noisy = rsqr(noisy, window=10)
        # On average, noisy R² should be lower
        assert np.nanmean(r2_noisy) < np.nanmean(r2_clean)

    def test_cross_validate_with_polyfit(self):
        """Cross-validate against np.polyfit residuals."""
        rng = np.random.default_rng(99)
        close = np.cumsum(rng.standard_normal(50)) + 100
        window = 8
        result = rsqr(close, window=window)

        for k in range(window - 1, len(close)):
            seg = close[k - window + 1: k + 1]
            x = np.arange(window, dtype=float)
            coeffs = np.polyfit(x, seg, 1)
            predicted = np.polyval(coeffs, x)
            ss_res = np.sum((seg - predicted) ** 2)
            ss_tot = np.sum((seg - np.mean(seg)) ** 2)
            expected = 1.0 - ss_res / ss_tot if ss_tot > 1e-30 else 1.0
            np.testing.assert_allclose(result[k], expected, atol=1e-6,
                                       err_msg=f"R² mismatch at index {k}")

    def test_empty_array(self):
        result = rsqr(np.array([]), window=5)
        assert len(result) == 0

    def test_short_array(self):
        close = np.array([1.0, 2.0])
        result = rsqr(close, window=10)
        assert np.all(np.isnan(result))


# ══════════════════════════════════════════════════════════════════════
# CORR (price-volume correlation)
# ══════════════════════════════════════════════════════════════════════

class TestCorrPriceVolume:
    """CORR: Pearson correlation between close and log(volume+1)."""

    def test_positive_correlation(self):
        """Price and volume both rising → positive correlation."""
        close = np.arange(1.0, 31.0)
        volume = np.arange(100.0, 130.0)
        result = corr_price_volume(close, volume, window=10)
        _assert_nan_prefix(result, 9)
        assert np.all(result[9:] > 0.9), "Should be strongly positive"

    def test_negative_correlation(self):
        """Price up, volume down → negative correlation."""
        close = np.arange(1.0, 31.0)
        volume = np.arange(130.0, 100.0, -1.0)
        result = corr_price_volume(close, volume, window=10)
        _assert_nan_prefix(result, 9)
        assert np.all(result[9:] < -0.9), "Should be strongly negative"

    def test_range_minus1_plus1(self):
        """Correlation must always be in [-1, 1]."""
        rng = np.random.default_rng(77)
        close = np.cumsum(rng.standard_normal(100)) + 100
        volume = np.abs(rng.standard_normal(100)) * 10000
        result = corr_price_volume(close, volume, window=15)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= -1.0), "Corr should be >= -1"
        assert np.all(valid <= 1.0), "Corr should be <= 1"

    def test_constant_price_zero_corr(self):
        """Constant price → correlation is 0 (or undefined → 0)."""
        close = np.full(30, 50.0)
        volume = np.arange(1.0, 31.0)
        result = corr_price_volume(close, volume, window=10)
        _assert_nan_prefix(result, 9)
        np.testing.assert_allclose(result[9:], 0.0, atol=1e-10)

    def test_cross_validate_with_corrcoef(self):
        """Cross-validate against np.corrcoef."""
        rng = np.random.default_rng(55)
        close = np.cumsum(rng.standard_normal(40)) + 100
        volume = np.abs(rng.standard_normal(40)) * 5000 + 100
        window = 10
        result = corr_price_volume(close, volume, window=window)

        log_vol = np.log(volume + 1)
        for k in range(window - 1, len(close)):
            seg_c = close[k - window + 1: k + 1]
            seg_v = log_vol[k - window + 1: k + 1]
            expected = np.corrcoef(seg_c, seg_v)[0, 1]
            np.testing.assert_allclose(result[k], expected, atol=1e-6,
                                       err_msg=f"Corr mismatch at index {k}")

    def test_empty_array(self):
        result = corr_price_volume(np.array([]), np.array([]), window=5)
        assert len(result) == 0

    def test_short_array(self):
        close = np.array([1.0, 2.0])
        volume = np.array([100.0, 200.0])
        result = corr_price_volume(close, volume, window=10)
        assert np.all(np.isnan(result))


# ══════════════════════════════════════════════════════════════════════
# AROON
# ══════════════════════════════════════════════════════════════════════

class TestAroon:
    """Aroon indicator: aroon_up, aroon_down, aroon_oscillator."""

    def test_strong_uptrend(self):
        """Monotonically rising highs → aroon_up = 100."""
        high = np.arange(1.0, 31.0)
        low = high - 0.5
        up, down, osc = aroon(high, low, window=10)
        _assert_nan_prefix(up, 9)
        # Highest high is always the latest bar → aroon_up = 100
        np.testing.assert_allclose(up[9:], 100.0, atol=1e-10)

    def test_strong_downtrend(self):
        """Monotonically falling lows → aroon_down = 100."""
        low = np.arange(30.0, 0.0, -1.0)
        high = low + 0.5
        up, down, osc = aroon(high, low, window=10)
        _assert_nan_prefix(down, 9)
        # Lowest low always on the latest bar → aroon_down = 100
        np.testing.assert_allclose(down[9:], 100.0, atol=1e-10)

    def test_oscillator_range(self):
        """Aroon oscillator must be in [-100, 100]."""
        rng = np.random.default_rng(33)
        high = np.cumsum(np.abs(rng.standard_normal(50))) + 100
        low = high - np.abs(rng.standard_normal(50))
        _, _, osc = aroon(high, low, window=15)
        valid = osc[~np.isnan(osc)]
        assert np.all(valid >= -100.0)
        assert np.all(valid <= 100.0)

    def test_known_values(self):
        """Manual example: window=5, verify against hand calculation.

        highs = [5, 4, 3, 2, 1, 6]  (length 6, window 5)
        For index 4 (window=[5,4,3,2,1]):
            highest at index 0 (value 5), days_since = 4
            aroon_up = 100 * (5-4) / 5 = 20
        For index 5 (window=[4,3,2,1,6]):
            highest at index 4 (value 6), days_since = 0
            aroon_up = 100 * 5 / 5 = 100
        """
        high = np.array([5.0, 4.0, 3.0, 2.0, 1.0, 6.0])
        low = np.array([4.0, 3.0, 2.0, 1.0, 0.0, 5.0])
        up, down, osc = aroon(high, low, window=5)

        # Index 4 (window covers indices 0-4)
        assert abs(up[4] - 20.0) < 1e-10
        # Index 5 (window covers indices 1-5): highest = 6 at index 5 → days_since=0
        assert abs(up[5] - 100.0) < 1e-10

    def test_nan_prefix_length(self):
        """First window-1 values must be NaN."""
        high = np.arange(1.0, 31.0)
        low = high - 0.5
        for w in [5, 10, 25]:
            up, down, osc = aroon(high, low, window=w)
            _assert_nan_prefix(up, w - 1)
            _assert_nan_prefix(down, w - 1)
            _assert_nan_prefix(osc, w - 1)

    def test_empty_array(self):
        up, down, osc = aroon(np.array([]), np.array([]), window=5)
        assert len(up) == 0
        assert len(down) == 0
        assert len(osc) == 0

    def test_short_array(self):
        high = np.array([1.0, 2.0])
        low = np.array([0.5, 1.5])
        up, down, osc = aroon(high, low, window=10)
        assert np.all(np.isnan(up))
        assert np.all(np.isnan(down))


# ══════════════════════════════════════════════════════════════════════
# TREND QUALITY
# ══════════════════════════════════════════════════════════════════════

class TestTrendQuality:
    """trend_quality: BETA × RSQR composite."""

    def test_clear_uptrend_positive(self):
        """Perfect uptrend → positive trend quality."""
        close = np.arange(1.0, 31.0)
        result = trend_quality(close, window=10)
        _assert_nan_prefix(result, 9)
        assert np.all(result[9:] > 0)

    def test_clear_downtrend_negative(self):
        """Perfect downtrend → negative trend quality."""
        close = np.arange(30.0, 0.0, -1.0)
        result = trend_quality(close, window=10)
        _assert_nan_prefix(result, 9)
        assert np.all(result[9:] < 0)

    def test_constant_zero(self):
        """Constant price → trend quality = 0."""
        close = np.full(30, 100.0)
        result = trend_quality(close, window=10)
        _assert_nan_prefix(result, 9)
        np.testing.assert_allclose(result[9:], 0.0, atol=1e-12)

    def test_equals_beta_times_rsqr(self):
        """trend_quality should exactly equal beta * rsqr."""
        rng = np.random.default_rng(11)
        close = np.cumsum(rng.standard_normal(50)) + 100
        w = 15
        tq = trend_quality(close, window=w)
        b = beta(close, window=w)
        r = rsqr(close, window=w)
        expected = b * r
        np.testing.assert_allclose(tq, expected, atol=1e-15)

    def test_noisy_lower_quality(self):
        """Adding noise lowers trend quality magnitude."""
        clean = np.linspace(10, 30, 40)
        noisy = clean + np.random.default_rng(7).standard_normal(40) * 5
        tq_clean = trend_quality(clean, window=10)
        tq_noisy = trend_quality(noisy, window=10)
        assert np.nanmean(np.abs(tq_clean)) > np.nanmean(np.abs(tq_noisy))

    def test_empty_array(self):
        result = trend_quality(np.array([]), window=5)
        assert len(result) == 0


# ══════════════════════════════════════════════════════════════════════
# HELPER: _rolling_linear_regression
# ══════════════════════════════════════════════════════════════════════

class TestRollingLinearRegression:
    """Verify the internal helper directly."""

    def test_perfect_line(self):
        y = np.arange(10.0)
        slope, rsq = _rolling_linear_regression(y, 5)
        _assert_nan_prefix(slope, 4)
        np.testing.assert_allclose(slope[4:], 1.0, atol=1e-10)
        np.testing.assert_allclose(rsq[4:], 1.0, atol=1e-10)

    def test_window_2(self):
        """Window of 2 → slope = diff of consecutive elements."""
        y = np.array([3.0, 7.0, 1.0, 5.0])
        slope, rsq = _rolling_linear_regression(y, 2)
        assert np.isnan(slope[0])
        np.testing.assert_allclose(slope[1], 4.0, atol=1e-10)  # 7-3
        np.testing.assert_allclose(slope[2], -6.0, atol=1e-10)  # 1-7
        np.testing.assert_allclose(slope[3], 4.0, atol=1e-10)  # 5-1
        # 2 points always give R²=1
        np.testing.assert_allclose(rsq[1:], 1.0, atol=1e-10)

    def test_too_short(self):
        y = np.array([1.0, 2.0])
        slope, rsq = _rolling_linear_regression(y, 5)
        assert np.all(np.isnan(slope))
        assert np.all(np.isnan(rsq))
