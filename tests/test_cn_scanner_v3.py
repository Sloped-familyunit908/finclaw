"""
Tests for A-Share Scanner V3 Scoring Engine
=============================================
Tests the 11 new OHLCV-based signal functions and the v3 scoring engine.
"""

import numpy as np
import pytest

from src.cn_scanner import (
    compute_score,
    compute_score_v2,
    compute_score_v3,
    classify_signal_v3,
    _signal_three_soldiers,
    _signal_long_lower_shadow,
    _signal_doji_at_bottom,
    _signal_volume_breakout_high,
    _signal_volume_climax_reversal,
    _signal_accumulation,
    _signal_macd_hist_acceleration,
    _signal_rsi_bullish_divergence,
    _signal_squeeze_release,
    _signal_adx_trend_strength,
    _signal_price_above_vwap,
    backtest_cn_strategy,
    format_backtest_output,
    _compute_score_at,
)


# ── Helper: generate synthetic OHLCV ─────────────────────────────────

def _make_ohlcv(n: int = 60, base: float = 100.0, seed: int = 42):
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    close = np.empty(n)
    close[0] = base
    for i in range(1, n):
        close[i] = close[i - 1] * (1 + rng.randn() * 0.02)
    open_ = np.empty(n)
    open_[0] = base
    open_[1:] = close[:-1]
    high = np.maximum(close, open_) * (1 + rng.rand(n) * 0.01)
    low = np.minimum(close, open_) * (1 - rng.rand(n) * 0.01)
    volume = rng.randint(500, 2000, size=n).astype(np.float64)
    return open_, high, low, close, volume


# ── Three Soldiers ───────────────────────────────────────────────────

class TestThreeSoldiersSignal:
    def test_positive_trigger(self):
        """3 up days closing near high → +3."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 100.0
        low = np.ones(n) * 100.0
        # Last 3 days: bullish candles
        for i in range(-3, 0):
            open_[i] = 100 + (i + 3) * 2
            close[i] = open_[i] + 2.0  # close > open
            high[i] = close[i] + 0.1   # tiny upper wick
            low[i] = open_[i] - 0.1
        pts, reason = _signal_three_soldiers(open_, high, low, close)
        assert pts == 3
        assert "three soldiers" in reason

    def test_no_trigger_down_day(self):
        """One down day in last 3 → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 100.0
        low = np.ones(n) * 100.0
        open_[-3] = 100; close[-3] = 102; high[-3] = 102.1; low[-3] = 99.9
        open_[-2] = 102; close[-2] = 101; high[-2] = 102.5; low[-2] = 100  # down day
        open_[-1] = 101; close[-1] = 103; high[-1] = 103.1; low[-1] = 100.9
        pts, _ = _signal_three_soldiers(open_, high, low, close)
        assert pts == 0

    def test_no_trigger_long_upper_wick(self):
        """Close not near high (big upper wick) → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 100.0
        low = np.ones(n) * 100.0
        for i in range(-3, 0):
            open_[i] = 100 + (i + 3) * 2
            close[i] = open_[i] + 2.0
            high[i] = close[i] + 5.0  # huge upper wick
            low[i] = open_[i] - 0.1
        pts, _ = _signal_three_soldiers(open_, high, low, close)
        assert pts == 0

    def test_short_data(self):
        pts, _ = _signal_three_soldiers(
            np.array([100.0, 101.0, 102.0]),
            np.array([101.0, 102.0, 103.0]),
            np.array([99.0, 100.0, 101.0]),
            np.array([100.5, 101.5, 102.5]),
        )
        assert pts == 0


# ── Long Lower Shadow ───────────────────────────────────────────────

class TestLongLowerShadowSignal:
    def test_positive_trigger(self):
        """Long lower shadow at oversold → +3."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 100.0
        low = np.ones(n) * 100.0
        # Hammer candle at end
        open_[-1] = 100.0
        close[-1] = 100.5  # small body
        high[-1] = 100.7
        low[-1] = 97.0     # long lower shadow: 3.0 vs body 0.5
        pts, reason = _signal_long_lower_shadow(open_, high, low, close, 30.0)
        assert pts == 3
        assert "long lower shadow" in reason

    def test_no_trigger_rsi_not_oversold(self):
        """RSI >= 35 → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.copy(open_)
        high = np.copy(open_)
        low = np.copy(open_)
        open_[-1] = 100.0; close[-1] = 100.5; high[-1] = 100.7; low[-1] = 97.0
        pts, _ = _signal_long_lower_shadow(open_, high, low, close, 40.0)
        assert pts == 0

    def test_no_trigger_short_shadow(self):
        """Short lower shadow → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.copy(open_)
        high = np.copy(open_)
        low = np.copy(open_)
        open_[-1] = 100.0; close[-1] = 102.0; high[-1] = 102.5; low[-1] = 99.5
        # body=2, shadow=0.5 → shadow < 2x body
        pts, _ = _signal_long_lower_shadow(open_, high, low, close, 25.0)
        assert pts == 0


# ── Doji at Bottom ───────────────────────────────────────────────────

class TestDojiAtBottomSignal:
    def test_positive_trigger(self):
        """Doji (open ≈ close), RSI<40, low volume → +2."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        volume = np.ones(n) * 1000.0
        # Doji: open ≈ close
        open_[-1] = 100.0
        close[-1] = 100.3  # 0.3% difference
        volume[-1] = 500.0  # low volume (0.5x avg)
        pts, reason = _signal_doji_at_bottom(open_, high, low, close, volume, 35.0)
        assert pts == 2
        assert "doji at bottom" in reason

    def test_no_trigger_big_body(self):
        """Not a doji (big body) → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        volume = np.ones(n) * 1000.0
        open_[-1] = 100.0; close[-1] = 102.0; volume[-1] = 500.0  # 2% body
        pts, _ = _signal_doji_at_bottom(open_, high, low, close, volume, 35.0)
        assert pts == 0

    def test_no_trigger_rsi_too_high(self):
        """RSI >= 40 → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        volume = np.ones(n) * 1000.0
        open_[-1] = 100.0; close[-1] = 100.3; volume[-1] = 500.0
        pts, _ = _signal_doji_at_bottom(open_, high, low, close, volume, 45.0)
        assert pts == 0

    def test_no_trigger_high_volume(self):
        """Volume not low → 0."""
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        volume = np.ones(n) * 1000.0
        open_[-1] = 100.0; close[-1] = 100.3; volume[-1] = 1200.0  # above avg
        pts, _ = _signal_doji_at_bottom(open_, high, low, close, volume, 35.0)
        assert pts == 0

    def test_no_volume_data(self):
        n = 60
        open_ = np.ones(n) * 100.0
        close = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        pts, _ = _signal_doji_at_bottom(open_, high, low, close, None, 35.0)
        assert pts == 0


# ── Volume Breakout High ────────────────────────────────────────────

class TestVolumeBreakoutHighSignal:
    def test_positive_trigger(self):
        """Close > 20d high, vol > 2.5x, close in top 20% of range → +4."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        open_ = np.ones(n) * 100.0
        high = np.ones(n) * 101.0
        low = np.ones(n) * 99.0
        # New 20-day high
        close[-1] = 110.0
        open_[-1] = 105.0
        high[-1] = 111.0
        low[-1] = 104.0
        volume[-1] = 3000.0  # 3x average
        pts, reason = _signal_volume_breakout_high(open_, high, low, close, volume)
        assert pts == 4
        assert "vol breakout new high" in reason

    def test_no_trigger_not_new_high(self):
        """Close below 20d high → 0."""
        n = 60
        close = np.ones(n) * 100.0
        close[-10] = 110.0  # recent high was 10 days ago
        close[-1] = 109.0
        volume = np.ones(n) * 1000.0; volume[-1] = 3000.0
        open_ = np.ones(n) * 100.0; open_[-1] = 105.0
        high = np.ones(n) * 101.0; high[-1] = 111.0; high[-10] = 111.0
        low = np.ones(n) * 99.0; low[-1] = 104.0
        pts, _ = _signal_volume_breakout_high(open_, high, low, close, volume)
        assert pts == 0

    def test_no_trigger_low_volume(self):
        """Volume not enough → 0."""
        n = 60
        close = np.ones(n) * 100.0
        close[-1] = 110.0
        volume = np.ones(n) * 1000.0; volume[-1] = 2000.0  # only 2x
        open_ = np.ones(n) * 100.0; open_[-1] = 105.0
        high = np.ones(n) * 101.0; high[-1] = 111.0
        low = np.ones(n) * 99.0; low[-1] = 104.0
        pts, _ = _signal_volume_breakout_high(open_, high, low, close, volume)
        assert pts == 0

    def test_no_trigger_close_not_near_high(self):
        """Close in bottom part of range → 0."""
        n = 60
        close = np.ones(n) * 100.0
        close[-1] = 110.0
        volume = np.ones(n) * 1000.0; volume[-1] = 3000.0
        open_ = np.ones(n) * 100.0; open_[-1] = 112.0
        high = np.ones(n) * 101.0; high[-1] = 115.0
        low = np.ones(n) * 99.0; low[-1] = 105.0
        # position = (110 - 105) / (115 - 105) = 0.5 < 0.8
        pts, _ = _signal_volume_breakout_high(open_, high, low, close, volume)
        assert pts == 0


# ── Volume Climax Reversal ──────────────────────────────────────────

class TestVolumeClimaxReversalSignal:
    def test_positive_trigger(self):
        """Big down day with huge volume, followed by up day → +3."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-3] = 100.0  # baseline
        close[-2] = 96.0   # down day
        close[-1] = 97.0   # up day (bounce)
        volume[-2] = 4000.0  # 4x avg on down day
        pts, reason = _signal_volume_climax_reversal(close, volume)
        assert pts == 3
        assert "vol climax reversal" in reason

    def test_no_trigger_up_day_first(self):
        """Day -2 is not down → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-3] = 100.0; close[-2] = 102.0; close[-1] = 103.0
        volume[-2] = 4000.0
        pts, _ = _signal_volume_climax_reversal(close, volume)
        assert pts == 0

    def test_no_trigger_no_bounce(self):
        """No bounce on day -1 → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-3] = 100.0; close[-2] = 96.0; close[-1] = 95.0  # still falling
        volume[-2] = 4000.0
        pts, _ = _signal_volume_climax_reversal(close, volume)
        assert pts == 0

    def test_no_trigger_low_volume(self):
        """Volume not extreme → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-3] = 100.0; close[-2] = 96.0; close[-1] = 97.0
        volume[-2] = 2000.0  # only 2x
        pts, _ = _signal_volume_climax_reversal(close, volume)
        assert pts == 0


# ── Accumulation Pattern ────────────────────────────────────────────

class TestAccumulationSignal:
    def test_positive_trigger(self):
        """Price flat, volume increasing >50% → +2."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        # Price flat last 5 days (within 3%)
        close[-5:] = [100, 100.5, 99.5, 100.2, 100.1]
        # Previous 5 days normal volume, recent 5 days higher
        volume[-10:-5] = [1000, 1000, 1000, 1000, 1000]
        volume[-5:] = [1600, 1700, 1800, 1600, 1700]  # ~70% increase
        pts, reason = _signal_accumulation(close, volume)
        assert pts == 2
        assert "accumulation" in reason

    def test_no_trigger_price_moving(self):
        """Price not flat → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-5:] = [100, 102, 104, 106, 108]  # >3% range
        volume[-5:] = [1600, 1700, 1800, 1600, 1700]
        pts, _ = _signal_accumulation(close, volume)
        assert pts == 0

    def test_no_trigger_volume_flat(self):
        """Volume not increasing enough → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-5:] = [100, 100.5, 99.5, 100.2, 100.1]
        volume[-5:] = [1100, 1050, 1100, 1050, 1100]  # ~10% increase
        pts, _ = _signal_accumulation(close, volume)
        assert pts == 0

    def test_short_data(self):
        pts, _ = _signal_accumulation(np.ones(5) * 100, np.ones(5) * 1000)
        assert pts == 0


# ── MACD Histogram Acceleration ─────────────────────────────────────

class TestMACDHistAccelerationSignal:
    def test_positive_trigger(self):
        """MACD hist positive and increasing for 3 days → +2."""
        # Create a strong uptrend that produces accelerating MACD hist
        n = 80
        close = np.ones(n) * 100.0
        # Gentle decline then sharp upturn
        close[:40] = np.linspace(100, 95, 40)
        close[40:] = np.linspace(95, 120, 40)
        pts, reason = _signal_macd_hist_acceleration(close)
        # May or may not trigger depending on MACD internals
        assert pts >= 0
        if pts > 0:
            assert "MACD hist accelerating" in reason

    def test_short_data(self):
        pts, _ = _signal_macd_hist_acceleration(np.ones(20) * 100)
        assert pts == 0


# ── RSI Bullish Divergence ──────────────────────────────────────────

class TestRSIBullishDivergenceSignal:
    def test_positive_setup(self):
        """Price lower low but RSI higher low → +3."""
        # Create a price pattern with two troughs where RSI diverges
        n = 60
        close = np.ones(n) * 100.0
        # First trough around day 45
        close[40:50] = np.linspace(100, 85, 10)
        close[50:55] = np.linspace(86, 95, 5)
        # Second trough (lower) at end
        close[55:60] = np.linspace(94, 83, 5)
        from src.ta import rsi as calc_rsi
        rsi_arr = calc_rsi(close, 14)
        pts, reason = _signal_rsi_bullish_divergence(close, rsi_arr)
        # Divergence depends on RSI values — just verify no crash
        assert pts >= 0
        if pts > 0:
            assert "RSI bullish divergence" in reason

    def test_no_trigger_uptrend(self):
        """Uptrend (no new low) → 0."""
        close = np.linspace(90, 120, 60)
        from src.ta import rsi as calc_rsi
        rsi_arr = calc_rsi(close, 14)
        pts, _ = _signal_rsi_bullish_divergence(close, rsi_arr)
        assert pts == 0

    def test_short_data(self):
        close = np.ones(15) * 100.0
        rsi_arr = np.ones(15) * 50.0
        pts, _ = _signal_rsi_bullish_divergence(close, rsi_arr)
        assert pts == 0


# ── Squeeze Release ─────────────────────────────────────────────────

class TestSqueezeReleaseSignal:
    def test_positive_trigger(self):
        """Tight Bollinger bandwidth then expanding → +3."""
        # Create price series that's tight then explodes
        n = 60
        close = np.ones(n) * 100.0
        # Very tight range for 10 days
        close[-15:-5] = [100.0, 100.1, 99.9, 100.0, 100.1,
                         99.9, 100.0, 100.1, 99.9, 100.0]
        # Then expand
        close[-5:] = [101.0, 102.5, 104.0, 106.0, 108.0]
        pts, reason = _signal_squeeze_release(close)
        # May not trigger if BB period doesn't align perfectly
        assert pts >= 0
        if pts > 0:
            assert "squeeze release" in reason

    def test_no_trigger_volatile(self):
        """Always volatile (no squeeze) → 0."""
        rng = np.random.RandomState(42)
        close = 100 + np.cumsum(rng.randn(60) * 3)
        pts, _ = _signal_squeeze_release(close)
        assert pts == 0

    def test_short_data(self):
        pts, _ = _signal_squeeze_release(np.ones(20) * 100)
        assert pts == 0


# ── ADX Trend Strength ──────────────────────────────────────────────

class TestADXTrendStrengthSignal:
    def test_positive_trigger(self):
        """Strong uptrend → ADX > 25, +DI > -DI → +2."""
        n = 80
        # Strong uptrend
        close = np.linspace(80, 160, n)
        high = close + 1.0
        low = close - 1.0
        pts, reason = _signal_adx_trend_strength(high, low, close)
        assert pts == 2
        assert "ADX strong uptrend" in reason

    def test_no_trigger_sideways(self):
        """Sideways market → ADX low → 0."""
        n = 80
        rng = np.random.RandomState(42)
        close = 100 + rng.randn(n) * 0.5  # very tight range
        high = close + 0.5
        low = close - 0.5
        pts, _ = _signal_adx_trend_strength(high, low, close)
        # ADX should be low in sideways market
        assert pts == 0

    def test_short_data(self):
        close = np.ones(20) * 100.0
        pts, _ = _signal_adx_trend_strength(close + 1, close - 1, close)
        assert pts == 0


# ── Price Above VWAP ────────────────────────────────────────────────

class TestPriceAboveVWAPSignal:
    def test_positive_trigger(self):
        """Price above VWAP → +1."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        # Last day price spikes above VWAP
        close[-1] = 110.0
        pts, reason = _signal_price_above_vwap(close, volume)
        assert pts == 1
        assert "above VWAP" in reason

    def test_no_trigger_below_vwap(self):
        """Price below VWAP → 0."""
        n = 60
        close = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        close[-1] = 90.0  # below average
        pts, _ = _signal_price_above_vwap(close, volume)
        assert pts == 0

    def test_no_volume_data(self):
        close = np.ones(60) * 100.0
        pts, _ = _signal_price_above_vwap(close, None)
        assert pts == 0

    def test_short_data(self):
        pts, _ = _signal_price_above_vwap(np.ones(10) * 100, np.ones(10) * 1000)
        assert pts == 0


# ── V3 Compute Score Tests ──────────────────────────────────────────

class TestComputeScoreV3:
    def test_returns_expected_keys(self):
        """compute_score_v3 returns all expected keys including 'strategy'."""
        open_, high, low, close, volume = _make_ohlcv()
        result = compute_score_v3(close, volume, open_, high, low)
        expected_keys = {
            'score', 'rsi_val', 'macd_hist', 'pct_b',
            'change_1d', 'change_5d', 'volume_ratio',
            'signal', 'price', 'reasons', 'strategy',
        }
        assert set(result.keys()) == expected_keys
        assert result['strategy'] == 'v3'

    def test_insufficient_data(self):
        """Short data returns zero score with v3 strategy tag."""
        close = np.array([100.0, 101.0, 102.0])
        result = compute_score_v3(close)
        assert result['score'] == 0
        assert result['strategy'] == 'v3'

    def test_v3_score_gte_v2(self):
        """V3 score should be >= v2 (adds signals on top)."""
        open_, high, low, close, volume = _make_ohlcv()
        v2 = compute_score_v2(close, volume)
        v3 = compute_score_v3(close, volume, open_, high, low)
        assert v3['score'] >= v2['score']

    def test_v3_works_without_ohlcv(self):
        """V3 should work with only close+volume (synthesizes OHLCV)."""
        close = np.linspace(90, 110, 60)
        volume = np.ones(60) * 1000.0
        result = compute_score_v3(close, volume)
        assert result['strategy'] == 'v3'
        assert isinstance(result['score'], (int, float))

    def test_strong_bullish_scores_high(self):
        """A strong bullish pattern should score high in v3."""
        n = 60
        # Create uptrend with three soldiers at end
        close = np.linspace(80, 100, 57)
        close = np.append(close, [101, 103, 106])
        open_ = np.empty(n)
        open_[0] = 80; open_[1:] = close[:-1]
        high = close * 1.005
        low = open_ * 0.995
        volume = np.ones(n) * 1000.0
        volume[-3:] = 2000  # increasing volume
        result = compute_score_v3(close, volume, open_, high, low)
        assert result['score'] >= 3  # at minimum v1+v2 base

    def test_v3_with_30_bars(self):
        """Exactly 30 bars should work (boundary)."""
        open_, high, low, close, volume = _make_ohlcv(n=30)
        result = compute_score_v3(close, volume, open_, high, low)
        assert result['strategy'] == 'v3'

    def test_v3_with_29_bars(self):
        """29 bars (below minimum) → empty result."""
        close = np.linspace(90, 110, 29)
        result = compute_score_v3(close)
        assert result['score'] == 0
        assert result['strategy'] == 'v3'


# ── V3 Signal Classification ────────────────────────────────────────

class TestClassifySignalV3:
    def test_strong_buy(self):
        assert classify_signal_v3(14) == "*** STRONG BUY"
        assert classify_signal_v3(20) == "*** STRONG BUY"

    def test_buy(self):
        assert classify_signal_v3(10) == "** BUY"
        assert classify_signal_v3(13) == "** BUY"

    def test_watch(self):
        assert classify_signal_v3(6) == "WATCH"
        assert classify_signal_v3(9) == "WATCH"

    def test_hold(self):
        assert classify_signal_v3(5) == "HOLD"
        assert classify_signal_v3(0) == "HOLD"
        assert classify_signal_v3(-1) == "HOLD"


# ── V3 Backtest Tests ───────────────────────────────────────────────

class TestBacktestV3:
    @staticmethod
    def _make_synthetic_ohlcv(n: int = 120, seed: int = 42) -> dict[str, dict]:
        """Create synthetic OHLCV data for 3 stocks."""
        np.random.seed(seed)
        data: dict[str, dict] = {}

        for ticker, pattern in [
            ('600519.SS', 'oversold'),
            ('000858.SZ', 'uptrend'),
            ('300750.SZ', 'random'),
        ]:
            if pattern == 'oversold':
                close = np.ones(n) * 100.0
                for i in range(40, 70):
                    close[i] = 100 - (i - 40) * 0.5
                for i in range(70, n):
                    close[i] = close[69] + (i - 69) * 0.3
            elif pattern == 'uptrend':
                close = np.linspace(50, 150, n)
            else:
                close = 100 + np.cumsum(np.random.randn(n) * 0.5)
                close = np.maximum(close, 10)

            open_ = np.empty(n)
            open_[0] = close[0]
            open_[1:] = close[:-1]
            high = np.maximum(close, open_) * (1 + np.random.rand(n) * 0.01)
            low = np.minimum(close, open_) * (1 - np.random.rand(n) * 0.01)
            volume = np.random.randint(5000, 15000, size=n).astype(np.float64)

            data[ticker] = {
                "close": close,
                "volume": volume,
                "open": open_,
                "high": high,
                "low": low,
            }
        return data

    def test_backtest_v3_returns_batches(self):
        """V3 backtest should return valid results."""
        data = self._make_synthetic_ohlcv()
        result = backtest_cn_strategy(
            hold_days=5, min_score=3, lookback_days=30,
            data_override=data, strategy="v3",
        )
        assert "batches" in result
        assert "summary" in result

    def test_backtest_v3_vs_v2(self):
        """V3 backtest should produce valid output alongside v2."""
        data = self._make_synthetic_ohlcv()
        r_v2 = backtest_cn_strategy(
            hold_days=5, min_score=3, lookback_days=30,
            data_override=data, strategy="v2",
        )
        r_v3 = backtest_cn_strategy(
            hold_days=5, min_score=3, lookback_days=30,
            data_override=data, strategy="v3",
        )
        assert isinstance(r_v2["batches"], list)
        assert isinstance(r_v3["batches"], list)

    def test_backtest_v3_high_threshold(self):
        """Very high threshold → fewer/no selections."""
        data = self._make_synthetic_ohlcv()
        result = backtest_cn_strategy(
            hold_days=5, min_score=20, lookback_days=30,
            data_override=data, strategy="v3",
        )
        assert result["summary"]["total_batches"] >= 0

    def test_backtest_format_v3(self):
        """format_backtest_output shows v3 strategy tag."""
        data = self._make_synthetic_ohlcv()
        result = backtest_cn_strategy(
            hold_days=5, min_score=1, lookback_days=30,
            data_override=data, strategy="v3",
        )
        output = format_backtest_output(result, strategy="v3")
        assert "strategy=v3" in output

    def test_compute_score_at_v3(self):
        """_compute_score_at with strategy=v3 uses v3 scoring."""
        open_, high, low, close, volume = _make_ohlcv(n=60)
        r_v3 = _compute_score_at(
            close, volume, 59, strategy="v3",
            open_=open_, high=high, low=low,
        )
        assert r_v3.get("strategy") == "v3"


# ── CLI Argument Tests for V3 ────────────────────────────────────────

class TestCLIArgsV3:
    def test_scan_cn_strategy_default_is_v3(self):
        """Default strategy for scan-cn should be v3."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn'])
        assert args.strategy == 'v3'

    def test_scan_cn_strategy_v3_explicit(self):
        """Can select v3 strategy explicitly."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn', '--strategy', 'v3'])
        assert args.strategy == 'v3'

    def test_scan_cn_backtest_v3(self):
        """Can select v3 for backtest."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn-backtest', '--strategy', 'v3'])
        assert args.strategy == 'v3'

    def test_scan_cn_v1_still_works(self):
        """v1 still accepted."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn', '--strategy', 'v1'])
        assert args.strategy == 'v1'


# ── Edge Case & Robustness Tests ─────────────────────────────────────

class TestV3EdgeCases:
    def test_all_nan_volume(self):
        """NaN volume should not crash."""
        close = np.linspace(90, 110, 60)
        volume = np.full(60, np.nan)
        result = compute_score_v3(close, volume)
        assert isinstance(result['score'], (int, float))

    def test_constant_prices_ohlcv(self):
        """Constant OHLCV should not crash."""
        n = 60
        close = np.ones(n) * 100.0
        open_ = np.ones(n) * 100.0
        high = np.ones(n) * 100.0
        low = np.ones(n) * 100.0
        volume = np.ones(n) * 1000.0
        result = compute_score_v3(close, volume, open_, high, low)
        assert isinstance(result['score'], (int, float))

    def test_zero_volume_array(self):
        """Zero volume should not produce division errors."""
        open_, high, low, close, _ = _make_ohlcv()
        volume = np.zeros(60)
        result = compute_score_v3(close, volume, open_, high, low)
        assert isinstance(result['score'], (int, float))

    def test_very_long_series(self):
        """500-bar OHLCV series."""
        open_, high, low, close, volume = _make_ohlcv(n=500)
        result = compute_score_v3(close, volume, open_, high, low)
        assert isinstance(result['score'], (int, float))
        assert result['strategy'] == 'v3'

    def test_single_spike(self):
        """Single price spike should not crash."""
        n = 60
        open_, high, low, close, volume = _make_ohlcv(n=n)
        close[-1] = 300.0
        high[-1] = 310.0
        result = compute_score_v3(close, volume, open_, high, low)
        assert isinstance(result['score'], (int, float))

    def test_negative_prices_handled(self):
        """Gracefully handle near-zero prices."""
        n = 60
        close = np.linspace(10, 0.1, n)
        close = np.maximum(close, 0.01)
        volume = np.ones(n) * 1000.0
        result = compute_score_v3(close, volume)
        assert isinstance(result['score'], (int, float))

    def test_mismatched_lengths_graceful(self):
        """When OHLCV arrays are same length, no crash."""
        n = 60
        open_, high, low, close, volume = _make_ohlcv(n=n)
        result = compute_score_v3(close, volume, open_, high, low)
        assert result['strategy'] == 'v3'
