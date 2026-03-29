"""Tests for stub indicators not affecting score (Fix 5).

Verifies that stub indicators (ADX, VWAP, Ichimoku, Elder Ray) do NOT
influence the final score, even when their DNA weights are large.
"""

import math
import pytest

from src.evolution.auto_evolve import score_stock, StrategyDNA


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
    }


def test_stub_indicators_dont_affect_score():
    """Stub indicators (ADX, VWAP, Ichimoku, Elder Ray) should not influence score.

    Even if DNA evolves large weights for these stubs, the score should
    be identical because their effective weight is forced to 0.
    """
    idx = 50
    indicators = _make_indicators(idx)

    # DNA with all stub weights at 0
    dna_no_stubs = StrategyDNA(
        w_adx=0.0,
        w_vwap=0.0,
        w_ichimoku=0.0,
        w_elder_ray=0.0,
    )
    score_no_stubs = score_stock(idx, indicators, dna_no_stubs)

    # DNA with huge stub weights (should have no effect)
    dna_big_stubs = StrategyDNA(
        w_adx=1.0,
        w_vwap=1.0,
        w_ichimoku=1.0,
        w_elder_ray=1.0,
    )
    score_big_stubs = score_stock(idx, indicators, dna_big_stubs)

    # Scores should be identical (stub weights are forced to 0 in scoring)
    assert abs(score_no_stubs - score_big_stubs) < 1e-8, (
        f"Stub weights should have no effect. "
        f"Score with no stubs: {score_no_stubs:.6f}, "
        f"with big stubs: {score_big_stubs:.6f}"
    )
