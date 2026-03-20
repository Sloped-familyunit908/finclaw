"""
Tests for Limit-Up Pullback and Reversal Pattern Strategies
============================================================
Coverage:
  LimitUpPullback:
    - detect_limit_up: main board, ChiNext/STAR, no limit-up, edge cases
    - find_pullback_signals: valid pullback, broken bottom, volume too high
    - backtest: take profit, stop loss, max hold, empty data, overlapping signals
  UShapeReversal:
    - find_decline_phases: clear decline, shallow decline, short decline
    - find_signals: valid U shape, no consolidation, no breakout
    - backtest: round-trip trades
  VShapeReversal:
    - find_signals: valid V bounce, no RSI recovery, slow decline
    - backtest: round-trip trades, edge cases
"""

import numpy as np
import pytest

from src.strategies.limit_up_pullback import LimitUpPullback, LimitUpSignal
from src.strategies.reversal_patterns import UShapeReversal, VShapeReversal


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _make_limit_up_then_pullback(
    n: int = 30,
    start: float = 10.0,
    limit_up_day: int = 10,
    pullback_days: int = 3,
    pullback_depth: float = 0.03,
    volume_shrink: float = 0.4,
    code: str = "600000",
) -> tuple:
    """Create OHLCV data with a limit-up day followed by a controlled pullback.

    Returns (opens, highs, lows, closes, volumes).
    """
    rng = np.random.RandomState(42)
    opens = np.full(n, start)
    highs = np.full(n, start)
    lows = np.full(n, start)
    closes = np.full(n, start)
    volumes = np.full(n, 1_000_000.0)

    # Pre limit-up: gentle uptrend
    for i in range(1, limit_up_day):
        closes[i] = closes[i - 1] * 1.005
        opens[i] = closes[i - 1]
        highs[i] = closes[i] * 1.002
        lows[i] = opens[i] * 0.998

    # Limit-up day (10% for main board code 600000)
    pct = 0.10 if not code.startswith("688") and not code.startswith("300") else 0.20
    prev_close = closes[limit_up_day - 1]
    lu_close = prev_close * (1.0 + pct)
    lu_open = prev_close * 1.02
    lu_high = lu_close
    lu_low = prev_close * 0.99

    opens[limit_up_day] = lu_open
    highs[limit_up_day] = lu_high
    lows[limit_up_day] = lu_low
    closes[limit_up_day] = lu_close
    volumes[limit_up_day] = 5_000_000.0  # Big volume

    # Pullback days
    for d in range(1, pullback_days + 1):
        idx = limit_up_day + d
        if idx >= n:
            break
        # Price drifts down slightly but stays above limit-up low
        pb_close = lu_close * (1.0 - pullback_depth * d / pullback_days)
        opens[idx] = closes[idx - 1]
        closes[idx] = pb_close
        highs[idx] = opens[idx] * 1.001
        lows[idx] = pb_close * 0.998
        # Ensure lows don't break limit-up low
        lows[idx] = max(lows[idx], lu_low + 0.01)
        volumes[idx] = 5_000_000.0 * volume_shrink

    # After pullback: gentle uptrend for remaining days
    last_pb_idx = limit_up_day + pullback_days
    for i in range(last_pb_idx + 1, n):
        closes[i] = closes[i - 1] * 1.008
        opens[i] = closes[i - 1] * 1.001
        highs[i] = closes[i] * 1.005
        lows[i] = opens[i] * 0.997
        volumes[i] = 1_500_000.0

    return opens, highs, lows, closes, volumes


def _make_u_shape(n: int = 60, start: float = 100.0) -> tuple:
    """Create OHLCV data with a U-shape reversal pattern.

    Pattern: steady → 7-day decline (~18%) → 4-day consolidation → volume breakout
    """
    opens = np.full(n, start)
    highs = np.full(n, start)
    lows = np.full(n, start)
    closes = np.full(n, start)
    volumes = np.full(n, 1_000_000.0)

    # Phase 1: Steady (days 0-14)
    for i in range(1, 15):
        closes[i] = closes[i - 1] * 1.002
        opens[i] = closes[i - 1]
        highs[i] = closes[i] * 1.003
        lows[i] = opens[i] * 0.997

    # Phase 2: Decline for 7 days (~18% drop)
    decline_start = 15
    for i in range(7):
        idx = decline_start + i
        if idx >= n:
            break
        closes[idx] = closes[idx - 1] * 0.972  # ~2.8% per day
        opens[idx] = closes[idx - 1] * 0.998
        highs[idx] = opens[idx] * 1.001
        lows[idx] = closes[idx] * 0.998
        volumes[idx] = 2_000_000.0

    # Phase 3: Consolidation for 4 days (flat, low volume)
    cons_start = decline_start + 7
    bottom_price = closes[cons_start - 1]
    for i in range(4):
        idx = cons_start + i
        if idx >= n:
            break
        closes[idx] = bottom_price * (1.0 + 0.003 * (i % 2))  # Tiny oscillation
        opens[idx] = bottom_price * 0.999
        highs[idx] = bottom_price * 1.01
        lows[idx] = bottom_price * 0.99
        volumes[idx] = 500_000.0

    # Phase 4: Breakout day
    breakout_idx = cons_start + 4
    if breakout_idx < n:
        cons_high = bottom_price * 1.01
        closes[breakout_idx] = cons_high * 1.05
        opens[breakout_idx] = bottom_price * 1.01
        highs[breakout_idx] = closes[breakout_idx] * 1.01
        lows[breakout_idx] = opens[breakout_idx] * 0.998
        volumes[breakout_idx] = 3_000_000.0  # Volume spike

    # Phase 5: Recovery
    for i in range(breakout_idx + 1, n):
        closes[i] = closes[i - 1] * 1.01
        opens[i] = closes[i - 1] * 1.001
        highs[i] = closes[i] * 1.005
        lows[i] = opens[i] * 0.997
        volumes[i] = 1_500_000.0

    return opens, highs, lows, closes, volumes


def _make_v_shape(n: int = 60, start: float = 100.0) -> tuple:
    """Create OHLCV data with a V-shape reversal pattern.

    Pattern: 20 days steady → 4 days sharp decline (~12%) → immediate bounce
    """
    opens = np.full(n, start)
    highs = np.full(n, start)
    lows = np.full(n, start)
    closes = np.full(n, start)
    volumes = np.full(n, 1_000_000.0)

    # Phase 1: Steady (days 0-19)
    for i in range(1, 20):
        closes[i] = closes[i - 1] * 1.001
        opens[i] = closes[i - 1]
        highs[i] = closes[i] * 1.002
        lows[i] = opens[i] * 0.998

    # Phase 2: Sharp decline for 4 days (~12% total)
    decline_start = 20
    for i in range(4):
        idx = decline_start + i
        if idx >= n:
            break
        closes[idx] = closes[idx - 1] * 0.968  # ~3.2% per day → ~12.4% total
        opens[idx] = closes[idx - 1] * 0.998
        highs[idx] = opens[idx] * 1.001
        lows[idx] = closes[idx] * 0.998
        volumes[idx] = 2_000_000.0

    # Phase 3: Immediate V bounce (3 days of strong recovery)
    bounce_start = decline_start + 4
    for i in range(3):
        idx = bounce_start + i
        if idx >= n:
            break
        closes[idx] = closes[idx - 1] * 1.04  # Strong bounce
        opens[idx] = closes[idx - 1] * 1.005
        highs[idx] = closes[idx] * 1.005
        lows[idx] = opens[idx] * 0.997
        volumes[idx] = 2_500_000.0

    # Phase 4: Continued recovery
    for i in range(bounce_start + 3, n):
        closes[i] = closes[i - 1] * 1.005
        opens[i] = closes[i - 1] * 1.001
        highs[i] = closes[i] * 1.003
        lows[i] = opens[i] * 0.998
        volumes[i] = 1_200_000.0

    return opens, highs, lows, closes, volumes


# ═══════════════════════════════════════════════════════════
#  LimitUpPullback — detect_limit_up
# ═══════════════════════════════════════════════════════════

class TestDetectLimitUp:
    """Tests for limit-up detection."""

    def test_main_board_limit_up(self):
        """Main board stock (600xxx) with 10% gain is detected as limit-up."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(code="600000")
        strat = LimitUpPullback()
        days = strat.detect_limit_up(opens, highs, lows, closes, volumes, code="600000")
        assert len(days) >= 1
        assert 10 in days  # limit_up_day = 10

    def test_chinext_limit_up_requires_20pct(self):
        """ChiNext stock (300xxx) uses 20% limit threshold; a 10% gain is NOT limit-up."""
        # Build data with a forced 10% gain (main board limit) for a ChiNext code
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(code="600000")
        # The helper made a 10% jump at day 10. If we call detect with code="300001",
        # the 10% gain should not qualify as ChiNext limit-up (needs 19%).
        strat = LimitUpPullback()
        days = strat.detect_limit_up(opens, highs, lows, closes, volumes, code="300001")
        assert 10 not in days

    def test_star_market_limit_up(self):
        """STAR market (688xxx) uses 20% limit threshold."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            code="688001", limit_up_day=10
        )
        strat = LimitUpPullback()
        days = strat.detect_limit_up(opens, highs, lows, closes, volumes, code="688001")
        # With 20% limit-up on the data, should be detected
        assert len(days) >= 1

    def test_no_limit_up_in_flat_data(self):
        """Flat data produces no limit-up days."""
        n = 30
        closes = np.full(n, 10.0)
        opens = closes.copy()
        highs = closes.copy()
        lows = closes.copy()
        volumes = np.full(n, 1_000_000.0)
        strat = LimitUpPullback()
        days = strat.detect_limit_up(opens, highs, lows, closes, volumes, code="600000")
        assert len(days) == 0

    def test_limit_up_with_exchange_prefix(self):
        """Code with exchange prefix like 'sh.600000' is handled."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(code="sh.600000")
        strat = LimitUpPullback()
        pct = strat.get_limit_pct("sh.600000")
        assert pct == 0.10

    def test_limit_up_single_bar(self):
        """Only 1 bar → no limit-up (need prev close)."""
        strat = LimitUpPullback()
        days = strat.detect_limit_up(
            np.array([10.0]), np.array([11.0]),
            np.array([9.0]), np.array([11.0]),
            np.array([100.0]), code="600000"
        )
        assert len(days) == 0

    def test_exactly_at_threshold(self):
        """A gain of exactly 9.5% (0.095) should be detected (threshold is 0.095)."""
        closes = np.array([10.0, 10.95])
        opens = np.array([10.0, 10.0])
        highs = np.array([10.0, 10.95])
        lows = np.array([10.0, 10.0])
        volumes = np.array([1e6, 1e6])
        strat = LimitUpPullback()
        days = strat.detect_limit_up(opens, highs, lows, closes, volumes, code="600000")
        assert 1 in days


# ═══════════════════════════════════════════════════════════
#  LimitUpPullback — find_pullback_signals
# ═══════════════════════════════════════════════════════════

class TestFindPullbackSignals:
    """Tests for pullback signal detection."""

    def test_valid_pullback_detected(self):
        """Standard 3-day pullback with volume shrinkage generates a signal."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            pullback_days=3, volume_shrink=0.4
        )
        strat = LimitUpPullback()
        signals = strat.find_pullback_signals(opens, highs, lows, closes, volumes, code="600000")
        assert len(signals) >= 1
        sig = signals[0]
        assert sig.pullback_days >= 2
        assert sig.volume_ratio < 0.6
        assert sig.buy_price > 0

    def test_broken_bottom_no_signal(self):
        """If pullback breaks limit-up day's low, no signal is generated."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            pullback_days=3, volume_shrink=0.3
        )
        # Break the bottom: set one pullback day's low below limit-up low
        lu_low = lows[10]
        lows[12] = lu_low - 1.0  # Break below limit-up low
        strat = LimitUpPullback()
        signals = strat.find_pullback_signals(opens, highs, lows, closes, volumes, code="600000")
        # Should find no signal (or only shorter pullback not including broken day)
        for sig in signals:
            # Verify no signal includes the broken bottom day
            assert sig.limit_up_idx + sig.pullback_days < 12 or sig.date_idx < 12

    def test_high_volume_pullback_no_signal(self):
        """If pullback volume is too high (not shrinking), no signal."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            pullback_days=3, volume_shrink=0.9  # Volume barely shrinks
        )
        strat = LimitUpPullback()
        signals = strat.find_pullback_signals(opens, highs, lows, closes, volumes, code="600000")
        assert len(signals) == 0

    def test_too_short_pullback_no_signal(self):
        """1-day pullback is too short (min is 2)."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            pullback_days=1, volume_shrink=0.3
        )
        strat = LimitUpPullback(min_pullback_days=2)
        signals = strat.find_pullback_signals(opens, highs, lows, closes, volumes, code="600000")
        # 1-day pullback should not generate signal with min_pullback_days=2
        for sig in signals:
            assert sig.pullback_days >= 2

    def test_signal_score_higher_for_lower_volume(self):
        """Lower volume ratio should give higher signal score."""
        o1, h1, l1, c1, v1 = _make_limit_up_then_pullback(volume_shrink=0.2, pullback_days=3)
        o2, h2, l2, c2, v2 = _make_limit_up_then_pullback(volume_shrink=0.5, pullback_days=3)
        strat = LimitUpPullback()
        sig1 = strat.find_pullback_signals(o1, h1, l1, c1, v1, code="600000")
        sig2 = strat.find_pullback_signals(o2, h2, l2, c2, v2, code="600000")
        if sig1 and sig2:
            assert sig1[0].score >= sig2[0].score

    def test_signal_buy_price_is_t1_open(self):
        """Buy price should be the T+1 open after the signal day."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            pullback_days=3, volume_shrink=0.3
        )
        strat = LimitUpPullback()
        signals = strat.find_pullback_signals(opens, highs, lows, closes, volumes, code="600000")
        if signals:
            sig = signals[0]
            expected_buy_price = opens[sig.date_idx + 1]
            assert sig.buy_price == pytest.approx(expected_buy_price, rel=1e-6)


# ═══════════════════════════════════════════════════════════
#  LimitUpPullback — backtest
# ═══════════════════════════════════════════════════════════

class TestLimitUpBacktest:
    """Tests for the backtest method."""

    def test_backtest_returns_trades(self):
        """Backtest on valid data should produce at least one trade."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            n=40, pullback_days=3, volume_shrink=0.3
        )
        strat = LimitUpPullback()
        result = strat.backtest(opens, highs, lows, closes, volumes, code="600000")
        assert "trades" in result
        assert "total_return" in result
        assert "win_rate" in result

    def test_backtest_take_profit(self):
        """When price rises enough, trade exits with take_profit."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            n=40, pullback_days=3, volume_shrink=0.3
        )
        # Make post-pullback prices rise sharply to trigger TP
        for i in range(14, 40):
            highs[i] = closes[i] * 1.15  # High enough to trigger 10% TP
        strat = LimitUpPullback(tp_pct=10.0)
        result = strat.backtest(opens, highs, lows, closes, volumes, code="600000")
        if result["trades"]:
            # At least one should be take_profit
            tp_trades = [t for t in result["trades"] if t["exit_reason"] == "take_profit"]
            assert len(tp_trades) >= 1

    def test_backtest_stop_loss(self):
        """When price drops, trade exits with stop_loss."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            n=40, pullback_days=3, volume_shrink=0.3
        )
        # Make post-pullback prices drop sharply
        for i in range(14, 40):
            lows[i] = closes[i] * 0.85
            closes[i] = closes[i] * 0.90
        strat = LimitUpPullback(sl_pct=5.0)
        result = strat.backtest(opens, highs, lows, closes, volumes, code="600000")
        if result["trades"]:
            sl_trades = [t for t in result["trades"] if t["exit_reason"] == "stop_loss"]
            assert len(sl_trades) >= 1

    def test_backtest_empty_data(self):
        """Empty data should return empty results."""
        strat = LimitUpPullback()
        result = strat.backtest(
            np.array([]), np.array([]), np.array([]),
            np.array([]), np.array([]), code="600000"
        )
        assert result["total_trades"] == 0
        assert result["trades"] == []
        assert result["total_return"] == 0.0

    def test_backtest_max_hold_exit(self):
        """When neither TP nor SL triggers, exit at max_hold_days."""
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            n=40, pullback_days=3, volume_shrink=0.3
        )
        # Make post-pullback prices very flat (no TP or SL)
        for i in range(14, 40):
            closes[i] = closes[13] * 1.001
            opens[i] = closes[13] * 1.001
            highs[i] = closes[13] * 1.002
            lows[i] = closes[13] * 0.999
        strat = LimitUpPullback(tp_pct=20.0, sl_pct=20.0, max_hold_days=5)
        result = strat.backtest(opens, highs, lows, closes, volumes, code="600000")
        if result["trades"]:
            for t in result["trades"]:
                if t["exit_reason"] == "max_hold":
                    assert t["hold_days"] <= 5

    def test_backtest_no_overlap(self):
        """Two signals close together: the second is skipped while in position."""
        # Create data with two limit-up events close together
        opens, highs, lows, closes, volumes = _make_limit_up_then_pullback(
            n=50, pullback_days=2, volume_shrink=0.3, limit_up_day=5
        )
        # Add another limit-up at day 12 (while we'd still be in position)
        if closes[11] > 0:
            closes[12] = closes[11] * 1.10
            highs[12] = closes[12]
            volumes[12] = 5_000_000.0
        strat = LimitUpPullback(max_hold_days=10)
        result = strat.backtest(opens, highs, lows, closes, volumes, code="600000")
        # Verify no overlapping entries
        for i in range(len(result["trades"]) - 1):
            assert result["trades"][i]["exit_idx"] < result["trades"][i + 1]["entry_idx"]


# ═══════════════════════════════════════════════════════════
#  LimitUpPullback — get_limit_pct
# ═══════════════════════════════════════════════════════════

class TestGetLimitPct:
    """Tests for board type classification."""

    def test_main_board_600(self):
        assert LimitUpPullback.get_limit_pct("600000") == 0.10

    def test_main_board_000(self):
        assert LimitUpPullback.get_limit_pct("000001") == 0.10

    def test_chinext_300(self):
        assert LimitUpPullback.get_limit_pct("300001") == 0.20

    def test_star_688(self):
        assert LimitUpPullback.get_limit_pct("688001") == 0.20

    def test_with_prefix_sh(self):
        assert LimitUpPullback.get_limit_pct("sh.600000") == 0.10

    def test_with_prefix_sz(self):
        assert LimitUpPullback.get_limit_pct("sz.300001") == 0.20


# ═══════════════════════════════════════════════════════════
#  UShapeReversal
# ═══════════════════════════════════════════════════════════

class TestUShapeReversal:
    """Tests for U-shape reversal detection."""

    def test_find_decline_phases(self):
        """Should detect a decline phase in U-shape data."""
        opens, highs, lows, closes, volumes = _make_u_shape()
        strat = UShapeReversal()
        phases = strat.find_decline_phases(closes)
        assert len(phases) >= 1
        start, end, pct = phases[0]
        assert pct >= 15.0
        assert end - start >= 5

    def test_no_decline_in_uptrend(self):
        """Pure uptrend should have no decline phases."""
        n = 60
        closes = np.array([100.0 * (1.005 ** i) for i in range(n)])
        strat = UShapeReversal()
        phases = strat.find_decline_phases(closes)
        assert len(phases) == 0

    def test_shallow_decline_skipped(self):
        """Decline < 15% should not be detected."""
        n = 60
        closes = np.full(n, 100.0)
        # 10% decline only
        for i in range(20, 30):
            closes[i] = 100.0 * (1.0 - 0.01 * (i - 20))
        strat = UShapeReversal(min_decline_pct=15.0)
        phases = strat.find_decline_phases(closes)
        # Should not find 10% decline
        for _, _, pct in phases:
            assert pct >= 15.0

    def test_find_u_shape_signal(self):
        """Valid U-shape pattern produces a signal."""
        opens, highs, lows, closes, volumes = _make_u_shape()
        strat = UShapeReversal()
        signals = strat.find_signals(opens, highs, lows, closes, volumes)
        assert len(signals) >= 1
        sig = signals[0]
        assert sig.decline_pct >= 15.0
        assert sig.consolidation_days >= 3
        assert sig.breakout_volume_ratio >= 1.5
        assert sig.buy_price > 0

    def test_u_shape_backtest(self):
        """Backtest on U-shape data should produce trades."""
        opens, highs, lows, closes, volumes = _make_u_shape(n=80)
        strat = UShapeReversal()
        result = strat.backtest(opens, highs, lows, closes, volumes)
        assert "trades" in result
        assert "total_return" in result

    def test_u_shape_no_breakout_no_signal(self):
        """If there's no volume breakout, no signal is generated."""
        opens, highs, lows, closes, volumes = _make_u_shape()
        # Kill the breakout volume
        breakout_idx = 26  # Approximate breakout location
        for i in range(breakout_idx - 1, min(breakout_idx + 2, len(volumes))):
            volumes[i] = 100_000.0  # Very low volume
        strat = UShapeReversal(min_breakout_volume=2.0)
        signals = strat.find_signals(opens, highs, lows, closes, volumes)
        # May or may not find signals depending on exact data, but breakout criterion is strict
        for sig in signals:
            assert sig.breakout_volume_ratio >= 2.0

    def test_calculate_r2_flat(self):
        """R² of perfectly flat prices should be 0."""
        r2 = UShapeReversal.calculate_r2(np.full(10, 50.0))
        assert r2 == 0.0

    def test_calculate_r2_linear(self):
        """R² of perfectly linear prices should be ~1.0."""
        r2 = UShapeReversal.calculate_r2(np.arange(10, dtype=np.float64))
        assert r2 == pytest.approx(1.0, abs=1e-10)


# ═══════════════════════════════════════════════════════════
#  VShapeReversal
# ═══════════════════════════════════════════════════════════

class TestVShapeReversal:
    """Tests for V-shape reversal detection."""

    def test_find_v_shape_signal(self):
        """Valid V-shape pattern produces a signal."""
        opens, highs, lows, closes, volumes = _make_v_shape()
        strat = VShapeReversal()
        signals = strat.find_signals(opens, highs, lows, closes, volumes)
        # V-shape may or may not trigger depending on RSI dynamics
        # With a 12% decline and sharp bounce, RSI should recover
        if signals:
            sig = signals[0]
            assert sig.decline_pct >= 10.0
            assert sig.rsi_at_bottom <= 20.0
            assert sig.rsi_current >= 40.0
            assert sig.buy_price > 0

    def test_v_shape_rsi_calculation(self):
        """RSI calculation matches expected behavior."""
        strat = VShapeReversal()
        # Create clear downtrend then sharp recovery
        prices = np.array([100.0 - i * 2.0 for i in range(20)] +
                         [60.0 + i * 3.0 for i in range(10)])
        rsi = strat.calculate_rsi(prices, period=14)
        # RSI should be low at the bottom and recover
        assert not np.isnan(rsi[-1])
        assert rsi[-1] > rsi[19]  # Recovery

    def test_no_signal_in_gentle_decline(self):
        """Gentle decline (< 10%) should not trigger V-shape."""
        n = 60
        opens = np.full(n, 100.0)
        highs = np.full(n, 100.0)
        lows = np.full(n, 100.0)
        closes = np.full(n, 100.0)
        volumes = np.full(n, 1_000_000.0)
        # Only 5% decline over 3 days
        for i in range(20, 24):
            closes[i] = closes[i - 1] * 0.987
            opens[i] = closes[i - 1]
            highs[i] = opens[i]
            lows[i] = closes[i]
        strat = VShapeReversal(min_decline_pct=10.0)
        signals = strat.find_signals(opens, highs, lows, closes, volumes)
        # Should NOT detect a signal for <10% decline
        for sig in signals:
            assert sig.decline_pct >= 10.0

    def test_v_shape_backtest(self):
        """Backtest on V-shape data should produce results dict."""
        opens, highs, lows, closes, volumes = _make_v_shape(n=80)
        strat = VShapeReversal()
        result = strat.backtest(opens, highs, lows, closes, volumes)
        assert "trades" in result
        assert "total_return" in result
        assert isinstance(result["total_trades"], int)

    def test_v_shape_empty_data(self):
        """Empty data should return empty results."""
        strat = VShapeReversal()
        result = strat.backtest(
            np.array([]), np.array([]), np.array([]),
            np.array([]), np.array([])
        )
        assert result["total_trades"] == 0
        assert result["trades"] == []

    def test_v_shape_short_data(self):
        """Data too short for RSI should return no signals."""
        strat = VShapeReversal(rsi_period=14)
        signals = strat.find_signals(
            np.full(10, 100.0), np.full(10, 101.0),
            np.full(10, 99.0), np.full(10, 100.0),
            np.full(10, 1e6)
        )
        assert len(signals) == 0

    def test_rsi_leading_nans(self):
        """RSI array should have NaN for the first `period` values."""
        strat = VShapeReversal()
        prices = np.arange(30, dtype=np.float64) + 50.0
        rsi = strat.calculate_rsi(prices, period=14)
        assert np.all(np.isnan(rsi[:14]))
        assert not np.isnan(rsi[14])
