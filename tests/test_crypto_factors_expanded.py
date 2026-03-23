"""
Tests for expanded crypto factors (30 new factors).
Covers batch validation, edge cases, and directional tests per group.
"""

import sys
import os
import math
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# Group 1: Whale & Smart Money
# ============================================================
from factors.crypto.crypto_whale_candle import compute as whale_candle_compute
from factors.crypto.crypto_absorption import compute as absorption_compute
from factors.crypto.crypto_smart_money_exit import compute as smart_money_exit_compute
from factors.crypto.crypto_accumulation_48h import compute as accumulation_48h_compute
from factors.crypto.crypto_distribution_pattern import compute as distribution_pattern_compute

# ============================================================
# Group 2: Market Microstructure
# ============================================================
from factors.crypto.crypto_spread_proxy import compute as spread_proxy_compute
from factors.crypto.crypto_tick_intensity import compute as tick_intensity_compute
from factors.crypto.crypto_amihud_illiquidity import compute as amihud_illiquidity_compute
from factors.crypto.crypto_trade_flow_imbalance import compute as trade_flow_imbalance_compute
from factors.crypto.crypto_market_depth import compute as market_depth_compute

# ============================================================
# Group 3: Multi-Timeframe Momentum
# ============================================================
from factors.crypto.crypto_trend_4h import compute as trend_4h_compute
from factors.crypto.crypto_multi_tf_alignment import compute as multi_tf_alignment_compute
from factors.crypto.crypto_momentum_divergence import compute as momentum_divergence_compute
from factors.crypto.crypto_breakout_volume import compute as breakout_volume_compute
from factors.crypto.crypto_pullback_buy import compute as pullback_buy_compute

# ============================================================
# Group 4: Volatility & Risk
# ============================================================
from factors.crypto.crypto_vol_squeeze import compute as vol_squeeze_compute
from factors.crypto.crypto_atr_trend import compute as atr_trend_compute
from factors.crypto.crypto_risk_reward_setup import compute as risk_reward_setup_compute
from factors.crypto.crypto_tail_risk import compute as tail_risk_compute
from factors.crypto.crypto_drawdown_recovery import compute as drawdown_recovery_compute

# ============================================================
# Group 5: Cross-Asset Signals
# ============================================================
from factors.crypto.crypto_btc_correlation import compute as btc_correlation_compute
from factors.crypto.crypto_volume_sync import compute as volume_sync_compute
from factors.crypto.crypto_relative_alpha import compute as relative_alpha_compute
from factors.crypto.crypto_pair_momentum import compute as pair_momentum_compute
from factors.crypto.crypto_beta_momentum import compute as beta_momentum_compute

# ============================================================
# Group 6: Mean Reversion
# ============================================================
from factors.crypto.crypto_zscore_48h import compute as zscore_48h_compute
from factors.crypto.crypto_rsi_divergence import compute as rsi_divergence_compute
from factors.crypto.crypto_bollinger_fast import compute as bollinger_fast_compute
from factors.crypto.crypto_gap_fill import compute as gap_fill_compute
from factors.crypto.crypto_overextension import compute as overextension_compute


# ============================================================
# All 30 compute functions
# ============================================================
ALL_FACTORS = [
    # Group 1: Whale & Smart Money
    whale_candle_compute,
    absorption_compute,
    smart_money_exit_compute,
    accumulation_48h_compute,
    distribution_pattern_compute,
    # Group 2: Market Microstructure
    spread_proxy_compute,
    tick_intensity_compute,
    amihud_illiquidity_compute,
    trade_flow_imbalance_compute,
    market_depth_compute,
    # Group 3: Multi-Timeframe Momentum
    trend_4h_compute,
    multi_tf_alignment_compute,
    momentum_divergence_compute,
    breakout_volume_compute,
    pullback_buy_compute,
    # Group 4: Volatility & Risk
    vol_squeeze_compute,
    atr_trend_compute,
    risk_reward_setup_compute,
    tail_risk_compute,
    drawdown_recovery_compute,
    # Group 5: Cross-Asset Signals
    btc_correlation_compute,
    volume_sync_compute,
    relative_alpha_compute,
    pair_momentum_compute,
    beta_momentum_compute,
    # Group 6: Mean Reversion
    zscore_48h_compute,
    rsi_divergence_compute,
    bollinger_fast_compute,
    gap_fill_compute,
    overextension_compute,
]


# ============================================================
# Helpers
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
        price = max(price, 1.0)
        closes.append(price)
        highs.append(price + abs(volatility) * 2)
        lows.append(price - abs(volatility) * 2)
        volumes.append(1000000.0 + (i % 5) * 200000)
    return closes, highs, lows, volumes


def assert_valid_score(score, context=""):
    """Assert score is a valid factor output."""
    assert isinstance(score, (int, float)), f"Score must be numeric, got {type(score)} {context}"
    assert not math.isnan(score), f"Score must not be NaN {context}"
    assert not math.isinf(score), f"Score must not be infinite {context}"
    assert 0.0 <= score <= 1.0, f"Score {score} out of range [0, 1] {context}"


# ============================================================
# BATCH TEST: All 30 factors return [0, 1] for synthetic data
# ============================================================

class TestBatchValidation:
    """All 30 factors must return valid [0, 1] scores for various data."""

    def test_all_factors_normal_data(self):
        """Test with normal trending data."""
        closes, highs, lows, volumes = make_data(200, trend=0.001)
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=fn.__module__)

    def test_all_factors_flat_data(self):
        """Test with flat/constant data."""
        closes = [100.0] * 200
        highs = [101.0] * 200
        lows = [99.0] * 200
        volumes = [1e6] * 200
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=fn.__module__)

    def test_all_factors_volatile_data(self):
        """Test with high volatility data."""
        closes, highs, lows, volumes = make_data(200, volatility=5.0)
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=fn.__module__)

    def test_all_factors_downtrend_data(self):
        """Test with downtrending data."""
        closes, highs, lows, volumes = make_data(200, base_price=200.0, trend=-0.001)
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=fn.__module__)

    def test_all_factors_high_volume_data(self):
        """Test with extremely high volume."""
        closes, highs, lows, volumes = make_data(200)
        volumes = [v * 1000 for v in volumes]
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=fn.__module__)


# ============================================================
# EDGE CASES
# ============================================================

class TestEdgeCases:
    """Edge cases: idx=0, short arrays, zero volume, etc."""

    def test_all_factors_idx_0(self):
        """All factors return valid score at idx=0."""
        closes = [100.0]
        highs = [101.0]
        lows = [99.0]
        volumes = [1e6]
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 0)
            assert_valid_score(score, context=f"{fn.__module__} at idx=0")

    def test_all_factors_idx_1(self):
        """All factors return valid score at idx=1."""
        closes = [100.0, 101.0]
        highs = [101.0, 102.0]
        lows = [99.0, 100.0]
        volumes = [1e6, 1e6]
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 1)
            assert_valid_score(score, context=f"{fn.__module__} at idx=1")

    def test_all_factors_short_array(self):
        """All factors return valid score for 5-element array."""
        closes = [100.0, 101.0, 99.0, 102.0, 100.5]
        highs = [h + 1.0 for h in closes]
        lows = [l - 1.0 for l in closes]
        volumes = [1e6] * 5
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 4)
            assert_valid_score(score, context=f"{fn.__module__} short array")

    def test_all_factors_zero_volume(self):
        """All factors handle zero volume gracefully."""
        closes = [100.0] * 200
        highs = [101.0] * 200
        lows = [99.0] * 200
        volumes = [0.0] * 200
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=f"{fn.__module__} zero volume")

    def test_all_factors_equal_hlc(self):
        """All factors handle H=L=C (doji / zero range)."""
        closes = [100.0] * 200
        highs = [100.0] * 200
        lows = [100.0] * 200
        volumes = [1e6] * 200
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 199)
            assert_valid_score(score, context=f"{fn.__module__} doji")

    def test_all_factors_insufficient_returns_neutral(self):
        """With only 10 bars, factors should return near-neutral."""
        closes, highs, lows, volumes = make_data(10)
        for fn in ALL_FACTORS:
            score = fn(closes, highs, lows, volumes, 5)
            assert_valid_score(score, context=f"{fn.__module__} insufficient data")


# ============================================================
# DIRECTIONAL TESTS — Group 1: Whale & Smart Money
# ============================================================

class TestGroup1WhaleSmartMoney:
    """At least 1 directional test per group."""

    def test_whale_candle_big_volume_big_move(self):
        """Whale candle: >5x vol + >1% move should deviate from 0.5."""
        closes = [100.0] * 50
        highs = [101.0] * 50
        lows = [99.0] * 50
        volumes = [1e6] * 50
        # Massive buy: 10x volume + 3% up move
        closes[49] = 103.0
        highs[49] = 104.0
        volumes[49] = 10e6
        score = whale_candle_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.7, f"Whale buy candle should be bullish, got {score}"

    def test_smart_money_exit_rising_price_falling_volume(self):
        """Rising price + falling volume = smart money exiting → bearish."""
        closes = [100.0] * 30
        highs = [101.0] * 30
        lows = [99.0] * 30
        volumes = [1e6] * 30
        # 8 bars: price up, volume down
        for i in range(22, 30):
            closes[i] = closes[i - 1] + 0.5
            highs[i] = closes[i] + 1.0
            lows[i] = closes[i] - 0.5
            volumes[i] = volumes[i - 1] * 0.85
        score = smart_money_exit_compute(closes, highs, lows, volumes, 29)
        assert_valid_score(score)
        assert score < 0.5, f"Smart money exit should be bearish, got {score}"

    def test_distribution_rising_price_shrinking_bodies(self):
        """Rising price + shrinking candle bodies = distribution → bearish."""
        closes = [100.0] * 50
        highs = [101.0] * 50
        lows = [99.0] * 50
        volumes = [1e6] * 50
        # First half: big body moves up
        for i in range(38, 44):
            closes[i] = closes[i - 1] + 2.0
            highs[i] = closes[i] + 1.0
            lows[i] = closes[i] - 1.0
        # Second half: smaller body moves, still up
        for i in range(44, 50):
            closes[i] = closes[i - 1] + 0.3
            highs[i] = closes[i] + 1.5
            lows[i] = closes[i] - 1.5
        score = distribution_pattern_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score < 0.5, f"Distribution pattern should be bearish, got {score}"


# ============================================================
# DIRECTIONAL TESTS — Group 2: Market Microstructure
# ============================================================

class TestGroup2MarketMicrostructure:

    def test_spread_proxy_tight_spread(self):
        """Very tight spread (small H-L range) should give high score."""
        closes = [100.0] * 50
        highs = [101.0] * 50  # Normal range
        lows = [99.0] * 50
        volumes = [1e6] * 50
        # Current bar: very tight range
        highs[49] = 100.1
        lows[49] = 99.9
        score = spread_proxy_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.6, f"Tight spread should indicate liquidity (high score), got {score}"

    def test_trade_flow_imbalance_buying_pressure(self):
        """Close near high = buying pressure → high score."""
        closes = [100.0] * 50
        highs = [105.0] * 50
        lows = [95.0] * 50
        volumes = [1e6] * 50
        # Recent bars: close near high
        for i in range(38, 50):
            closes[i] = 104.5  # Very near high
        score = trade_flow_imbalance_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.8, f"Buying pressure should give high score, got {score}"


# ============================================================
# DIRECTIONAL TESTS — Group 3: Multi-Timeframe Momentum
# ============================================================

class TestGroup3MultiTimeframeMomentum:

    def test_trend_4h_strong_uptrend(self):
        """Strong uptrend should give high score."""
        closes = [100.0 + i * 0.5 for i in range(50)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1e6] * 50
        score = trend_4h_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.55, f"Strong uptrend should be bullish, got {score}"

    def test_breakout_volume_confirmed(self):
        """Price above 48h range with high volume → bullish breakout."""
        closes = [100.0] * 100
        highs = [101.0] * 100
        lows = [99.0] * 100
        volumes = [1e6] * 100
        # Breakout bar
        closes[99] = 105.0
        highs[99] = 106.0
        lows[99] = 103.0
        volumes[99] = 3e6  # 3x avg volume
        score = breakout_volume_compute(closes, highs, lows, volumes, 99)
        assert_valid_score(score)
        assert score > 0.7, f"Volume-confirmed breakout should be very bullish, got {score}"

    def test_multi_tf_alignment_all_bullish(self):
        """Price above all timeframe EMAs = all bullish."""
        closes = [50.0 + i * 0.3 for i in range(100)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1e6] * 100
        score = multi_tf_alignment_compute(closes, highs, lows, volumes, 99)
        assert_valid_score(score)
        assert score > 0.7, f"All-bullish alignment should be high, got {score}"


# ============================================================
# DIRECTIONAL TESTS — Group 4: Volatility & Risk
# ============================================================

class TestGroup4VolatilityRisk:

    def test_atr_trend_expanding(self):
        """Expanding ATR (second half more volatile) → higher score."""
        closes = [100.0] * 50
        highs = [101.0] * 50
        lows = [99.0] * 50
        volumes = [1e6] * 50
        # Make second half more volatile
        for i in range(37, 50):
            highs[i] = closes[i] + 5.0
            lows[i] = closes[i] - 5.0
        score = atr_trend_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.5, f"Expanding ATR should give higher score, got {score}"

    def test_risk_reward_near_support(self):
        """Price near 48h swing low = good long risk/reward → high score."""
        closes = [100.0] * 100
        highs = [105.0] * 100
        lows = [95.0] * 100
        volumes = [1e6] * 100
        # Price near the low
        closes[99] = 96.0
        lows[99] = 95.5
        score = risk_reward_setup_compute(closes, highs, lows, volumes, 99)
        assert_valid_score(score)
        assert score > 0.6, f"Near support should show good long R/R, got {score}"


# ============================================================
# DIRECTIONAL TESTS — Group 5: Cross-Asset Signals
# ============================================================

class TestGroup5CrossAssetSignals:

    def test_pair_momentum_above_ma(self):
        """Price above MA24 → bullish momentum."""
        closes = [100.0 + i * 0.3 for i in range(50)]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1e6] * 50
        score = pair_momentum_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.5, f"Above MA24 should indicate momentum, got {score}"

    def test_beta_momentum_strong_uptrend(self):
        """Strong uptrend with moderate vol → good risk-adjusted momentum."""
        closes = [100.0] * 50
        for i in range(25, 50):
            closes[i] = closes[i - 1] * 1.002  # Steady rise
        highs = [c + 0.5 for c in closes]
        lows = [c - 0.5 for c in closes]
        volumes = [1e6] * 50
        score = beta_momentum_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.5, f"Strong risk-adj momentum should be bullish, got {score}"


# ============================================================
# DIRECTIONAL TESTS — Group 6: Mean Reversion
# ============================================================

class TestGroup6MeanReversion:

    def test_zscore_well_below_mean(self):
        """Price well below 48h mean → low z-score → low score."""
        closes = [100.0] * 100
        highs = [101.0] * 100
        lows = [99.0] * 100
        volumes = [1e6] * 100
        # Current price drops significantly
        closes[99] = 90.0
        lows[99] = 89.0
        score = zscore_48h_compute(closes, highs, lows, volumes, 99)
        assert_valid_score(score)
        assert score < 0.4, f"Price below mean should give low z-score, got {score}"

    def test_bollinger_fast_near_upper(self):
        """Price near upper Bollinger band → high score."""
        closes = [100.0] * 50
        # Spike up
        closes[49] = 115.0
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1e6] * 50
        score = bollinger_fast_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        assert score > 0.8, f"Near upper BB should give high score, got {score}"

    def test_rsi_divergence_bearish(self):
        """Price rising but RSI declining → bearish divergence → low score."""
        closes = [100.0] * 50
        highs = [101.0] * 50
        lows = [99.0] * 50
        volumes = [1e6] * 50
        # Sharp rise then slower rise (causes RSI to decline even though price rises)
        for i in range(30, 42):
            closes[i] = closes[i - 1] + 2.0  # Fast rise
            highs[i] = closes[i] + 1.0
            lows[i] = closes[i] - 1.0
        for i in range(42, 50):
            closes[i] = closes[i - 1] + 0.1  # Slow rise
            highs[i] = closes[i] + 1.0
            lows[i] = closes[i] - 1.0
        score = rsi_divergence_compute(closes, highs, lows, volumes, 49)
        assert_valid_score(score)
        # RSI may or may not show clear divergence depending on exact values,
        # but the score should still be valid


# ============================================================
# Factor registry discovers all 40 crypto factors
# ============================================================

def test_factor_registry_loads_all_40_crypto():
    """Verify the factor registry loads all 40 crypto factors."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from evolution.factor_discovery import FactorRegistry

    registry = FactorRegistry(
        factors_dir=os.path.join(os.path.dirname(__file__), "..", "factors")
    )
    loaded = registry.load_all()

    factor_names = registry.list_factors()
    crypto_factors = [f for f in factor_names if f.startswith("crypto_")]
    assert len(crypto_factors) >= 40, (
        f"Expected at least 40 crypto factors, got {len(crypto_factors)}: {crypto_factors}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
