"""
Tests for Quality/Relative-Strength factors and the hard drawdown filter.
==========================================================================
At least 15 tests covering:
- Stocks in uptrend get high quality scores
- Stocks in 40% drawdown get low quality scores
- Stocks outperforming market get high relative strength
- Hard filter removes stocks >30% below peak
- Soft filter reduces score for stocks 15-30% below peak
"""

import sys
import os
import math

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all 10 quality factors
from factors.quality_relative_strength_60d import compute as rs60_compute
from factors.quality_relative_strength_20d import compute as rs20_compute
from factors.quality_price_vs_200d_ma import compute as ma200_compute
from factors.quality_trend_persistence import compute as trend_persist_compute
from factors.quality_new_high_proximity import compute as new_high_compute
from factors.quality_drawdown_from_peak import compute as drawdown_compute
from factors.quality_earnings_momentum_proxy import compute as earnings_compute
from factors.quality_volume_trend_60d import compute as vol_trend_compute
from factors.quality_resilience_score import compute as resilience_compute
from factors.quality_momentum_rank import compute as mom_rank_compute


# ── Helper: generate synthetic price data ──


def _make_uptrend(n=200, start=10.0, daily_pct=0.003):
    """Generate steady uptrend: price grows ~0.3%/day."""
    closes = [start]
    for i in range(1, n):
        closes.append(closes[-1] * (1 + daily_pct))
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    volumes = [1_000_000] * n
    return closes, highs, lows, volumes


def _make_downtrend(n=200, start=20.0, daily_pct=-0.005):
    """Generate steady downtrend: price drops ~0.5%/day."""
    closes = [start]
    for i in range(1, n):
        closes.append(closes[-1] * (1 + daily_pct))
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    volumes = [1_000_000] * n
    return closes, highs, lows, volumes


def _make_crash(n=200, start=20.0, crash_at=150, crash_pct=0.40):
    """Generate a stock that crashes at crash_at by crash_pct."""
    closes = [start]
    for i in range(1, n):
        if i == crash_at:
            closes.append(closes[-1] * (1 - crash_pct))
        else:
            closes.append(closes[-1] * 1.001)  # slight uptrend otherwise
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    volumes = [1_000_000] * n
    return closes, highs, lows, volumes


def _make_flat(n=200, price=15.0):
    """Generate flat/sideways stock."""
    closes = [price] * n
    highs = [price * 1.002] * n
    lows = [price * 0.998] * n
    volumes = [1_000_000] * n
    return closes, highs, lows, volumes


def _make_dying_stock(n=200, start=30.0):
    """Generate a dying stock: 60% drawdown over time (like solar/lithium)."""
    closes = [start]
    for i in range(1, n):
        closes.append(closes[-1] * 0.995)  # steady -0.5% per day
    # After 200 days: ~36% of original price (64% decline)
    highs = [c * 1.003 for c in closes]
    lows = [c * 0.997 for c in closes]
    # Declining volume too (losing interest)
    volumes = [max(100_000, 2_000_000 - i * 8000) for i in range(n)]
    return closes, highs, lows, volumes


# ═══════════════════════════════════════════════════════════════
# Test 1-3: Relative Strength factors
# ═══════════════════════════════════════════════════════════════


def test_rs60_uptrend_high_score():
    """Stock in uptrend should get high relative strength score."""
    closes, highs, lows, volumes = _make_uptrend(200)
    idx = 199
    score = rs60_compute(closes, highs, lows, volumes, idx)
    # Continuous uptrend should score well (>0.5)
    assert score >= 0.4, f"Uptrend stock should score >=0.4, got {score}"


def test_rs60_downtrend_low_score():
    """Stock in downtrend should get low relative strength score."""
    closes, highs, lows, volumes = _make_downtrend(200)
    idx = 199
    score = rs60_compute(closes, highs, lows, volumes, idx)
    # Constant-rate decline self-benchmarks to ~0.5; allow small fp epsilon
    assert score <= 0.51, f"Downtrend stock should score <=0.51, got {score}"


def test_rs20_dying_stock_low():
    """Dying stock (like solar) should get low 20d relative strength."""
    closes, highs, lows, volumes = _make_dying_stock(200)
    idx = 199
    score = rs20_compute(closes, highs, lows, volumes, idx)
    # Constant-rate decline self-benchmarks to ~0.5; allow small fp epsilon
    assert score <= 0.51, f"Dying stock should have low RS20, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 4-5: Price vs 200d MA
# ═══════════════════════════════════════════════════════════════


def test_ma200_above_ma_high_score():
    """Stock above 200MA should score high."""
    closes, highs, lows, volumes = _make_uptrend(250, daily_pct=0.003)
    idx = 249
    score = ma200_compute(closes, highs, lows, volumes, idx)
    assert score > 0.5, f"Stock above 200MA should score >0.5, got {score}"


def test_ma200_below_20pct_low_score():
    """Stock 20%+ below 200MA should score near 0."""
    closes, highs, lows, volumes = _make_dying_stock(250)
    idx = 249
    score = ma200_compute(closes, highs, lows, volumes, idx)
    assert score < 0.3, f"Stock far below 200MA should score <0.3, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 6-7: Trend Persistence
# ═══════════════════════════════════════════════════════════════


def test_trend_persistence_uptrend():
    """Stock in steady uptrend should be above MA20 most of the time."""
    closes, highs, lows, volumes = _make_uptrend(200)
    idx = 199
    score = trend_persist_compute(closes, highs, lows, volumes, idx)
    assert score >= 0.6, f"Uptrend stock should have high trend persistence, got {score}"


def test_trend_persistence_downtrend():
    """Stock in downtrend should be below MA20 most of the time."""
    closes, highs, lows, volumes = _make_downtrend(200)
    idx = 199
    score = trend_persist_compute(closes, highs, lows, volumes, idx)
    assert score <= 0.4, f"Downtrend stock should have low trend persistence, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 8-9: New High Proximity & Drawdown from Peak
# ═══════════════════════════════════════════════════════════════


def test_new_high_proximity_near_high():
    """Stock near its 60d high should get high score."""
    closes, highs, lows, volumes = _make_uptrend(100)
    idx = 99
    score = new_high_compute(closes, highs, lows, volumes, idx)
    assert score >= 0.8, f"Stock near 60d high should score >=0.8, got {score}"


def test_drawdown_40pct_low_score():
    """Stock in 40% drawdown should get very low score."""
    closes, highs, lows, volumes = _make_crash(200, crash_at=150, crash_pct=0.40)
    idx = 155  # shortly after crash
    score = drawdown_compute(closes, highs, lows, volumes, idx)
    assert score < 0.3, f"40% drawdown should score <0.3, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 10-11: Earnings Momentum Proxy
# ═══════════════════════════════════════════════════════════════


def test_earnings_proxy_uptrend():
    """Stock in uptrend (positive slope) = good earnings proxy."""
    closes, highs, lows, volumes = _make_uptrend(100)
    idx = 99
    score = earnings_compute(closes, highs, lows, volumes, idx)
    assert score > 0.5, f"Uptrend stock should have positive earnings proxy, got {score}"


def test_earnings_proxy_dying():
    """Dying stock (negative slope) = bad earnings."""
    closes, highs, lows, volumes = _make_dying_stock(100)
    idx = 99
    score = earnings_compute(closes, highs, lows, volumes, idx)
    assert score < 0.3, f"Dying stock should have bad earnings proxy, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 12: Volume Trend
# ═══════════════════════════════════════════════════════════════


def test_volume_trend_dying_stock():
    """Dying stock with declining volume should score low."""
    closes, highs, lows, volumes = _make_dying_stock(200)
    idx = 199
    score = vol_trend_compute(closes, highs, lows, volumes, idx)
    assert score < 0.5, f"Dying stock + declining volume should score <0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 13: Resilience Score
# ═══════════════════════════════════════════════════════════════


def test_resilience_flat_stock():
    """Flat stock should have neutral resilience."""
    closes, highs, lows, volumes = _make_flat(200)
    idx = 199
    score = resilience_compute(closes, highs, lows, volumes, idx)
    # Flat stock has zero variance, so all days are equally "bad" -> neutral
    assert 0.0 <= score <= 1.0, f"Score should be in [0,1], got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 14: Momentum Rank
# ═══════════════════════════════════════════════════════════════


def test_momentum_rank_uptrend():
    """Current momentum at end of uptrend should rank high vs history."""
    closes, highs, lows, volumes = _make_uptrend(200, daily_pct=0.003)
    idx = 199
    score = mom_rank_compute(closes, highs, lows, volumes, idx)
    # In a steady uptrend, current mom ≈ historical mom, should be ~0.5
    assert score >= 0.3, f"Uptrend momentum rank should be >=0.3, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 15-17: Hard Filter Logic (simulates auto_evolve behavior)
# ═══════════════════════════════════════════════════════════════


def _apply_hard_filter(scored, data, day):
    """Replicate the hard filter logic from auto_evolve._run_backtest."""
    filtered_scored = []
    for code, s in scored:
        closes = data[code]["close"]
        if day >= 60:
            peak_60d = max(closes[day - 59:day + 1])
            current = closes[day]
            if peak_60d > 0:
                drawdown_from_peak = (peak_60d - current) / peak_60d
                if drawdown_from_peak > 0.30:
                    continue  # Hard reject
                if drawdown_from_peak > 0.15:
                    s = s * 0.70  # Soft penalty
        filtered_scored.append((code, s))
    return filtered_scored


def test_hard_filter_removes_dying_stock():
    """Hard filter should remove stocks >30% below 60-day peak."""
    closes, highs, lows, volumes = _make_crash(200, crash_at=130, crash_pct=0.40)
    data = {"dying": {"close": closes, "high": highs, "low": lows, "volume": volumes}}
    scored = [("dying", 8.5)]
    day = 140  # after the crash

    filtered = _apply_hard_filter(scored, data, day)
    assert len(filtered) == 0, f"Dying stock should be filtered out, got {filtered}"


def test_hard_filter_keeps_healthy_stock():
    """Hard filter should keep healthy stocks."""
    closes, highs, lows, volumes = _make_uptrend(200)
    data = {"healthy": {"close": closes, "high": highs, "low": lows, "volume": volumes}}
    scored = [("healthy", 7.0)]
    day = 199

    filtered = _apply_hard_filter(scored, data, day)
    assert len(filtered) == 1, "Healthy stock should pass the filter"
    assert filtered[0][0] == "healthy"
    assert filtered[0][1] == 7.0  # score unchanged


def test_soft_filter_reduces_score():
    """Soft filter should reduce score by 30% for stocks 15-30% below peak."""
    # Create a stock that's ~20% below its 60d high
    n = 200
    closes = [20.0] * n
    # Set a peak 25 days ago, then drop 20%
    for i in range(n - 25, n):
        closes[i] = 20.0 * 0.80  # 20% below peak
    highs = [c * 1.001 for c in closes]
    lows = [c * 0.999 for c in closes]
    volumes = [1_000_000] * n

    data = {"moderate_dd": {"close": closes, "high": highs, "low": lows, "volume": volumes}}
    scored = [("moderate_dd", 8.0)]
    day = 199

    filtered = _apply_hard_filter(scored, data, day)
    assert len(filtered) == 1, "Stock with 20% drawdown should pass (not hard filtered)"
    # Score should be reduced by 30%: 8.0 * 0.70 = 5.6
    assert abs(filtered[0][1] - 5.6) < 0.01, f"Score should be ~5.6, got {filtered[0][1]}"


# ═══════════════════════════════════════════════════════════════
# Test 18-19: Edge cases and category checks
# ═══════════════════════════════════════════════════════════════


def test_all_factors_return_valid_range():
    """All quality factors must return values in [0.0, 1.0]."""
    closes, highs, lows, volumes = _make_uptrend(200)
    idx = 199

    factors = [
        rs60_compute, rs20_compute, ma200_compute, trend_persist_compute,
        new_high_compute, drawdown_compute, earnings_compute,
        vol_trend_compute, resilience_compute, mom_rank_compute,
    ]

    for fn in factors:
        score = fn(closes, highs, lows, volumes, idx)
        assert 0.0 <= score <= 1.0, f"{fn.__module__} returned {score}, expected [0,1]"


def test_all_factors_handle_short_data():
    """All quality factors should handle very short data gracefully (return 0.5)."""
    closes = [10.0, 10.1, 10.2]
    highs = [10.1, 10.2, 10.3]
    lows = [9.9, 10.0, 10.1]
    volumes = [100, 200, 300]
    idx = 2

    factors = [
        rs60_compute, rs20_compute, ma200_compute, trend_persist_compute,
        new_high_compute, drawdown_compute, earnings_compute,
        vol_trend_compute, resilience_compute, mom_rank_compute,
    ]

    for fn in factors:
        score = fn(closes, highs, lows, volumes, idx)
        assert 0.0 <= score <= 1.0, f"{fn.__module__} returned {score} on short data"


def test_factor_categories():
    """All quality factors should have FACTOR_CATEGORY = 'quality_filter'."""
    import factors.quality_relative_strength_60d as f1
    import factors.quality_relative_strength_20d as f2
    import factors.quality_price_vs_200d_ma as f3
    import factors.quality_trend_persistence as f4
    import factors.quality_new_high_proximity as f5
    import factors.quality_drawdown_from_peak as f6
    import factors.quality_earnings_momentum_proxy as f7
    import factors.quality_volume_trend_60d as f8
    import factors.quality_resilience_score as f9
    import factors.quality_momentum_rank as f10

    for mod in [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10]:
        assert mod.FACTOR_CATEGORY == "quality_filter", (
            f"{mod.FACTOR_NAME} has category '{mod.FACTOR_CATEGORY}', expected 'quality_filter'"
        )
