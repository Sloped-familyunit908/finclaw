"""
Tests for Pullback Strategy Factors + min_score Range Validation
================================================================
At least 10 tests covering:
- Uptrend + dip → high score (THE KEY test)
- Downtrend + dip → low score (THE KEY inverse test)
- Flat market + dip → medium score
- MA20 bounce detection
- Volume dry-up during pullback
- Healthy retracement scoring
- RSI divergence in uptrend
- Min score range validation (PARAM_RANGES clamped to 4-8)
"""

import math
import pytest

# ── Import the 5 pullback factors ──
from factors.pullback_uptrend_dip import compute as compute_uptrend_dip
from factors.pullback_ma20_bounce import compute as compute_ma20_bounce
from factors.pullback_healthy_retracement import compute as compute_healthy_retracement
from factors.pullback_rsi_divergence_in_uptrend import compute as compute_rsi_divergence
from factors.pullback_volume_dry_up import compute as compute_volume_dry_up


# ═══════════════════════════════════════════════════════════════
# Helpers: generate synthetic price data
# ═══════════════════════════════════════════════════════════════

def make_uptrend_with_dip(n=80, dip_bars=5, dip_pct=0.05):
    """
    Create an uptrend stock that dips in the last few bars.
    - First n-dip_bars bars: steady uptrend from 10 → ~15
    - Last dip_bars bars: price drops by dip_pct from peak
    """
    base = 10.0
    trend_len = n - dip_bars
    closes = []
    highs = []
    lows = []
    volumes = []

    # Uptrend phase
    for i in range(trend_len):
        price = base + (5.0 * i / max(trend_len - 1, 1))
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000 + i * 10000)  # rising volume in uptrend

    peak = closes[-1]

    # Dip phase: price drops, volume decreases (healthy pullback)
    for i in range(dip_bars):
        drop = peak * dip_pct * (i + 1) / dip_bars
        price = peak - drop
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        # Volume declining during pullback
        volumes.append(max(100000, 1000000 - (i + 1) * 200000))

    return closes, highs, lows, volumes


def make_downtrend_with_dip(n=80):
    """
    Create a downtrend stock — price steadily declining.
    RSI should be low, MA60 slope negative, price below MA60.
    """
    base = 20.0
    closes = []
    highs = []
    lows = []
    volumes = []

    for i in range(n):
        price = base - (10.0 * i / max(n - 1, 1))  # 20 → 10
        price = max(price, 1.0)
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000 + i * 5000)

    return closes, highs, lows, volumes


def make_flat_data(n=80, base_price=10.0):
    """Flat/sideways data with small random-ish oscillation."""
    closes = []
    highs = []
    lows = []
    volumes = []

    for i in range(n):
        # Tiny oscillation around base
        offset = 0.1 * (1 if i % 2 == 0 else -1)
        price = base_price + offset
        closes.append(price)
        highs.append(price + 0.05)
        lows.append(price - 0.05)
        volumes.append(1000000)

    return closes, highs, lows, volumes


def make_uptrend_touching_ma20(n=80):
    """
    Uptrend where price recently pulled back to touch MA20.
    - First 60 bars: strong uptrend
    - Next 15 bars: moderate uptrend (so MA20 is rising)
    - Last 5 bars: price pulls back to MA20 level
    """
    closes = []
    highs = []
    lows = []
    volumes = []

    for i in range(60):
        price = 10.0 + (5.0 * i / 59)
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    # Continue uptrend but slower
    for i in range(15):
        price = 15.0 + (1.0 * i / 14)
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    # Now pull back toward MA20
    peak = closes[-1]
    # MA20 at this point is roughly the average of the last 20 closes
    # which is around 14.5-15.5
    ma20_approx = sum(closes[-20:]) / 20

    for i in range(5):
        frac = (i + 1) / 5
        price = peak - (peak - ma20_approx) * frac
        closes.append(price)
        highs.append(price + 0.1)
        # Low touches slightly below MA20
        lows.append(price - 0.15)
        volumes.append(800000 - i * 100000)

    return closes, highs, lows, volumes


def make_rally_then_pullback(n=80, rally_pct=0.20, pullback_pct=0.05):
    """
    Stock rallies 20% over 20 bars, then pulls back 5% on declining volume.
    """
    closes = []
    highs = []
    lows = []
    volumes = []

    # Flat base
    for i in range(50):
        price = 10.0
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    # Rally phase: 20 bars
    base_price = 10.0
    for i in range(20):
        price = base_price * (1 + rally_pct * (i + 1) / 20)
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1500000)  # above average volume during rally

    peak = closes[-1]

    # Pullback phase: 10 bars
    for i in range(10):
        drop = peak * pullback_pct * (i + 1) / 10
        price = peak - drop
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        # Volume declining during pullback
        volumes.append(max(200000, 1200000 - (i + 1) * 100000))

    return closes, highs, lows, volumes


def make_uptrend_oversold_macd_positive(n=80):
    """
    Uptrend stock with RSI dipped to 30-40 range but MACD still positive.
    Price above MA60, recent sharp dip that pushed RSI down.
    """
    closes = []
    highs = []
    lows = []
    volumes = []

    # Strong uptrend for 70 bars
    for i in range(70):
        price = 10.0 + (8.0 * i / 69)  # 10 → 18
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    # Sharp but brief dip for 10 bars (pushes RSI to ~35)
    peak = closes[-1]
    for i in range(10):
        price = peak * (1 - 0.008 * (i + 1))  # ~8% total drop
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(700000)

    return closes, highs, lows, volumes


def make_pullback_with_declining_volume(n=80):
    """
    Price dipping with volume declining bar-over-bar.
    """
    closes = []
    highs = []
    lows = []
    volumes = []

    # Normal phase
    for i in range(70):
        price = 10.0 + (3.0 * i / 69)  # slight uptrend
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    # Pullback with declining volume
    peak = closes[-1]
    for i in range(10):
        price = peak * (1 - 0.003 * (i + 1))  # 3% pullback
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        # Steadily declining volume
        volumes.append(max(100000, 900000 - i * 150000))

    return closes, highs, lows, volumes


def make_pullback_with_high_volume(n=80):
    """
    Price dipping but volume INCREASING — panic selling, not healthy.
    """
    closes = []
    highs = []
    lows = []
    volumes = []

    for i in range(70):
        price = 10.0 + (3.0 * i / 69)
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        volumes.append(1000000)

    peak = closes[-1]
    for i in range(10):
        price = peak * (1 - 0.003 * (i + 1))
        closes.append(price)
        highs.append(price * 1.01)
        lows.append(price * 0.99)
        # Volume INCREASING during pullback — panic
        volumes.append(1000000 + (i + 1) * 200000)

    return closes, highs, lows, volumes


# ═══════════════════════════════════════════════════════════════
# Test 1: Uptrend + dip → high score (THE KEY TEST)
# ═══════════════════════════════════════════════════════════════

class TestPullbackUptrendDip:
    def test_uptrend_dip_high_score(self):
        """Stock in clear uptrend with short-term dip should score HIGH."""
        closes, highs, lows, volumes = make_uptrend_with_dip(
            n=80, dip_bars=5, dip_pct=0.05
        )
        idx = len(closes) - 1
        score = compute_uptrend_dip(closes, highs, lows, volumes, idx)
        # Should be well above 0.5 — this is the ideal buy-the-dip
        assert score > 0.5, f"Uptrend dip should score > 0.5, got {score}"

    def test_downtrend_dip_low_score(self):
        """Stock in DOWNTREND should score LOW even if RSI is low.
        THIS IS THE KEY TEST — prevents buying falling knives."""
        closes, highs, lows, volumes = make_downtrend_with_dip(n=80)
        idx = len(closes) - 1
        score = compute_uptrend_dip(closes, highs, lows, volumes, idx)
        # MA60 slope is negative → should return 0.0
        assert score <= 0.2, (
            f"Downtrend stock should score ≤ 0.2, got {score}. "
            f"This factor must NOT buy falling knives!"
        )

    def test_flat_market_neutral(self):
        """Flat/sideways market should give neutral score."""
        closes, highs, lows, volumes = make_flat_data(n=80)
        idx = len(closes) - 1
        score = compute_uptrend_dip(closes, highs, lows, volumes, idx)
        assert 0.0 <= score <= 0.6, f"Flat market should be neutral, got {score}"

    def test_insufficient_data_returns_neutral(self):
        """With too few bars, should return 0.5."""
        closes = [10.0] * 30
        highs = [10.1] * 30
        lows = [9.9] * 30
        volumes = [1000000] * 30
        score = compute_uptrend_dip(closes, highs, lows, volumes, 20)
        assert score == 0.5, f"Insufficient data should return 0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 2: MA20 Bounce Detection
# ═══════════════════════════════════════════════════════════════

class TestPullbackMA20Bounce:
    def test_ma20_bounce_in_uptrend(self):
        """Price touching rising MA20 in uptrend should score well."""
        closes, highs, lows, volumes = make_uptrend_touching_ma20(n=80)
        idx = len(closes) - 1
        score = compute_ma20_bounce(closes, highs, lows, volumes, idx)
        assert score > 0.5, f"MA20 bounce in uptrend should score > 0.5, got {score}"

    def test_ma20_bounce_in_downtrend(self):
        """In a downtrend, MA20 is falling — should score low."""
        closes, highs, lows, volumes = make_downtrend_with_dip(n=80)
        idx = len(closes) - 1
        score = compute_ma20_bounce(closes, highs, lows, volumes, idx)
        assert score <= 0.5, f"Downtrend MA20 bounce should score ≤ 0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 3: Healthy Retracement
# ═══════════════════════════════════════════════════════════════

class TestPullbackHealthyRetracement:
    def test_healthy_pullback_after_rally(self):
        """After 20% rally, a 5% pullback on declining volume → high score."""
        closes, highs, lows, volumes = make_rally_then_pullback(
            n=80, rally_pct=0.20, pullback_pct=0.05
        )
        idx = len(closes) - 1
        score = compute_healthy_retracement(closes, highs, lows, volumes, idx)
        assert score > 0.5, f"Healthy retracement should score > 0.5, got {score}"

    def test_deep_pullback_low_score(self):
        """A 15%+ pullback after rally → likely breakdown, low score."""
        closes, highs, lows, volumes = make_rally_then_pullback(
            n=80, rally_pct=0.20, pullback_pct=0.15
        )
        idx = len(closes) - 1
        score = compute_healthy_retracement(closes, highs, lows, volumes, idx)
        assert score < 0.5, f"Deep pullback should score < 0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 4: RSI Divergence in Uptrend
# ═══════════════════════════════════════════════════════════════

class TestPullbackRSIDivergence:
    def test_oversold_rsi_in_uptrend(self):
        """RSI in 30-40 zone while price above MA60 + MACD positive → high."""
        closes, highs, lows, volumes = make_uptrend_oversold_macd_positive(n=80)
        idx = len(closes) - 1
        score = compute_rsi_divergence(closes, highs, lows, volumes, idx)
        # In a strong uptrend with dip, RSI should be lowish and MACD still positive
        assert score > 0.3, f"RSI divergence in uptrend should score > 0.3, got {score}"

    def test_rsi_divergence_in_downtrend(self):
        """In downtrend, price below MA60 → should score low."""
        closes, highs, lows, volumes = make_downtrend_with_dip(n=80)
        idx = len(closes) - 1
        score = compute_rsi_divergence(closes, highs, lows, volumes, idx)
        assert score <= 0.5, f"Downtrend RSI should score ≤ 0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 5: Volume Dry-Up During Pullback
# ═══════════════════════════════════════════════════════════════

class TestPullbackVolumeDryUp:
    def test_declining_volume_during_pullback(self):
        """Volume drying up during price decline → high score."""
        closes, highs, lows, volumes = make_pullback_with_declining_volume(n=80)
        idx = len(closes) - 1
        score = compute_volume_dry_up(closes, highs, lows, volumes, idx)
        assert score > 0.5, f"Volume dry-up in pullback should score > 0.5, got {score}"

    def test_high_volume_during_pullback(self):
        """Volume increasing during decline = panic selling → lower score."""
        closes, highs, lows, volumes = make_pullback_with_high_volume(n=80)
        idx = len(closes) - 1
        score = compute_volume_dry_up(closes, highs, lows, volumes, idx)
        # The declining volume case should score higher
        closes2, highs2, lows2, volumes2 = make_pullback_with_declining_volume(n=80)
        score_declining = compute_volume_dry_up(closes2, highs2, lows2, volumes2, len(closes2) - 1)
        assert score < score_declining, (
            f"High volume pullback ({score}) should score lower than "
            f"dry-up pullback ({score_declining})"
        )

    def test_no_pullback_neutral(self):
        """If price is not declining, should return neutral."""
        closes = [10.0 + i * 0.1 for i in range(80)]  # uptrend, no pullback
        highs = [c * 1.01 for c in closes]
        lows = [c * 0.99 for c in closes]
        volumes = [1000000] * 80
        score = compute_volume_dry_up(closes, highs, lows, volumes, 79)
        assert score == 0.5, f"No pullback should return 0.5, got {score}"


# ═══════════════════════════════════════════════════════════════
# Test 6: min_score PARAM_RANGE Validation
# ═══════════════════════════════════════════════════════════════

class TestMinScoreRange:
    def test_min_score_range_clamped(self):
        """min_score PARAM_RANGE should be (4, 8, True) — not (1, 10)."""
        from src.evolution.auto_evolve import _PARAM_RANGES
        lo, hi, is_int = _PARAM_RANGES["min_score"]
        assert lo == 4, f"min_score lower bound should be 4, got {lo}"
        assert hi == 8, f"min_score upper bound should be 8, got {hi}"
        assert is_int is True, f"min_score should be int type"

    def test_min_score_prevents_loose_threshold(self):
        """Evolution should not be able to set min_score below 4."""
        from src.evolution.auto_evolve import _PARAM_RANGES
        lo, _, _ = _PARAM_RANGES["min_score"]
        assert lo >= 4, (
            f"min_score minimum must be ≥ 4 to prevent overfitting. Got {lo}"
        )


# ═══════════════════════════════════════════════════════════════
# Test 7: Factor metadata validation
# ═══════════════════════════════════════════════════════════════

class TestFactorMetadata:
    def test_all_factors_have_pullback_category(self):
        """All pullback factors should have category 'pullback_strategy'."""
        import factors.pullback_uptrend_dip as f1
        import factors.pullback_ma20_bounce as f2
        import factors.pullback_healthy_retracement as f3
        import factors.pullback_rsi_divergence_in_uptrend as f4
        import factors.pullback_volume_dry_up as f5

        for mod in [f1, f2, f3, f4, f5]:
            assert mod.FACTOR_CATEGORY == "pullback_strategy", (
                f"{mod.FACTOR_NAME} should have category 'pullback_strategy', "
                f"got '{mod.FACTOR_CATEGORY}'"
            )

    def test_all_factors_return_bounded_scores(self):
        """All factors should return scores in [0, 1]."""
        closes, highs, lows, volumes = make_uptrend_with_dip(n=80)
        idx = len(closes) - 1

        for compute_fn, name in [
            (compute_uptrend_dip, "uptrend_dip"),
            (compute_ma20_bounce, "ma20_bounce"),
            (compute_healthy_retracement, "healthy_retracement"),
            (compute_rsi_divergence, "rsi_divergence"),
            (compute_volume_dry_up, "volume_dry_up"),
        ]:
            score = compute_fn(closes, highs, lows, volumes, idx)
            assert 0.0 <= score <= 1.0, (
                f"{name} returned out-of-range score: {score}"
            )
