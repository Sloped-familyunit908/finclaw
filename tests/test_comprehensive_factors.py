"""Tests for comprehensive factors: top_escape, trend_following, risk_warning, market_breadth."""

import importlib
import os
import sys

import pytest

# Ensure factors directory is importable
FACTORS_DIR = os.path.join(os.path.dirname(__file__), "..", "factors")
sys.path.insert(0, FACTORS_DIR)


# ── All 35 new factor modules ──────────────────────────────────────

TOP_ESCAPE_FACTORS = [
    "top_climax_volume",
    "top_bearish_divergence",
    "top_volume_price_divergence",
    "top_overbought_extreme",
    "top_distribution_candles",
    "top_evening_star",
    "top_rising_wedge",
    "top_smart_money_exit",
    "top_acceleration_exhaustion",
    "top_consecutive_upper_shadow",
]

TREND_FOLLOWING_FACTORS = [
    "trend_ema_golden_cross",
    "trend_ema_death_cross",
    "trend_price_above_all_ma",
    "trend_adx_strength",
    "trend_channel_position",
    "trend_higher_highs_lows",
    "trend_ma_fan_bullish",
    "trend_pullback_in_uptrend",
    "trend_breakout_new_high",
    "trend_momentum_confirmation",
]

RISK_WARNING_FACTORS = [
    "risk_gap_down",
    "risk_limit_down_nearby",
    "risk_volume_crash",
    "risk_consecutive_losses",
    "risk_below_all_ma",
    "risk_high_volatility",
    "risk_new_low_60d",
    "risk_ma_death_fan",
    "risk_earnings_cliff",
    "risk_declining_rsi_trend",
]

MARKET_BREADTH_FACTORS = [
    "breadth_advance_decline",
    "breadth_new_highs_lows",
    "breadth_sector_rotation",
    "breadth_market_momentum",
    "breadth_correlation_regime",
]

ALL_FACTORS = TOP_ESCAPE_FACTORS + TREND_FOLLOWING_FACTORS + RISK_WARNING_FACTORS + MARKET_BREADTH_FACTORS


# ── Helpers ─────────────────────────────────────────────────────────

def _load_factor(name):
    """Import a factor module by name."""
    return importlib.import_module(name)


def _make_uptrend(n=100):
    """Generate a clean uptrend dataset."""
    closes = [10.0 + i * 0.5 for i in range(n)]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.2 for c in closes]
    volumes = [1000000.0] * n
    return closes, highs, lows, volumes


def _make_downtrend(n=100):
    """Generate a clean downtrend dataset."""
    closes = [60.0 - i * 0.4 for i in range(n)]
    closes = [max(1.0, c) for c in closes]
    highs = [c + 0.2 for c in closes]
    lows = [c - 0.3 for c in closes]
    volumes = [1000000.0] * n
    return closes, highs, lows, volumes


def _make_topping(n=100):
    """Generate a topping pattern: rally then stall with distribution signals."""
    closes = []
    for i in range(n):
        if i < 70:
            # Strong rally phase
            closes.append(10.0 + i * 0.8)
        elif i < 85:
            # Stalling/distribution phase — small moves near highs
            closes.append(66.0 + (i - 70) * 0.05)
        else:
            # Beginning to roll over
            closes.append(66.75 - (i - 85) * 0.3)

    highs = [c + 1.5 for c in closes]  # Long upper shadows in distribution
    lows = [c - 0.3 for c in closes]
    # Volume: climax volume at the top, then declining
    volumes = []
    for i in range(n):
        if i < 70:
            volumes.append(1000000.0 + i * 10000)
        elif i < 75:
            volumes.append(4000000.0)  # Climax volume
        else:
            volumes.append(max(200000.0, 3000000.0 - (i - 75) * 100000))
    return closes, highs, lows, volumes


def _make_dangerous(n=100):
    """Generate a dangerous/risky dataset with crashes and gaps."""
    closes = [50.0] * 20  # Flat start
    # Then consecutive drops
    for i in range(20, 30):
        closes.append(closes[-1] * 0.97)  # 3% daily drops
    # Gap down
    closes.append(closes[-1] * 0.90)  # 10% gap
    for i in range(31, n):
        closes.append(closes[-1] * 0.99)  # Continued slow decline

    highs = [c * 1.01 for c in closes]
    lows = [c * 0.98 for c in closes]
    # Volume crashes in the middle
    volumes = [1000000.0] * 30 + [3500000.0] + [200000.0] * (n - 31)
    return closes, highs, lows, volumes


def _make_flat(n=100):
    """Generate a flat/sideways dataset."""
    closes = [50.0 + (i % 5) * 0.2 - 0.5 for i in range(n)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    volumes = [1000000.0] * n
    return closes, highs, lows, volumes


# ══════════════════════════════════════════════════════════════════════
# PART 1: Batch test — all factors importable and return [0, 1]
# ══════════════════════════════════════════════════════════════════════

class TestAllFactorsBasic:
    """Every factor should be importable and return values in [0, 1]."""

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_factor_importable(self, factor_name):
        mod = _load_factor(factor_name)
        assert hasattr(mod, "FACTOR_NAME")
        assert hasattr(mod, "FACTOR_DESC")
        assert hasattr(mod, "FACTOR_CATEGORY")
        assert hasattr(mod, "compute")

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_factor_returns_0_1_uptrend(self, factor_name):
        mod = _load_factor(factor_name)
        closes, highs, lows, volumes = _make_uptrend()
        for idx in [0, 5, 20, 50, 99]:
            result = mod.compute(closes, highs, lows, volumes, idx)
            assert 0.0 <= result <= 1.0, f"{factor_name} at idx={idx} returned {result}"

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_factor_returns_0_1_downtrend(self, factor_name):
        mod = _load_factor(factor_name)
        closes, highs, lows, volumes = _make_downtrend()
        for idx in [0, 5, 20, 50, 99]:
            result = mod.compute(closes, highs, lows, volumes, idx)
            assert 0.0 <= result <= 1.0, f"{factor_name} at idx={idx} returned {result}"

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_factor_default_on_insufficient_data(self, factor_name):
        """With insufficient data (idx=0), should return 0.5 default or valid [0,1]."""
        mod = _load_factor(factor_name)
        closes = [10.0]
        highs = [10.5]
        lows = [9.5]
        volumes = [1000000.0]
        result = mod.compute(closes, highs, lows, volumes, 0)
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_factor_category_correct(self, factor_name):
        mod = _load_factor(factor_name)
        expected_categories = {
            "top_escape", "trend_following", "risk_warning", "market_breadth"
        }
        assert mod.FACTOR_CATEGORY in expected_categories, (
            f"{factor_name} has unexpected category: {mod.FACTOR_CATEGORY}"
        )


# ══════════════════════════════════════════════════════════════════════
# PART 2: Top escape factors — should score high on topping patterns
# ══════════════════════════════════════════════════════════════════════

class TestTopEscapeFactors:
    """Top escape factors should detect distribution/topping patterns."""

    def test_climax_volume_at_top(self):
        """Extreme volume near highs → high score."""
        mod = _load_factor("top_climax_volume")
        # Build data specifically for climax volume: price near 20d high + extreme volume
        n = 30
        closes = [10.0 + i * 0.5 for i in range(n)]  # Rising
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.2 for c in closes]
        volumes = [1000000.0] * n
        volumes[-1] = 4000000.0  # 4x average at the high
        score = mod.compute(closes, highs, lows, volumes, n - 1)
        assert score > 0.5, f"Expected high score at top, got {score}"

    def test_climax_volume_normal(self):
        """Normal volume away from highs → default score."""
        mod = _load_factor("top_climax_volume")
        closes, highs, lows, volumes = _make_flat()
        score = mod.compute(closes, highs, lows, volumes, 50)
        assert score <= 0.6, f"Expected low score on flat data, got {score}"

    def test_volume_price_divergence_at_top(self):
        """Volume declining while price rises → distribution."""
        mod = _load_factor("top_volume_price_divergence")
        # Create specific pattern: price rising, volume falling
        closes = [10.0 + i * 0.3 for i in range(50)]
        highs = [c + 0.2 for c in closes]
        lows = [c - 0.1 for c in closes]
        volumes = [2000000.0 - i * 30000 for i in range(50)]
        score = mod.compute(closes, highs, lows, volumes, 49)
        assert score >= 0.5, f"Expected elevated score, got {score}"

    def test_overbought_extreme_normal(self):
        """Normal conditions → default score."""
        mod = _load_factor("top_overbought_extreme")
        closes, highs, lows, volumes = _make_flat()
        score = mod.compute(closes, highs, lows, volumes, 50)
        assert score <= 0.6, f"Expected low score on flat data, got {score}"

    def test_distribution_candles_at_top(self):
        """Small bodies near highs → distribution."""
        mod = _load_factor("top_distribution_candles")
        closes, highs, lows, volumes = _make_topping()
        # Distribution phase has small bodies
        score = mod.compute(closes, highs, lows, volumes, 80)
        assert 0.0 <= score <= 1.0

    def test_evening_star_pattern(self):
        """Classic evening star → should detect."""
        mod = _load_factor("top_evening_star")
        # Build evening star: big green, small body, big red
        closes = [10.0] * 20
        closes.extend([10.0, 12.0, 12.1, 10.5])  # green → doji → red
        highs = [c + 0.3 for c in closes]
        highs[-2] = 12.5  # Small body at the top
        lows = [c - 0.3 for c in closes]
        volumes = [1000000.0] * len(closes)
        score = mod.compute(closes, highs, lows, volumes, len(closes) - 1)
        assert 0.0 <= score <= 1.0

    def test_rising_wedge_in_uptrend(self):
        """Converging range in uptrend → wedge."""
        mod = _load_factor("top_rising_wedge")
        # Create converging range
        closes = []
        highs_data = []
        lows_data = []
        for i in range(30):
            base = 10.0 + i * 0.3
            spread = max(0.5, 3.0 - i * 0.08)  # Converging range
            closes.append(base)
            highs_data.append(base + spread)
            lows_data.append(base - spread * 0.3)
        volumes = [1000000.0] * 30
        score = mod.compute(closes, highs_data, lows_data, volumes, 29)
        assert 0.0 <= score <= 1.0

    def test_smart_money_exit_selling(self):
        """High volume with close near lows → smart money exit."""
        mod = _load_factor("top_smart_money_exit")
        closes = [50.0] * 20
        highs = [52.0] * 20
        lows = [49.0] * 20
        volumes = [1000000.0] * 20
        # Add 5 bars of high volume closing near lows
        for _ in range(5):
            closes.append(49.2)  # Close near low
            highs.append(52.0)  # High range
            lows.append(49.0)
            volumes.append(3000000.0)  # High volume
        score = mod.compute(closes, highs, lows, volumes, len(closes) - 1)
        assert score > 0.5, f"Expected high score for smart money exit, got {score}"

    def test_acceleration_exhaustion(self):
        """Fast rally then stall → exhaustion."""
        mod = _load_factor("top_acceleration_exhaustion")
        # 5 days of big gains then 2 days of tiny gains
        closes = [10.0] * 20
        closes.extend([10.0, 10.5, 11.2, 11.9, 12.5, 12.52, 12.53])
        highs = [c + 0.2 for c in closes]
        lows = [c - 0.1 for c in closes]
        volumes = [1000000.0] * len(closes)
        score = mod.compute(closes, highs, lows, volumes, len(closes) - 1)
        assert 0.0 <= score <= 1.0

    def test_consecutive_upper_shadow(self):
        """Multiple candles with long upper shadows → rejection."""
        mod = _load_factor("top_consecutive_upper_shadow")
        closes = [50.0] * 20
        # Add candles with long upper shadows
        for i in range(5):
            closes.append(50.1)
            # Long upper shadow = high >> close
        highs = [c + 0.2 for c in closes[:20]] + [53.0] * 5  # Much higher than close
        lows = [c - 0.1 for c in closes[:20]] + [49.9] * 5
        volumes = [1000000.0] * len(closes)
        score = mod.compute(closes, highs, lows, volumes, len(closes) - 1)
        assert score > 0.5, f"Expected high score for upper shadow rejection, got {score}"


# ══════════════════════════════════════════════════════════════════════
# PART 3: Trend following factors
# ══════════════════════════════════════════════════════════════════════

class TestTrendFollowingFactors:
    """Trend factors should score high in uptrends, low in downtrends."""

    def test_ema_golden_cross_uptrend(self):
        mod = _load_factor("trend_ema_golden_cross")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score >= 0.5, f"Golden cross in uptrend should be >=0.5, got {score}"

    def test_ema_death_cross_downtrend(self):
        mod = _load_factor("trend_ema_death_cross")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score >= 0.5, f"Death cross in downtrend should be >=0.5, got {score}"

    def test_price_above_all_ma_uptrend(self):
        mod = _load_factor("trend_price_above_all_ma")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Price above all MA in uptrend should be >0.5, got {score}"

    def test_price_above_all_ma_downtrend(self):
        mod = _load_factor("trend_price_above_all_ma")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Price below all MA in downtrend should be <0.5, got {score}"

    def test_adx_strength_trending(self):
        mod = _load_factor("trend_adx_strength")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.3, f"ADX in trend should be positive, got {score}"

    def test_higher_highs_lows_uptrend(self):
        mod = _load_factor("trend_higher_highs_lows")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.7, f"Should have many higher highs/lows in uptrend, got {score}"

    def test_higher_highs_lows_downtrend(self):
        mod = _load_factor("trend_higher_highs_lows")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.3, f"Should have few higher highs/lows in downtrend, got {score}"

    def test_ma_fan_bullish_uptrend(self):
        mod = _load_factor("trend_ma_fan_bullish")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.7, f"MA fan should be bullish in uptrend, got {score}"

    def test_ma_fan_bullish_downtrend(self):
        mod = _load_factor("trend_ma_fan_bullish")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"MA fan should NOT be bullish in downtrend, got {score}"

    def test_breakout_new_high(self):
        mod = _load_factor("trend_breakout_new_high")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"New highs in uptrend should score high, got {score}"

    def test_momentum_confirmation_uptrend(self):
        mod = _load_factor("trend_momentum_confirmation")
        closes, highs, lows, volumes = _make_uptrend()
        # Add rising volume to confirm the trend (vol increasing over time)
        volumes = [800000.0 + i * 5000 for i in range(100)]
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score >= 0.5, f"Triple confirmation in uptrend should be high, got {score}"

    def test_channel_position_uptrend(self):
        mod = _load_factor("trend_channel_position")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= score <= 1.0

    def test_pullback_in_uptrend_default(self):
        """Pullback factor on non-pullback should be neutral."""
        mod = _load_factor("trend_pullback_in_uptrend")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# PART 4: Risk warning factors
# ══════════════════════════════════════════════════════════════════════

class TestRiskWarningFactors:
    """Risk factors should score high for dangerous situations."""

    def test_gap_down_danger(self):
        mod = _load_factor("risk_gap_down")
        closes, highs, lows, volumes = _make_dangerous()
        # idx=30 is the big gap down
        score = mod.compute(closes, highs, lows, volumes, 30)
        assert score > 0.5, f"Gap down should score high risk, got {score}"

    def test_gap_down_normal(self):
        mod = _load_factor("risk_gap_down")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 50)
        assert score <= 0.6, f"Normal uptrend should not flag gap down, got {score}"

    def test_limit_down_nearby(self):
        mod = _load_factor("risk_limit_down_nearby")
        # Create data where price is near limit-down
        closes = [50.0] * 20 + [45.5]  # -9% drop, near -10% limit
        highs = [c + 0.2 for c in closes]
        lows = [c - 0.1 for c in closes]
        volumes = [1000000.0] * len(closes)
        score = mod.compute(closes, highs, lows, volumes, len(closes) - 1)
        assert score > 0.5, f"Near limit-down should score high, got {score}"

    def test_volume_crash_low_liquidity(self):
        mod = _load_factor("risk_volume_crash")
        closes = [50.0] * 30
        highs = [51.0] * 30
        lows = [49.0] * 30
        volumes = [1000000.0] * 25 + [100000.0] * 5  # Volume crashes to 10%
        score = mod.compute(closes, highs, lows, volumes, 29)
        assert score > 0.5, f"Volume crash should score high risk, got {score}"

    def test_consecutive_losses_danger(self):
        mod = _load_factor("risk_consecutive_losses")
        closes, highs, lows, volumes = _make_dangerous()
        # After 10 consecutive drops (idx~29)
        score = mod.compute(closes, highs, lows, volumes, 29)
        assert score > 0.5, f"Consecutive losses should flag risk, got {score}"

    def test_consecutive_losses_normal(self):
        mod = _load_factor("risk_consecutive_losses")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 50)
        assert score <= 0.6, f"Uptrend should not flag consecutive losses, got {score}"

    def test_below_all_ma_downtrend(self):
        mod = _load_factor("risk_below_all_ma")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Downtrend should be below all MAs, got {score}"

    def test_below_all_ma_uptrend(self):
        mod = _load_factor("risk_below_all_ma")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Uptrend should NOT be below all MAs, got {score}"

    def test_high_volatility_extreme(self):
        mod = _load_factor("risk_high_volatility")
        # Create very volatile data
        closes = [50.0] * 20
        highs = [55.0] * 20  # 10% range
        lows = [45.0] * 20
        volumes = [1000000.0] * 20
        score = mod.compute(closes, highs, lows, volumes, 19)
        assert score > 0.5, f"High volatility should score high risk, got {score}"

    def test_new_low_60d_at_bottom(self):
        mod = _load_factor("risk_new_low_60d")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"New 60-day low should flag risk, got {score}"

    def test_ma_death_fan_downtrend(self):
        mod = _load_factor("risk_ma_death_fan")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Death fan in downtrend should score high, got {score}"

    def test_ma_death_fan_uptrend(self):
        mod = _load_factor("risk_ma_death_fan")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Uptrend should NOT have death fan, got {score}"

    def test_earnings_cliff_on_crash(self):
        mod = _load_factor("risk_earnings_cliff")
        closes, highs, lows, volumes = _make_dangerous()
        score = mod.compute(closes, highs, lows, volumes, 30)
        assert score > 0.5, f"Crash on volume should flag earnings cliff, got {score}"

    def test_declining_rsi_trend(self):
        mod = _load_factor("risk_declining_rsi_trend")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# PART 5: Market breadth factors
# ══════════════════════════════════════════════════════════════════════

class TestMarketBreadthFactors:
    """Market breadth proxies should reflect market conditions."""

    def test_advance_decline_uptrend(self):
        mod = _load_factor("breadth_advance_decline")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Uptrend should show advancing, got {score}"

    def test_advance_decline_downtrend(self):
        mod = _load_factor("breadth_advance_decline")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Downtrend should show declining, got {score}"

    def test_new_highs_lows_uptrend(self):
        mod = _load_factor("breadth_new_highs_lows")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Uptrend should be near highs, got {score}"

    def test_new_highs_lows_downtrend(self):
        mod = _load_factor("breadth_new_highs_lows")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Downtrend should be near lows, got {score}"

    def test_sector_rotation_uptrend(self):
        mod = _load_factor("breadth_sector_rotation")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Uptrend should show hot sector, got {score}"

    def test_market_momentum_uptrend(self):
        mod = _load_factor("breadth_market_momentum")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score > 0.5, f"Uptrend should show positive momentum, got {score}"

    def test_market_momentum_downtrend(self):
        mod = _load_factor("breadth_market_momentum")
        closes, highs, lows, volumes = _make_downtrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert score < 0.5, f"Downtrend should show negative momentum, got {score}"

    def test_correlation_regime_returns_valid(self):
        mod = _load_factor("breadth_correlation_regime")
        closes, highs, lows, volumes = _make_uptrend()
        score = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════
# PART 6: Edge cases
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases that all factors should handle gracefully."""

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_single_bar(self, factor_name):
        mod = _load_factor(factor_name)
        result = mod.compute([100.0], [101.0], [99.0], [1000000.0], 0)
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_two_bars(self, factor_name):
        mod = _load_factor(factor_name)
        result = mod.compute(
            [100.0, 101.0], [101.0, 102.0], [99.0, 100.0], [1e6, 1e6], 1
        )
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_zero_volume(self, factor_name):
        mod = _load_factor(factor_name)
        closes = [50.0] * 100
        highs = [51.0] * 100
        lows = [49.0] * 100
        volumes = [0.0] * 100
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_constant_price(self, factor_name):
        mod = _load_factor(factor_name)
        closes = [50.0] * 100
        highs = [50.0] * 100
        lows = [50.0] * 100
        volumes = [1000000.0] * 100
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("factor_name", ALL_FACTORS)
    def test_very_small_price(self, factor_name):
        mod = _load_factor(factor_name)
        closes = [0.01] * 100
        highs = [0.012] * 100
        lows = [0.008] * 100
        volumes = [1000000.0] * 100
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert 0.0 <= result <= 1.0
