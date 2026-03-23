"""
Tests for crypto-specific factors.
Tests cover edge cases, boundary conditions, and expected behavior.
"""

import sys
import os
import math
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import all crypto factors
from factors.crypto.crypto_volume_spike import compute as volume_spike_compute
from factors.crypto.crypto_hourly_seasonality import compute as hourly_seasonality_compute
from factors.crypto.crypto_weekend_effect import compute as weekend_effect_compute
from factors.crypto.crypto_large_move_reversal import compute as large_move_reversal_compute
from factors.crypto.crypto_volatility_regime import compute as volatility_regime_compute
from factors.crypto.crypto_momentum_acceleration import compute as momentum_acceleration_compute
from factors.crypto.crypto_volume_profile_24h import compute as volume_profile_compute
from factors.crypto.crypto_range_breakout import compute as range_breakout_compute
from factors.crypto.crypto_mean_reversion_24h import compute as mean_reversion_compute
from factors.crypto.crypto_consecutive_candles import compute as consecutive_candles_compute


# ============================================================
# Test Helpers
# ============================================================

def make_data(n=200, base_price=100.0, trend=0.0, volatility=0.5):
    """Generate synthetic OHLCV data."""
    closes = []
    highs = []
    lows = []
    volumes = []
    price = base_price
    for i in range(n):
        price = price * (1 + trend) + (i % 7 - 3) * volatility
        price = max(price, 1.0)  # Prevent negative prices
        closes.append(price)
        highs.append(price + abs(volatility) * 2)
        lows.append(price - abs(volatility) * 2)
        volumes.append(1000000.0 + (i % 5) * 200000)
    return closes, highs, lows, volumes


def assert_valid_score(score):
    """Assert score is a valid factor output."""
    assert isinstance(score, (int, float)), f"Score must be numeric, got {type(score)}"
    assert not math.isnan(score), "Score must not be NaN"
    assert not math.isinf(score), "Score must not be infinite"
    assert 0.0 <= score <= 1.0, f"Score {score} out of range [0, 1]"


# ============================================================
# Test 1: Volume Spike — basic range
# ============================================================

def test_volume_spike_returns_valid_range():
    closes, highs, lows, volumes = make_data(100)
    score = volume_spike_compute(closes, highs, lows, volumes, 99)
    assert_valid_score(score)


# ============================================================
# Test 2: Volume Spike — insufficient data returns 0.5
# ============================================================

def test_volume_spike_insufficient_data():
    closes, highs, lows, volumes = make_data(30)
    score = volume_spike_compute(closes, highs, lows, volumes, 10)
    assert score == 0.5


# ============================================================
# Test 3: Volume Spike — high volume gives higher score
# ============================================================

def test_volume_spike_high_volume():
    closes, highs, lows, volumes = make_data(50)
    # Make current bar volume 10x average
    volumes[49] = sum(volumes[25:49]) / 24 * 10
    score = volume_spike_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.5, "High volume spike should give above-average score"


# ============================================================
# Test 4: Hourly Seasonality — returns valid for all hours
# ============================================================

def test_hourly_seasonality_all_hours():
    closes, highs, lows, volumes = make_data(200)
    for idx in range(24):
        score = hourly_seasonality_compute(closes, highs, lows, volumes, idx)
        assert_valid_score(score)


# ============================================================
# Test 5: Hourly Seasonality — US open hours are bullish
# ============================================================

def test_hourly_seasonality_us_open_bullish():
    closes, highs, lows, volumes = make_data(200)
    # idx % 24 == 14 (US market open)
    score_us_open = hourly_seasonality_compute(closes, highs, lows, volumes, 14)
    score_low_liq = hourly_seasonality_compute(closes, highs, lows, volumes, 7)
    assert score_us_open > score_low_liq, "US open should be more bullish than low-liquidity hours"


# ============================================================
# Test 6: Weekend Effect — valid output
# ============================================================

def test_weekend_effect_valid():
    closes, highs, lows, volumes = make_data(200)
    score = weekend_effect_compute(closes, highs, lows, volumes, 199)
    assert_valid_score(score)


# ============================================================
# Test 7: Weekend Effect — insufficient data returns 0.5
# ============================================================

def test_weekend_effect_insufficient():
    closes, highs, lows, volumes = make_data(200)
    score = weekend_effect_compute(closes, highs, lows, volumes, 50)
    assert score == 0.5


# ============================================================
# Test 8: Large Move Reversal — big drop should be bullish
# ============================================================

def test_large_move_reversal_big_drop():
    closes = [100.0] * 50
    # 10% drop over 4 bars
    closes[46] = 100.0
    closes[47] = 97.0
    closes[48] = 94.0
    closes[49] = 90.0
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    volumes = [1000000.0] * 50
    score = large_move_reversal_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.5, "Big drop should signal bullish reversal"


# ============================================================
# Test 9: Large Move Reversal — big rally should be bearish
# ============================================================

def test_large_move_reversal_big_rally():
    closes = [100.0] * 50
    closes[46] = 100.0
    closes[47] = 103.0
    closes[48] = 106.0
    closes[49] = 110.0
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    volumes = [1000000.0] * 50
    score = large_move_reversal_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score < 0.5, "Big rally should signal bearish reversal"


# ============================================================
# Test 10: Volatility Regime — valid output
# ============================================================

def test_volatility_regime_valid():
    closes, highs, lows, volumes = make_data(250)
    score = volatility_regime_compute(closes, highs, lows, volumes, 249)
    assert_valid_score(score)


# ============================================================
# Test 11: Momentum Acceleration — accelerating up is bullish
# ============================================================

def test_momentum_acceleration_uptrend():
    # Accelerating uptrend: each period's momentum is larger
    closes = [100.0] * 50
    for i in range(25, 50):
        closes[i] = closes[i - 1] * (1 + 0.001 * (i - 24))  # Accelerating
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    volumes = [1000000.0] * 50
    score = momentum_acceleration_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.5, "Accelerating uptrend should be bullish"


# ============================================================
# Test 12: Volume Profile — accumulation pattern
# ============================================================

def test_volume_profile_accumulation():
    closes, highs, lows, volumes = make_data(50)
    # Make closes near highs (bullish close pattern)
    for i in range(26, 50):
        lows[i] = closes[i] - 2
        highs[i] = closes[i] + 0.1  # Close near high
    score = volume_profile_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.5, "Close near high pattern should show accumulation"


# ============================================================
# Test 13: Range Breakout — above range is bullish
# ============================================================

def test_range_breakout_above():
    closes = [100.0] * 100
    highs = [101.0] * 100
    lows = [99.0] * 100
    # Price breaks above range
    closes[99] = 105.0
    highs[99] = 106.0
    lows[99] = 103.0
    score = range_breakout_compute(closes, highs, lows, [1e6] * 100, 99)
    assert_valid_score(score)
    assert score > 0.7, "Breakout above 48h range should be very bullish"


# ============================================================
# Test 14: Range Breakout — below range is bearish
# ============================================================

def test_range_breakout_below():
    closes = [100.0] * 100
    highs = [101.0] * 100
    lows = [99.0] * 100
    # Price breaks below range
    closes[99] = 95.0
    highs[99] = 97.0
    lows[99] = 94.0
    score = range_breakout_compute(closes, highs, lows, [1e6] * 100, 99)
    assert_valid_score(score)
    assert score < 0.3, "Breakdown below 48h range should be very bearish"


# ============================================================
# Test 15: Mean Reversion — far below VWAP is bullish
# ============================================================

def test_mean_reversion_below_vwap():
    closes = [100.0] * 50
    highs = [101.0] * 50
    lows = [99.0] * 50
    volumes = [1000000.0] * 50
    # Current price drops well below VWAP
    closes[49] = 96.0
    lows[49] = 95.0
    score = mean_reversion_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.5, "Price below VWAP should be bullish (mean reversion)"


# ============================================================
# Test 16: Mean Reversion — far above VWAP is bearish
# ============================================================

def test_mean_reversion_above_vwap():
    closes = [100.0] * 50
    highs = [101.0] * 50
    lows = [99.0] * 50
    volumes = [1000000.0] * 50
    # Current price spikes above VWAP
    closes[49] = 104.0
    highs[49] = 105.0
    score = mean_reversion_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score < 0.5, "Price above VWAP should be bearish (mean reversion)"


# ============================================================
# Test 17: Consecutive Candles — many green → overbought
# ============================================================

def test_consecutive_candles_many_green():
    closes = [100.0] * 50
    # 7 consecutive green candles
    for i in range(43, 50):
        closes[i] = closes[i - 1] + 1.0
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    volumes = [1e6] * 50
    score = consecutive_candles_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score < 0.3, "7+ consecutive green candles should signal overbought"


# ============================================================
# Test 18: Consecutive Candles — many red → oversold
# ============================================================

def test_consecutive_candles_many_red():
    closes = [100.0] * 50
    # 7 consecutive red candles
    for i in range(43, 50):
        closes[i] = closes[i - 1] - 1.0
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    volumes = [1e6] * 50
    score = consecutive_candles_compute(closes, highs, lows, volumes, 49)
    assert_valid_score(score)
    assert score > 0.7, "7+ consecutive red candles should signal oversold"


# ============================================================
# Test 19: All factors handle edge case idx=0
# ============================================================

def test_all_factors_edge_case_idx_zero():
    closes = [100.0]
    highs = [101.0]
    lows = [99.0]
    volumes = [1e6]
    
    funcs = [
        volume_spike_compute,
        hourly_seasonality_compute,
        weekend_effect_compute,
        large_move_reversal_compute,
        volatility_regime_compute,
        momentum_acceleration_compute,
        volume_profile_compute,
        range_breakout_compute,
        mean_reversion_compute,
        consecutive_candles_compute,
    ]
    for fn in funcs:
        score = fn(closes, highs, lows, volumes, 0)
        assert_valid_score(score)


# ============================================================
# Test 20: All factors handle zero volume
# ============================================================

def test_all_factors_zero_volume():
    closes = [100.0] * 200
    highs = [101.0] * 200
    lows = [99.0] * 200
    volumes = [0.0] * 200
    
    funcs = [
        volume_spike_compute,
        hourly_seasonality_compute,
        weekend_effect_compute,
        large_move_reversal_compute,
        volatility_regime_compute,
        momentum_acceleration_compute,
        volume_profile_compute,
        range_breakout_compute,
        mean_reversion_compute,
        consecutive_candles_compute,
    ]
    for fn in funcs:
        score = fn(closes, highs, lows, volumes, 199)
        assert_valid_score(score)


# ============================================================
# Test 21: Factor registry discovers crypto factors
# ============================================================

def test_factor_registry_loads_crypto():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from evolution.factor_discovery import FactorRegistry
    
    registry = FactorRegistry(
        factors_dir=os.path.join(os.path.dirname(__file__), "..", "factors")
    )
    loaded = registry.load_all()
    
    factor_names = registry.list_factors()
    crypto_factors = [f for f in factor_names if f.startswith("crypto_")]
    assert len(crypto_factors) >= 10, f"Expected at least 10 crypto factors, got {len(crypto_factors)}: {crypto_factors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
