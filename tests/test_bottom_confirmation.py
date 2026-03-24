"""
Tests for Bottom Confirmation Factors + Market State Safety Filter
===================================================================
At least 15 tests covering:
- Each bottom factor with known patterns (should return high score)
- Reverse patterns (should return low/neutral score)
- Market state filter: crash day reduces scores
- Market state filter: recovery day doesn't reduce scores
- Integration: scores are adjusted before picking
"""

import math
import pytest

# ── Import the 5 bottom factors ──
from factors.bottom_long_lower_shadow import compute as compute_long_lower_shadow
from factors.bottom_volume_decline_stabilize import compute as compute_vol_decline
from factors.bottom_reversal_candle import compute as compute_reversal_candle
from factors.bottom_support_bounce import compute as compute_support_bounce_factor
from factors.bottom_consecutive_decline_exhaustion import compute as compute_decline_exhaustion

# ── Import the market state filter ──
from src.evolution.market_filter import MarketStateFilter, BOTTOM_FACTOR_NAMES


# ═══════════════════════════════════════════════════════════════
# Helpers: generate synthetic price data
# ═══════════════════════════════════════════════════════════════

def make_flat_data(n=30, base_price=10.0, base_volume=1000000):
    """Flat data: all the same. No signal expected."""
    closes = [base_price] * n
    highs = [base_price * 1.01] * n
    lows = [base_price * 0.99] * n
    volumes = [base_volume] * n
    return closes, highs, lows, volumes


def make_hammer_candle(n=30, idx=None):
    """Create data that includes a clear hammer candle at given idx.

    At idx: close > open, long lower shadow > 2x body, upper shadow tiny.
    """
    if idx is None:
        idx = n - 1
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    # Make preceding days slightly declining so it's at a "bottom"
    for i in range(max(0, idx - 5), idx):
        closes[i] = 10.0 - (idx - i) * 0.3
        highs[i] = closes[i] + 0.2
        lows[i] = closes[i] - 0.2

    # Hammer candle at idx:
    # prev_close (open proxy) = closes[idx-1], close > prev_close (bullish)
    # low far below, close near high
    closes[idx - 1] = 8.5  # "open" for hammer day
    closes[idx] = 9.0      # close above open → bullish
    highs[idx] = 9.1       # tiny upper shadow
    lows[idx] = 7.5        # very long lower shadow: 7.5 -> 8.5 = 1.0, body = 0.5

    return closes, highs, lows, volumes


def make_declining_volume_data(n=30, idx=None):
    """Create data with declining volume + price stabilization at idx."""
    if idx is None:
        idx = n - 1
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    # Create a prior decline
    for i in range(max(0, idx - 10), idx - 3):
        closes[i] = 10.0 - (idx - 3 - i) * 0.2
        lows[i] = closes[i] - 0.3

    # Last 4 days: price stabilizes (stops making new lows)
    base = closes[idx - 4] if idx >= 4 else 8.0
    for i in range(idx - 3, idx + 1):
        closes[i] = base + 0.05 * (i - (idx - 3))
        lows[i] = closes[i] - 0.1
        highs[i] = closes[i] + 0.1

    # Declining volume for last 3 days
    volumes[idx - 2] = 800000
    volumes[idx - 1] = 600000
    volumes[idx] = 400000

    return closes, highs, lows, volumes


def make_reversal_data(n=30, idx=None):
    """Create data with 3+ red candles followed by a bullish reversal at idx."""
    if idx is None:
        idx = n - 1
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    # 4 red candles before idx
    for i in range(idx - 4, idx):
        closes[i] = 10.0 - (i - (idx - 5)) * 0.5
    # closes[idx-4]=9.5, closes[idx-3]=9.0, closes[idx-2]=8.5, closes[idx-1]=8.0

    # Green candle at idx that closes above midpoint of previous red
    # prev red: open_proxy=closes[idx-2]=8.5, close=closes[idx-1]=8.0
    # midpoint = 8.25
    closes[idx] = 8.6  # above 8.25 (midpoint) and even above 8.5 (prev open)

    return closes, highs, lows, volumes


def make_support_bounce_data(n=30, idx=None):
    """Create data where price touches 20-day support and bounces at idx."""
    if idx is None:
        idx = n - 1
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    # Set support level: lowest low in last 20 days at 9.0
    if idx >= 15:
        lows[idx - 15] = 9.0

    # Price approaches support
    for i in range(max(0, idx - 3), idx):
        closes[i] = 9.2 - (idx - 1 - i) * 0.1
        lows[i] = closes[i] - 0.15

    # At idx: low touches support (9.0), then bounces to close at 9.3
    lows[idx] = 9.0
    closes[idx] = 9.3
    highs[idx] = 9.35

    return closes, highs, lows, volumes


def make_exhaustion_data(n=30, idx=None):
    """Create data with 4+ consecutive declines with deceleration at idx."""
    if idx is None:
        idx = n - 1
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    # 5 consecutive declining days ending at idx
    # Each day's decline is smaller than the previous (deceleration)
    drops = [0.8, 0.6, 0.4, 0.3, 0.15]  # decelerating
    base = 10.0
    for i, drop in enumerate(drops):
        day = idx - len(drops) + 1 + i
        if day >= 0:
            base -= drop
            closes[day] = base
            lows[day] = base - 0.1
            highs[day] = base + 0.1

    return closes, highs, lows, volumes


# ═══════════════════════════════════════════════════════════════
# Part 1: Bottom Factor Tests (10 tests)
# ═══════════════════════════════════════════════════════════════

class TestBottomLongLowerShadow:
    """Tests for bottom_long_lower_shadow factor."""

    def test_clear_hammer_scores_high(self):
        """A clear bullish hammer should score >= 0.7."""
        closes, highs, lows, volumes = make_hammer_candle(30, 29)
        score = compute_long_lower_shadow(closes, highs, lows, volumes, 29)
        assert score >= 0.7, f"Hammer score {score} should be >= 0.7"

    def test_no_shadow_scores_neutral(self):
        """Flat data with no shadow should return ~0.5 (neutral)."""
        closes, highs, lows, volumes = make_flat_data(30)
        score = compute_long_lower_shadow(closes, highs, lows, volumes, 29)
        assert score == pytest.approx(0.5, abs=0.1), f"No-shadow score {score} should be ~0.5"

    def test_bearish_candle_not_high(self):
        """A long lower shadow but bearish close should not score as high."""
        closes, highs, lows, volumes = make_hammer_candle(30, 29)
        # Swap to make bearish: close below open proxy
        closes[29] = 7.8  # below prev_close (8.5)
        score = compute_long_lower_shadow(closes, highs, lows, volumes, 29)
        assert score < 0.7, f"Bearish shadow score {score} should be < 0.7"


class TestBottomVolumeDeclStabilize:
    """Tests for bottom_volume_decline_stabilize factor."""

    def test_declining_volume_stable_price_scores_high(self):
        """Declining volume + price stabilization = high score."""
        closes, highs, lows, volumes = make_declining_volume_data(30, 29)
        score = compute_vol_decline(closes, highs, lows, volumes, 29)
        assert score >= 0.7, f"Vol decline + stable score {score} should be >= 0.7"

    def test_increasing_volume_scores_neutral(self):
        """Increasing volume should return neutral."""
        closes, highs, lows, volumes = make_flat_data(30)
        # Increasing volume
        volumes[27] = 800000
        volumes[28] = 1200000
        volumes[29] = 1600000
        score = compute_vol_decline(closes, highs, lows, volumes, 29)
        assert score <= 0.6, f"Increasing vol score {score} should be <= 0.6"


class TestBottomReversalCandle:
    """Tests for bottom_reversal_candle factor."""

    def test_reversal_after_red_candles_scores_high(self):
        """Green candle after 3+ reds closing above midpoint = high score."""
        closes, highs, lows, volumes = make_reversal_data(30, 29)
        score = compute_reversal_candle(closes, highs, lows, volumes, 29)
        assert score >= 0.7, f"Reversal score {score} should be >= 0.7"

    def test_no_prior_reds_scores_neutral(self):
        """Without prior red candles, reversal should score neutral."""
        closes, highs, lows, volumes = make_flat_data(30)
        # Make today green
        closes[28] = 9.8
        closes[29] = 10.2
        score = compute_reversal_candle(closes, highs, lows, volumes, 29)
        assert score <= 0.6, f"No-prior-reds score {score} should be <= 0.6"


class TestBottomSupportBounce:
    """Tests for bottom_support_bounce factor."""

    def test_bounce_from_support_scores_high(self):
        """Price touching support and bouncing = high score."""
        closes, highs, lows, volumes = make_support_bounce_data(30, 29)
        score = compute_support_bounce_factor(closes, highs, lows, volumes, 29)
        assert score >= 0.7, f"Support bounce score {score} should be >= 0.7"

    def test_far_from_support_scores_neutral(self):
        """Price far above support should score ~ neutral."""
        closes, highs, lows, volumes = make_flat_data(30, base_price=15.0)
        # Support is around 14.85 (lows), price at 15 is far above
        score = compute_support_bounce_factor(closes, highs, lows, volumes, 29)
        assert score <= 0.6, f"Far-from-support score {score} should be <= 0.6"


class TestBottomConsecutiveDeclineExhaustion:
    """Tests for bottom_consecutive_decline_exhaustion factor."""

    def test_decelerating_decline_scores_high(self):
        """4+ declining days with deceleration = high score."""
        closes, highs, lows, volumes = make_exhaustion_data(30, 29)
        score = compute_decline_exhaustion(closes, highs, lows, volumes, 29)
        assert score >= 0.7, f"Decel decline score {score} should be >= 0.7"

    def test_accelerating_decline_scores_low(self):
        """Decline accelerating (bigger drops) should NOT score high."""
        closes, highs, lows, volumes = make_flat_data(30)
        # 4 consecutive declining days with ACCELERATING drops
        closes[25] = 10.0
        closes[26] = 9.85   # drop 0.15
        closes[27] = 9.55   # drop 0.30
        closes[28] = 9.05   # drop 0.50
        closes[29] = 8.25   # drop 0.80
        score = compute_decline_exhaustion(closes, highs, lows, volumes, 29)
        assert score <= 0.6, f"Accel decline score {score} should be <= 0.6"

    def test_too_few_declines_neutral(self):
        """Only 2 declining days should return neutral."""
        closes, highs, lows, volumes = make_flat_data(30)
        closes[27] = 10.0
        closes[28] = 9.8
        closes[29] = 9.7
        score = compute_decline_exhaustion(closes, highs, lows, volumes, 29)
        assert score <= 0.55, f"Few declines score {score} should be <= 0.55"


# ═══════════════════════════════════════════════════════════════
# Part 2: MarketStateFilter Tests (6+ tests)
# ═══════════════════════════════════════════════════════════════

def _make_stock_data(n=50, trend="flat"):
    """Generate stock data for market state tests.

    trend: 'flat', 'crash', 'recovery', 'strong'
    """
    closes = [10.0] * n
    highs = [10.2] * n
    lows = [9.8] * n
    volumes = [1000000] * n

    if trend == "crash":
        for i in range(1, n):
            closes[i] = closes[i - 1] * 0.97  # 3% daily drop
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
    elif trend == "recovery":
        # First half crash, second half recovery
        for i in range(1, n // 2):
            closes[i] = closes[i - 1] * 0.98
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
        for i in range(n // 2, n):
            closes[i] = closes[i - 1] * 1.02
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
    elif trend == "strong":
        for i in range(1, n):
            closes[i] = closes[i - 1] * 1.01
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99

    return {"close": closes, "high": highs, "low": lows, "volume": volumes, "open": closes[:]}


def _make_indicators(stock_data, n=50):
    """Create minimal indicator dict for testing."""
    closes = stock_data["close"]
    rsi = [50.0] * n
    # Compute rough RSI
    for i in range(14, n):
        gains = sum(max(closes[j] - closes[j - 1], 0) for j in range(i - 13, i + 1))
        losses = sum(max(closes[j - 1] - closes[j], 0) for j in range(i - 13, i + 1))
        if losses > 0:
            rs = gains / losses
            rsi[i] = 100 - 100 / (1 + rs)
        else:
            rsi[i] = 100.0

    return {"rsi": rsi, "_factor_fns": {}}


class TestMarketStateFilter:
    """Tests for MarketStateFilter."""

    def test_crash_day_reduces_market_state(self):
        """When >70% of stocks are declining, market state should be < 0.5."""
        msf = MarketStateFilter()
        # Create 10 crashing stocks
        all_data = {}
        all_indicators = {}
        codes = []
        for i in range(10):
            code = f"stock_{i}"
            codes.append(code)
            all_data[code] = _make_stock_data(50, "crash")
            all_indicators[code] = _make_indicators(all_data[code], 50)

        state = msf.compute_market_state(all_data, all_indicators, codes, 30)
        assert state < 0.5, f"Crash market state {state} should be < 0.5"

    def test_strong_market_high_state(self):
        """Strong market (most stocks rising) should produce state > 0.5."""
        msf = MarketStateFilter()
        all_data = {}
        all_indicators = {}
        codes = []
        for i in range(10):
            code = f"stock_{i}"
            codes.append(code)
            all_data[code] = _make_stock_data(50, "strong")
            all_indicators[code] = _make_indicators(all_data[code], 50)

        state = msf.compute_market_state(all_data, all_indicators, codes, 30)
        assert state > 0.5, f"Strong market state {state} should be > 0.5"

    def test_adjust_score_extreme_crash(self):
        """In extreme crash (state < 0.2), score should be heavily reduced."""
        msf = MarketStateFilter()
        raw = 8.0
        adjusted = msf.adjust_score(raw, 0.15, has_bottom_signal=False)
        assert adjusted == pytest.approx(raw * 0.3), f"Extreme crash: {adjusted} != {raw * 0.3}"

    def test_adjust_score_crash_no_bottom(self):
        """In crash (state < 0.3) without bottom signal, score *= 0.5."""
        msf = MarketStateFilter()
        raw = 8.0
        adjusted = msf.adjust_score(raw, 0.25, has_bottom_signal=False)
        assert adjusted == pytest.approx(raw * 0.5), f"Crash no bottom: {adjusted} != {raw * 0.5}"

    def test_adjust_score_crash_with_bottom(self):
        """In crash (state < 0.3) WITH bottom signal, score only *= 0.8."""
        msf = MarketStateFilter()
        raw = 8.0
        adjusted = msf.adjust_score(raw, 0.25, has_bottom_signal=True)
        assert adjusted == pytest.approx(raw * 0.8), f"Crash with bottom: {adjusted} != {raw * 0.8}"

    def test_adjust_score_strong_market_unchanged(self):
        """In strong market (state > 0.7), score should be unchanged."""
        msf = MarketStateFilter()
        raw = 7.5
        adjusted = msf.adjust_score(raw, 0.8, has_bottom_signal=False)
        assert adjusted == raw, f"Strong market: {adjusted} != {raw}"

    def test_recovery_day_doesnt_reduce(self):
        """Recovery market should not reduce scores (state should be > 0.5)."""
        msf = MarketStateFilter()
        all_data = {}
        all_indicators = {}
        codes = []
        for i in range(10):
            code = f"stock_{i}"
            codes.append(code)
            all_data[code] = _make_stock_data(50, "recovery")
            all_indicators[code] = _make_indicators(all_data[code], 50)

        # Check at recovery point (day 40, well into the recovery phase)
        state = msf.compute_market_state(all_data, all_indicators, codes, 40)
        raw = 7.0
        adjusted = msf.adjust_score(raw, state, has_bottom_signal=False)
        # In recovery, adjusted score should not be heavily penalized
        assert adjusted >= raw * 0.7, \
            f"Recovery adjusted {adjusted} should be >= {raw * 0.7} (state={state})"


# ═══════════════════════════════════════════════════════════════
# Part 3: Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration: scores are adjusted before picking."""

    def test_bottom_factor_names_constant(self):
        """BOTTOM_FACTOR_NAMES should contain all 5 factor names."""
        expected = {
            "bottom_long_lower_shadow",
            "bottom_volume_decline_stabilize",
            "bottom_reversal_candle",
            "bottom_support_bounce",
            "bottom_consecutive_decline_exhaustion",
        }
        assert BOTTOM_FACTOR_NAMES == expected

    def test_check_bottom_signals_detects_signal(self):
        """check_bottom_signals should return True when factor fires >= 0.7."""
        closes, highs, lows, volumes = make_flat_data(30)

        # Mock factor function that always returns high score
        def mock_high_fn(c, h, l, v, idx):
            return 0.9

        indicators = {
            "_factor_fns": {"bottom_long_lower_shadow": mock_high_fn}
        }
        has_signal = MarketStateFilter.check_bottom_signals(
            indicators, closes, highs, lows, volumes, 29
        )
        assert has_signal is True

    def test_check_bottom_signals_no_signal(self):
        """check_bottom_signals should return False when no factor fires."""
        closes, highs, lows, volumes = make_flat_data(30)

        def mock_flat_fn(c, h, l, v, idx):
            return 0.5

        indicators = {
            "_factor_fns": {"bottom_long_lower_shadow": mock_flat_fn}
        }
        has_signal = MarketStateFilter.check_bottom_signals(
            indicators, closes, highs, lows, volumes, 29
        )
        assert has_signal is False

    def test_market_filter_adjusts_picks(self):
        """In a crash, market filter should reduce scores below min_score threshold,
        effectively filtering out stocks that barely passed."""
        msf = MarketStateFilter()

        # Stock that barely passes min_score of 6
        raw_score = 6.5
        # Crash market state
        adjusted = msf.adjust_score(raw_score, 0.15, has_bottom_signal=False)
        # With extreme crash: 6.5 * 0.3 = 1.95 < 6 → would be filtered out
        assert adjusted < 6.0, \
            f"Crash-adjusted score {adjusted} should be below min_score 6.0"

    def test_early_idx_returns_neutral(self):
        """All factors should return 0.5 for idx < threshold (early data)."""
        closes, highs, lows, volumes = make_flat_data(10)
        for compute_fn in [compute_long_lower_shadow, compute_vol_decline,
                           compute_reversal_candle, compute_support_bounce_factor,
                           compute_decline_exhaustion]:
            score = compute_fn(closes, highs, lows, volumes, 2)
            assert score == 0.5, f"{compute_fn.__module__} returned {score} for early idx"
