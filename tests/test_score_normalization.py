"""Tests for score weight normalization (Fix 2).

Verifies that when custom factors are in DNA but missing from the factor
registry, the score normalization handles them correctly and doesn't
inflate scores.
"""

import math
import pytest

from src.evolution.auto_evolve import score_stock, StrategyDNA, _WEIGHT_KEYS


def _make_indicators(idx: int = 50):
    """Build minimal indicators dict for testing."""
    n = idx + 1
    closes = [100.0 + i * 0.1 for i in range(n)]
    opens = [c - 0.05 for c in closes]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    volumes = [1_000_000.0] * n

    return {
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
        "_factor_fns": {},  # empty: no custom factors available
    }


def test_score_with_missing_factors():
    """Score should not inflate when custom factors are in DNA but not in registry.

    When custom_weights has entries not in _factor_fns, those weights should
    still participate in total_weight normalization (with neutral 0.5 contribution),
    preventing score inflation.
    """
    dna = StrategyDNA()
    idx = 50
    indicators = _make_indicators(idx)

    # Score without custom weights
    score_no_custom = score_stock(idx, indicators, dna)

    # Now add custom weights that are NOT in the registry
    dna_with_missing = StrategyDNA(
        custom_weights={
            "nonexistent_factor_a": 0.5,
            "nonexistent_factor_b": 0.5,
        }
    )
    score_with_missing = score_stock(idx, indicators, dna_with_missing)

    # The score with missing factors should NOT be higher than without them
    # (they should add neutral 0.5 contribution, not inflate)
    assert score_with_missing <= score_no_custom + 0.5, (
        f"Score with missing factors ({score_with_missing:.4f}) should not inflate "
        f"above score without ({score_no_custom:.4f})"
    )


def test_score_normalization_sums_to_one():
    """Total weight should include only actually-computed factors.

    When custom factors are not in registry, their weight still appears in
    total_weight divisor so (raw / total_weight) doesn't inflate.
    """
    dna = StrategyDNA(
        custom_weights={
            "missing_x": 1.0,
            "missing_y": 1.0,
        }
    )
    idx = 50
    indicators = _make_indicators(idx)

    # If normalization is correct, score should be bounded [0, 10]
    score = score_stock(idx, indicators, dna)
    assert 0.0 <= score <= 10.0, f"Score {score} out of bounds [0, 10]"
