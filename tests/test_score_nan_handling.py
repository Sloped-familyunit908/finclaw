"""Tests for NaN handling in score_stock (Fix 4).

Verifies that score_stock gracefully handles NaN values in core indicators
instead of returning 0.0 when ANY indicator is NaN.
"""

import math
import pytest

from src.evolution.auto_evolve import score_stock, StrategyDNA


def _make_indicators(idx: int = 50, nan_keys=None):
    """Build indicators dict with optional NaN values for specified keys."""
    n = idx + 1
    closes = [100.0 + i * 0.1 for i in range(n)]
    opens = [c - 0.05 for c in closes]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    volumes = [1_000_000.0] * n

    indicators = {
        "rsi": [50.0] * n,
        "r2": [0.8] * n,
        "slope": [1.0] * n,
        "volume_ratio": [1.5] * n,
        "close": closes,
        "open": opens,
        "high": highs,
        "low": lows,
        "volume": volumes,
        "ma_alignment": [0.0] * n,
        "macd_line": [0.0] * n,
        "macd_signal": [0.0] * n,
        "macd_hist": [0.01] * n,
        "bb_upper": [c + 2 for c in closes],
        "bb_middle": closes[:],
        "bb_lower": [c - 2 for c in closes],
        "kdj_k": [50.0] * n,
        "kdj_d": [45.0] * n,
        "kdj_j": [60.0] * n,
        "obv_trend": [0.1] * n,
        "atr_pct": [2.0] * n,
        "roc": [3.0] * n,
        "williams_r": [-50.0] * n,
        "cci": [0.0] * n,
        "mfi": [50.0] * n,
        "donchian_pos": [0.5] * n,
        "aroon": [0.0] * n,
        "pv_corr": [0.0] * n,
        "fundamentals": {},
    }

    # Set specified keys to NaN at the target index
    if nan_keys:
        for key in nan_keys:
            if key in indicators:
                indicators[key][idx] = float("nan")

    return indicators


def test_score_with_some_nan_indicators():
    """Score should use available indicators when some are NaN.

    If RSI is NaN but R², slope, and volume_ratio are valid, the score
    should still be computed from the available indicators — not return 0.
    """
    dna = StrategyDNA()
    idx = 50

    # Score with all indicators valid
    indicators_good = _make_indicators(idx)
    score_good = score_stock(idx, indicators_good, dna)
    assert score_good > 0.0, f"Good score should be > 0, got {score_good}"

    # Score with RSI as NaN (only 1 of 4 core indicators)
    indicators_partial = _make_indicators(idx, nan_keys=["rsi"])
    score_partial = score_stock(idx, indicators_partial, dna)

    # Should NOT return 0 — should use remaining valid indicators
    assert score_partial > 0.0, (
        f"Score with 1 NaN indicator should be > 0, got {score_partial}"
    )
    # Should be different from all-good score (RSI contribution replaced by neutral)
    # But still within reasonable range
    assert 0.0 < score_partial <= 10.0, (
        f"Score with NaN RSI out of bounds: {score_partial}"
    )


def test_score_with_two_nan_indicators():
    """Score should still compute with 2 of 4 core indicators NaN."""
    dna = StrategyDNA()
    idx = 50

    indicators = _make_indicators(idx, nan_keys=["rsi", "volume_ratio"])
    score = score_stock(idx, indicators, dna)

    assert score > 0.0, (
        f"Score with 2 NaN indicators should be > 0, got {score}"
    )


def test_score_all_nan_returns_neutral():
    """All 4 core indicators NaN should return neutral score (5.0), not zero."""
    dna = StrategyDNA()
    idx = 50

    indicators = _make_indicators(
        idx, nan_keys=["rsi", "r2", "slope", "volume_ratio"]
    )
    score = score_stock(idx, indicators, dna)

    # Should return neutral 5.0 (the midpoint), NOT 0.0
    assert score == 5.0, (
        f"Score with all NaN should return 5.0 (neutral), got {score}"
    )
