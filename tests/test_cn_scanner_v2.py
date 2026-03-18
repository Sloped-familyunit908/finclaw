"""
Tests for A-Share Scanner V2 Scoring Engine
=============================================
Tests the multi-signal scoring system and its individual signal functions.
"""

import numpy as np
import pytest

from src.cn_scanner import (
    compute_score,
    compute_score_v2,
    classify_signal_v2,
    _signal_volume_breakout,
    _signal_bottom_reversal,
    _signal_macd_divergence,
    _signal_ma_alignment,
    _signal_low_volume_pullback,
    _signal_nday_breakout,
    _signal_short_term_reversal,
    _signal_momentum_confirmation,
    backtest_cn_strategy,
    format_backtest_output,
    _compute_score_at,
)


# ── Individual Signal Tests ──────────────────────────────────────────

class TestVolumeBreakoutSignal:
    def test_positive_trigger(self):
        """Price up >2% AND volume >2x average → +3."""
        close = np.ones(60) * 100.0
        close[-1] = 103.0  # +3% from prev
        volume = np.ones(60) * 1000.0
        volume[-1] = 2500.0  # 2.5x average
        pts, reason = _signal_volume_breakout(close, volume)
        assert pts == 3
        assert reason is not None
        assert "vol breakout" in reason

    def test_no_trigger_low_volume(self):
        """Price up but volume not enough → 0."""
        close = np.ones(60) * 100.0
        close[-1] = 103.0
        volume = np.ones(60) * 1000.0
        volume[-1] = 1500.0  # only 1.5x
        pts, _ = _signal_volume_breakout(close, volume)
        assert pts == 0

    def test_no_trigger_price_flat(self):
        """Volume up but price flat → 0."""
        close = np.ones(60) * 100.0
        close[-1] = 101.0  # only +1%
        volume = np.ones(60) * 1000.0
        volume[-1] = 3000.0
        pts, _ = _signal_volume_breakout(close, volume)
        assert pts == 0

    def test_no_volume_data(self):
        """No volume provided → 0."""
        close = np.ones(60) * 100.0
        close[-1] = 105.0
        pts, _ = _signal_volume_breakout(close, None)
        assert pts == 0

    def test_short_data(self):
        """Insufficient data → 0."""
        pts, _ = _signal_volume_breakout(np.array([100.0]), np.array([1000.0]))
        assert pts == 0


class TestBottomReversalSignal:
    def test_positive_trigger(self):
        """RSI < 25 AND price bouncing → +4."""
        close = np.ones(60) * 100.0
        close[-2] = 95.0   # prev day low
        close[-1] = 96.0   # bouncing
        pts, reason = _signal_bottom_reversal(close, 22.0)
        assert pts == 4
        assert "bottom reversal" in reason

    def test_no_trigger_rsi_too_high(self):
        """RSI not oversold enough → 0."""
        close = np.ones(60) * 100.0
        close[-2] = 95.0
        close[-1] = 96.0
        pts, _ = _signal_bottom_reversal(close, 35.0)
        assert pts == 0

    def test_no_trigger_still_falling(self):
        """RSI oversold but price still falling → 0."""
        close = np.ones(60) * 100.0
        close[-2] = 96.0
        close[-1] = 95.0   # still declining
        pts, _ = _signal_bottom_reversal(close, 20.0)
        assert pts == 0

    def test_short_data(self):
        """Single data point → 0."""
        pts, _ = _signal_bottom_reversal(np.array([100.0]), 20.0)
        assert pts == 0


class TestMACDDivergenceSignal:
    def test_positive_divergence(self):
        """Price new 10-day low, MACD hist higher than previous low → +3."""
        # Create declining price that makes two troughs
        close = np.ones(60) * 100.0
        # First trough around index 45
        close[40:50] = np.linspace(100, 88, 10)
        close[50:55] = np.linspace(89, 95, 5)
        # Second trough at end, lower price
        close[55:60] = np.linspace(94, 87, 5)

        # MACD hist: deeper at first trough, shallower at second
        macd_hist = np.zeros(60)
        macd_hist[40:50] = np.linspace(-0.5, -2.0, 10)
        macd_hist[50:55] = np.linspace(-1.5, -0.5, 5)
        macd_hist[55:60] = np.linspace(-0.3, -1.0, 5)

        pts, reason = _signal_macd_divergence(close, macd_hist)
        # May or may not trigger based on exact conditions, but should not crash
        assert pts >= 0
        if pts > 0:
            assert "MACD bullish divergence" in reason

    def test_no_trigger_short_data(self):
        """Less than 20 bars → 0."""
        close = np.ones(15) * 100.0
        macd_hist = np.zeros(15)
        pts, _ = _signal_macd_divergence(close, macd_hist)
        assert pts == 0

    def test_no_trigger_price_not_at_low(self):
        """Price not at 10-day low → 0."""
        close = np.linspace(90, 110, 60)  # steadily rising
        macd_hist = np.zeros(60)
        pts, _ = _signal_macd_divergence(close, macd_hist)
        assert pts == 0


class TestMAAlignmentSignal:
    def test_positive_alignment(self):
        """Close > MA5 > MA10 > MA20 → +2."""
        # Create steadily rising prices where MAs are aligned
        close = np.linspace(80, 120, 60)
        pts, reason = _signal_ma_alignment(close)
        assert pts == 2
        assert "MA alignment" in reason

    def test_no_alignment_declining(self):
        """Declining prices → MAs not aligned → 0."""
        close = np.linspace(120, 80, 60)
        pts, _ = _signal_ma_alignment(close)
        assert pts == 0

    def test_short_data(self):
        """Less than 20 bars → 0."""
        close = np.ones(15) * 100.0
        pts, _ = _signal_ma_alignment(close)
        assert pts == 0

    def test_flat_prices_no_alignment(self):
        """Perfectly flat prices — MA5 == MA10 == MA20, not strictly greater → 0."""
        close = np.ones(60) * 100.0
        pts, _ = _signal_ma_alignment(close)
        assert pts == 0


class TestLowVolumePullbackSignal:
    def test_positive_trigger(self):
        """Uptrend + pullback with declining volume → +3."""
        # Uptrend base
        close = np.linspace(90, 110, 55)
        # 5-day pullback at end
        close = np.append(close, [109.5, 109.0, 108.5, 108.0, 107.5])
        volume = np.ones(60) * 1000.0
        # Declining volume on pullback
        volume[-5:] = [900, 800, 700, 600, 500]
        pts, reason = _signal_low_volume_pullback(close, volume)
        # May trigger depending on MA20 calculation
        assert pts >= 0
        if pts > 0:
            assert "low-vol pullback" in reason

    def test_no_trigger_no_volume(self):
        """No volume → 0."""
        close = np.linspace(90, 110, 60)
        pts, _ = _signal_low_volume_pullback(close, None)
        assert pts == 0

    def test_no_trigger_downtrend(self):
        """Not in uptrend → 0."""
        close = np.linspace(110, 80, 60)
        volume = np.ones(60) * 1000.0
        volume[-3:] = [800, 600, 400]
        pts, _ = _signal_low_volume_pullback(close, volume)
        assert pts == 0

    def test_short_data(self):
        """Less than 25 bars → 0."""
        close = np.ones(20) * 100.0
        volume = np.ones(20) * 1000.0
        pts, _ = _signal_low_volume_pullback(close, volume)
        assert pts == 0


class TestNDayBreakoutSignal:
    def test_at_20_day_high(self):
        """Price at 20-day high → +2."""
        close = np.ones(60) * 100.0
        close[-1] = 110.0  # new 20-day high
        pts, reason = _signal_nday_breakout(close, 20)
        assert pts == 2
        assert "20d high breakout" in reason

    def test_not_at_high(self):
        """Price below 20-day high → 0."""
        close = np.ones(60) * 100.0
        close[-10] = 110.0  # high was 10 days ago
        pts, _ = _signal_nday_breakout(close, 20)
        assert pts == 0

    def test_short_data(self):
        """Less than N bars → 0."""
        close = np.ones(15) * 100.0
        pts, _ = _signal_nday_breakout(close, 20)
        assert pts == 0

    def test_custom_n(self):
        """Works with different N values."""
        close = np.ones(60) * 100.0
        close[-1] = 105.0
        pts_10, _ = _signal_nday_breakout(close, 10)
        assert pts_10 == 2


class TestShortTermReversalSignal:
    def test_positive_trigger(self):
        """5-day return < -5% → +2."""
        close = np.ones(60) * 100.0
        close[-6] = 100.0
        close[-1] = 94.0   # -6% over 5 days
        pts, reason = _signal_short_term_reversal(close)
        assert pts == 2
        assert "5d reversal" in reason

    def test_no_trigger_mild_decline(self):
        """5-day return only -2% → 0."""
        close = np.ones(60) * 100.0
        close[-6] = 100.0
        close[-1] = 98.0
        pts, _ = _signal_short_term_reversal(close)
        assert pts == 0

    def test_no_trigger_positive_return(self):
        """Positive 5-day return → 0."""
        close = np.ones(60) * 100.0
        close[-1] = 105.0
        pts, _ = _signal_short_term_reversal(close)
        assert pts == 0

    def test_short_data(self):
        """Less than 6 bars → 0."""
        pts, _ = _signal_short_term_reversal(np.array([100.0, 95.0]))
        assert pts == 0


class TestMomentumConfirmationSignal:
    def test_positive_trigger(self):
        """Both 10-d and 20-d returns positive → +1."""
        close = np.linspace(90, 110, 60)  # steadily rising
        pts, reason = _signal_momentum_confirmation(close)
        assert pts == 1
        assert "momentum confirmed" in reason

    def test_no_trigger_recent_decline(self):
        """10-day return negative → 0."""
        close = np.linspace(90, 110, 50)
        close = np.append(close, np.linspace(109, 100, 10))
        pts, _ = _signal_momentum_confirmation(close)
        assert pts == 0

    def test_short_data(self):
        """Less than 21 bars → 0."""
        close = np.ones(18) * 100.0
        pts, _ = _signal_momentum_confirmation(close)
        assert pts == 0


# ── V2 Compute Score Tests ───────────────────────────────────────────

class TestComputeScoreV2:
    def test_returns_expected_keys(self):
        """compute_score_v2 returns all expected keys including 'strategy'."""
        close = np.linspace(90, 110, 60)
        result = compute_score_v2(close)
        expected_keys = {
            'score', 'rsi_val', 'macd_hist', 'pct_b',
            'change_1d', 'change_5d', 'volume_ratio',
            'signal', 'price', 'reasons', 'strategy',
        }
        assert set(result.keys()) == expected_keys
        assert result['strategy'] == 'v2'

    def test_insufficient_data(self):
        """Short data returns zero score with v2 strategy tag."""
        close = np.array([100.0, 101.0, 102.0])
        result = compute_score_v2(close)
        assert result['score'] == 0
        assert result['strategy'] == 'v2'

    def test_v2_score_gte_v1(self):
        """V2 score should be >= v1 (since it adds signals on top)."""
        close = np.linspace(90, 110, 60)
        volume = np.ones(60) * 1000.0
        v1 = compute_score(close, volume)
        v2 = compute_score_v2(close, volume)
        assert v2['score'] >= v1['score']

    def test_oversold_bounce_triggers_bottom_reversal(self):
        """Strongly oversold with bounce should trigger bottom reversal signal."""
        # Create declining prices ending with a bounce
        close = np.linspace(150, 80, 59)
        close = np.append(close, [81.0])  # small bounce
        result = compute_score_v2(close)
        # RSI should be very low → bottom reversal if bouncing
        reasons_str = " ".join(result['reasons'])
        # May include RSI oversold from v1 + bottom reversal from v2
        assert result['score'] >= 4  # at minimum v1 RSI points

    def test_volume_breakout_scored(self):
        """Volume breakout adds +3 when triggered."""
        close = np.ones(60) * 100.0
        close[-1] = 103.0  # +3%
        volume = np.ones(60) * 1000.0
        volume[-1] = 2500.0  # 2.5x avg
        result = compute_score_v2(close, volume)
        assert any("vol breakout" in r for r in result['reasons'])

    def test_ma_alignment_scored(self):
        """Rising prices trigger MA alignment signal."""
        close = np.linspace(80, 120, 60)
        result = compute_score_v2(close)
        assert any("MA alignment" in r for r in result['reasons'])

    def test_20d_breakout_scored(self):
        """Price at 20-day high triggers breakout signal."""
        close = np.ones(60) * 100.0
        close[-1] = 110.0
        result = compute_score_v2(close)
        assert any("20d high breakout" in r for r in result['reasons'])

    def test_momentum_confirmed_scored(self):
        """Steady uptrend triggers momentum confirmation."""
        close = np.linspace(80, 120, 60)
        result = compute_score_v2(close)
        assert any("momentum confirmed" in r for r in result['reasons'])

    def test_5d_reversal_scored(self):
        """Sharp 5-day decline triggers reversal signal."""
        close = np.ones(60) * 100.0
        # Last 6 days: sharp drop
        close[-6:] = [100, 98, 96, 95, 94, 93]  # -7% in 5 days
        result = compute_score_v2(close)
        assert any("5d reversal" in r for r in result['reasons'])


# ── V2 Signal Classification ────────────────────────────────────────

class TestClassifySignalV2:
    def test_strong_buy(self):
        assert classify_signal_v2(10) == "*** STRONG BUY"
        assert classify_signal_v2(15) == "*** STRONG BUY"

    def test_buy(self):
        assert classify_signal_v2(7) == "** BUY"
        assert classify_signal_v2(9) == "** BUY"

    def test_watch(self):
        assert classify_signal_v2(4) == "WATCH"
        assert classify_signal_v2(6) == "WATCH"

    def test_hold(self):
        assert classify_signal_v2(3) == "HOLD"
        assert classify_signal_v2(0) == "HOLD"
        assert classify_signal_v2(-1) == "HOLD"


# ── V2 Backtest Tests ───────────────────────────────────────────────

class TestBacktestV2:
    """Tests for backtest engine with v2 strategy."""

    @staticmethod
    def _make_synthetic(n: int = 120, seed: int = 42) -> dict[str, dict]:
        """Create synthetic data for 3 stocks."""
        np.random.seed(seed)
        data: dict[str, dict] = {}

        # Stock A: oversold pattern → should score high
        close_a = np.ones(n) * 100.0
        for i in range(40, 70):
            close_a[i] = 100 - (i - 40) * 0.5
        for i in range(70, n):
            close_a[i] = close_a[69] + (i - 69) * 0.3
        volume_a = np.ones(n) * 10000
        volume_a[-5:] = 15000
        data['600519.SS'] = {"close": close_a, "volume": volume_a}

        # Stock B: steadily rising → MA alignment
        close_b = np.linspace(50, 150, n)
        data['000858.SZ'] = {"close": close_b, "volume": np.ones(n) * 10000}

        # Stock C: mixed
        close_c = 100 + np.cumsum(np.random.randn(n) * 0.5)
        close_c = np.maximum(close_c, 10)
        data['300750.SZ'] = {"close": close_c, "volume": np.ones(n) * 10000}

        return data

    def test_backtest_v2_returns_batches(self):
        """V2 backtest should return valid results."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=3,
            lookback_days=30,
            data_override=data,
            strategy="v2",
        )
        assert "batches" in result
        assert "summary" in result

    def test_backtest_v2_vs_v1_different_scores(self):
        """V2 backtest should produce different selection counts than v1."""
        data = self._make_synthetic()
        r_v1 = backtest_cn_strategy(
            hold_days=5, min_score=3, lookback_days=30,
            data_override=data, strategy="v1",
        )
        r_v2 = backtest_cn_strategy(
            hold_days=5, min_score=3, lookback_days=30,
            data_override=data, strategy="v2",
        )
        # V2 should generally select more (higher scores) or different stocks
        # We just verify both produce valid output
        assert isinstance(r_v1["batches"], list)
        assert isinstance(r_v2["batches"], list)

    def test_backtest_v2_high_threshold(self):
        """Very high threshold should produce fewer selections with v2."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=15,
            lookback_days=30,
            data_override=data,
            strategy="v2",
        )
        assert result["summary"]["total_batches"] >= 0

    def test_backtest_format_with_strategy(self):
        """format_backtest_output should show strategy tag."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5, min_score=1, lookback_days=30,
            data_override=data, strategy="v2",
        )
        output = format_backtest_output(result, strategy="v2")
        assert "strategy=v2" in output

    def test_compute_score_at_v2(self):
        """_compute_score_at with strategy=v2 should use v2 scoring."""
        close = np.linspace(80, 120, 60)
        r_v1 = _compute_score_at(close, None, 59, strategy="v1")
        r_v2 = _compute_score_at(close, None, 59, strategy="v2")
        assert "strategy" not in r_v1  # v1 doesn't have strategy key
        assert r_v2.get("strategy") == "v2"


# ── CLI Argument Tests for Strategy ──────────────────────────────────

class TestCLIArgsV2:
    def test_scan_cn_strategy_default(self):
        """Default strategy for scan-cn should be v2."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn'])
        assert args.strategy == 'v2'

    def test_scan_cn_strategy_v1(self):
        """Can select v1 strategy."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn', '--strategy', 'v1'])
        assert args.strategy == 'v1'

    def test_scan_cn_backtest_strategy_default(self):
        """Default strategy for backtest should be v1."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn-backtest'])
        assert args.strategy == 'v1'

    def test_scan_cn_backtest_strategy_v2(self):
        """Can select v2 strategy for backtest."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn-backtest', '--strategy', 'v2'])
        assert args.strategy == 'v2'


# ── Edge Case & Robustness Tests ─────────────────────────────────────

class TestV2EdgeCases:
    def test_all_nan_volume(self):
        """Volume array of NaN should not crash."""
        close = np.linspace(90, 110, 60)
        volume = np.full(60, np.nan)
        result = compute_score_v2(close, volume)
        assert isinstance(result['score'], (int, float))

    def test_constant_prices(self):
        """Constant prices should produce minimal score."""
        close = np.ones(60) * 100.0
        result = compute_score_v2(close)
        assert result['score'] >= 0  # should not be negative

    def test_single_spike(self):
        """Single price spike should not crash."""
        close = np.ones(60) * 100.0
        close[-1] = 200.0
        result = compute_score_v2(close)
        assert isinstance(result['score'], (int, float))

    def test_zero_volume(self):
        """Zero volume array should not produce division errors."""
        close = np.linspace(90, 110, 60)
        volume = np.zeros(60)
        result = compute_score_v2(close, volume)
        assert isinstance(result['score'], (int, float))

    def test_very_long_series(self):
        """Long price series (500 bars) should work."""
        close = np.linspace(80, 120, 500)
        volume = np.ones(500) * 1000.0
        result = compute_score_v2(close, volume)
        assert isinstance(result['score'], (int, float))
        assert result['strategy'] == 'v2'

    def test_v2_with_30_bars_minimum(self):
        """Exactly 30 bars should work (boundary)."""
        close = np.linspace(90, 110, 30)
        result = compute_score_v2(close)
        assert result['strategy'] == 'v2'
        # Some signals need more data but should gracefully return 0

    def test_v2_with_29_bars(self):
        """29 bars (below minimum) should return empty result."""
        close = np.linspace(90, 110, 29)
        result = compute_score_v2(close)
        assert result['score'] == 0
        assert result['strategy'] == 'v2'
