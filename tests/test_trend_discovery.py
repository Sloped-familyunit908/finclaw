"""
Tests for Trend Discovery Strategy
===================================
At least 20 test cases covering:
  - Synthetic uptrend → "strong_trend"
  - Sideways / oscillation → "no_trend"
  - V-shape reversal → "emerging_trend"
  - RSI oversold bounce → higher score
  - R² increasing detection
  - should_sell conditions
  - Edge cases (short data, flat prices, etc.)
"""

import numpy as np
import pytest

from src.strategies.trend_discovery import TrendDiscovery, TrendCandidate


# ─── helpers ──────────────────────────────────────────────

def _make_uptrend(n: int = 200, start: float = 50.0, daily_return: float = 0.005, noise: float = 0.002) -> np.ndarray:
    """Generate a clean uptrend with small noise."""
    rng = np.random.RandomState(42)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + daily_return + rng.normal(0, noise)))
    return np.array(prices)


def _make_sideways(n: int = 200, center: float = 100.0, amplitude: float = 5.0) -> np.ndarray:
    """Oscillating series around a center."""
    t = np.arange(n, dtype=np.float64)
    return center + amplitude * np.sin(t * 0.15)


def _make_v_reversal(n: int = 200, start: float = 100.0, bottom_frac: float = 0.5) -> np.ndarray:
    """Strong drop then strong recovery."""
    half = n // 2
    down = np.linspace(start, start * bottom_frac, half)
    up = np.linspace(start * bottom_frac, start * 1.3, n - half)
    return np.concatenate([down, up])


def _make_rsi_oversold_bounce(n: int = 90, start: float = 100.0) -> np.ndarray:
    """Sharp drop (to trigger RSI < 20) then gradual climb.

    Keep total length short so the crash (first 30 bars) falls within
    the 60-day lookback window for rsi_min_60d.
    Recovery rate is moderate (0.3 %/day + noise) so RSI stays under 80
    and the signal classifies as ``strong_trend`` rather than ``mature_trend``.
    """
    # 30 days crashing hard
    crash = np.linspace(start, start * 0.45, 30)
    # then gradual uptrend for the rest — moderate rate to keep RSI < 80
    recovery_len = n - 30
    rng = np.random.RandomState(99)
    recovery = [crash[-1]]
    for _ in range(recovery_len - 1):
        recovery.append(recovery[-1] * (1 + 0.003 + rng.normal(0, 0.008)))
    return np.concatenate([crash, np.array(recovery)])


# ─── fixtures ─────────────────────────────────────────────

@pytest.fixture
def td():
    """Default TrendDiscovery instance."""
    return TrendDiscovery()


# ═══════════════════════════════════════════════════════════
# 1-3: Basic signal classification
# ═══════════════════════════════════════════════════════════

def test_strong_trend_signal(td):
    """RSI dip + strong recovery + volume up should classify as strong_trend."""
    prices = _make_rsi_oversold_bounce(90)
    volumes = np.linspace(1e6, 1.5e6, len(prices))
    result = td.analyze_stock(prices, volumes, code="TEST01", name="UpTrend")
    assert result.signal == "strong_trend"
    assert result.hold_suggestion == "buy_and_hold"
    assert result.score >= 70


def test_sideways_no_trend(td):
    """Oscillating prices should be no_trend."""
    prices = _make_sideways(200)
    volumes = np.ones(200) * 1e6
    result = td.analyze_stock(prices, volumes, code="SIDE01", name="Sideways")
    assert result.signal == "no_trend"


def test_v_reversal_emerging(td):
    """V-shape reversal should be emerging_trend."""
    prices = _make_v_reversal(200, start=100, bottom_frac=0.4)
    volumes = np.ones(200) * 1e6
    result = td.analyze_stock(prices, volumes, code="VREV01", name="VRev")
    assert result.signal in ("emerging_trend", "strong_trend")


# ═══════════════════════════════════════════════════════════
# 4-5: RSI oversold scoring
# ═══════════════════════════════════════════════════════════

def test_rsi_oversold_boosts_score(td):
    """Stock with recent RSI oversold should score higher than one without."""
    # With RSI dip (short data so crash is in the 60d window)
    prices_dip = _make_rsi_oversold_bounce(90)
    vol = np.ones(len(prices_dip)) * 1e6
    result_dip = td.analyze_stock(prices_dip, vol)

    # Pure gentle uptrend (no RSI dip at all)
    prices_up = _make_uptrend(90, start=50, daily_return=0.005)
    vol_up = np.ones(len(prices_up)) * 1e6
    result_up = td.analyze_stock(prices_up, vol_up)

    assert result_dip.score > result_up.score


def test_rsi_min_60d_captures_dip(td):
    """rsi_min_60d should reflect the extreme reading after a crash."""
    prices = _make_rsi_oversold_bounce(90)
    vol = np.ones(len(prices)) * 1e6
    result = td.analyze_stock(prices, vol)
    assert result.rsi_min_60d < 20


# ═══════════════════════════════════════════════════════════
# 6-8: R² calculation
# ═══════════════════════════════════════════════════════════

def test_r2_perfect_linear():
    """Perfect linear series → R² = 1.0."""
    prices = np.linspace(10, 50, 60)
    r2 = TrendDiscovery.calculate_r2(prices, 60)
    assert abs(r2 - 1.0) < 1e-8


def test_r2_random_low():
    """Random walk should have low R²."""
    rng = np.random.RandomState(7)
    prices = 100 + rng.normal(0, 1, 120).cumsum()
    prices = prices - prices.min() + 10
    r2 = TrendDiscovery.calculate_r2(prices, 120)
    assert r2 < 0.9


def test_r2_increasing_detection(td):
    """When trend gets cleaner over time, r2_30d > r2_120d."""
    rng = np.random.RandomState(3)
    noisy = 100 + rng.normal(0, 3, 90).cumsum()
    noisy = noisy - noisy.min() + 50
    clean = np.linspace(noisy[-1], noisy[-1] + 40, 30)
    prices = np.concatenate([noisy, clean])
    vol = np.ones(len(prices)) * 1e6
    result = td.analyze_stock(prices, vol)
    assert result.r2_30d > result.r2_120d


# ═══════════════════════════════════════════════════════════
# 9-10: Slope
# ═══════════════════════════════════════════════════════════

def test_slope_positive_uptrend():
    prices = np.linspace(50, 100, 60)
    slope = TrendDiscovery.calculate_slope(prices, 30)
    assert slope > 0


def test_slope_negative_downtrend():
    prices = np.linspace(100, 50, 60)
    slope = TrendDiscovery.calculate_slope(prices, 30)
    assert slope < 0


# ═══════════════════════════════════════════════════════════
# 11-14: should_sell conditions
# ═══════════════════════════════════════════════════════════

def test_should_sell_r2_breakdown(td):
    """If trend breaks down (R² low), should sell."""
    rng = np.random.RandomState(5)
    clean = np.linspace(50, 100, 60)
    noisy = 100 + rng.normal(0, 5, 40)
    prices = np.concatenate([clean, noisy])
    sell, reason = td.should_sell(prices)
    assert sell is True
    assert reason == "r2_breakdown"


def test_should_sell_rsi_overbought(td):
    """Extremely overbought stock should trigger sell."""
    prices = np.array([50.0])
    for _ in range(100):
        prices = np.append(prices, prices[-1] * 1.025)
    sell, reason = td.should_sell(prices)
    assert sell is True
    assert reason == "rsi_overbought"


def test_should_sell_drawdown(td):
    """20 % drawdown from recent peak → sell.

    We need a sharp drop without the slope or R² checks triggering first.
    Use a long uptrend followed by a sudden gap down (not a gradual decline).
    """
    up = np.linspace(100, 200, 80)
    # sudden gap down: only 3 bars to avoid slope_negative on 10-bar window
    gap = np.array([200.0, 165.0, 155.0])
    prices = np.concatenate([up, gap])
    sell, reason = td.should_sell(prices)
    assert sell is True
    assert reason == "drawdown_20pct"


def test_should_sell_slope_negative(td):
    """Persistent negative slope should sell."""
    up = np.linspace(50, 100, 60)
    down = np.linspace(100, 85, 15)
    prices = np.concatenate([up, down])
    sell, reason = td.should_sell(prices)
    assert sell is True
    assert reason in ("slope_negative", "r2_breakdown")


# ═══════════════════════════════════════════════════════════
# 15-16: should_sell – no false sell on healthy trend
# ═══════════════════════════════════════════════════════════

def test_should_not_sell_healthy_trend(td):
    """A noisy uptrend with natural pullbacks should NOT trigger sell."""
    # ~0.1 %/day drift with wide noise → RSI oscillates naturally
    rng = np.random.RandomState(42)
    prices = [50.0]
    for _ in range(119):
        prices.append(prices[-1] * (1 + 0.001 + rng.normal(0, 0.005)))
    prices = np.array(prices)
    sell, reason = td.should_sell(prices)
    assert sell is False, f"False sell triggered: {reason}"


def test_should_sell_insufficient_data(td):
    prices = np.array([100.0, 101.0, 102.0])
    sell, reason = td.should_sell(prices)
    assert sell is False
    assert reason == "insufficient_data"


# ═══════════════════════════════════════════════════════════
# 17: scan (batch)
# ═══════════════════════════════════════════════════════════

def test_scan_sorts_and_filters(td):
    """scan() should return only non-no_trend results, sorted desc by score."""
    stock_data = {
        "UP001": {
            "prices": _make_rsi_oversold_bounce(90),
            "volumes": np.linspace(1e6, 1.5e6, 90),
            "name": "UpStock",
        },
        "SIDE01": {
            "prices": _make_sideways(200),
            "volumes": np.ones(200) * 1e6,
            "name": "SideStock",
        },
    }
    results = td.scan(stock_data)
    codes = [r.code for r in results]
    assert "UP001" in codes
    assert "SIDE01" not in codes
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


# ═══════════════════════════════════════════════════════════
# 18: report generation
# ═══════════════════════════════════════════════════════════

def test_generate_report_not_empty(td):
    prices = _make_rsi_oversold_bounce(90)
    vol = np.linspace(1e6, 1.5e6, len(prices))
    cand = td.analyze_stock(prices, vol, code="RPT01", name="Report")
    report = TrendDiscovery.generate_report([cand])
    assert "Trend Discovery Report" in report
    assert "RPT01" in report


def test_generate_report_empty():
    report = TrendDiscovery.generate_report([])
    assert "No trend candidates" in report


# ═══════════════════════════════════════════════════════════
# 19-20: Edge cases
# ═══════════════════════════════════════════════════════════

def test_short_data_returns_no_trend(td):
    prices = np.linspace(10, 20, 20)
    vol = np.ones(20)
    result = td.analyze_stock(prices, vol)
    assert result.signal == "no_trend"
    assert result.score == 0.0


def test_flat_prices(td):
    prices = np.full(100, 50.0)
    vol = np.ones(100) * 1e6
    result = td.analyze_stock(prices, vol)
    assert result.signal == "no_trend"
    assert result.r2_30d == 0.0


# ═══════════════════════════════════════════════════════════
# 21-24: RSI calculation unit tests
# ═══════════════════════════════════════════════════════════

def test_rsi_all_up():
    prices = np.arange(1, 50, dtype=np.float64)
    rsi = TrendDiscovery.calculate_rsi(prices, 14)
    valid = rsi[~np.isnan(rsi)]
    assert len(valid) > 0
    assert valid[-1] > 95


def test_rsi_all_down():
    prices = np.arange(50, 1, -1, dtype=np.float64)
    rsi = TrendDiscovery.calculate_rsi(prices, 14)
    valid = rsi[~np.isnan(rsi)]
    assert len(valid) > 0
    assert valid[-1] < 5


def test_rsi_short_data():
    prices = np.array([1.0, 2.0, 3.0])
    rsi = TrendDiscovery.calculate_rsi(prices, 14)
    assert np.all(np.isnan(rsi))


def test_rsi_length_matches_input():
    prices = np.arange(1, 100, dtype=np.float64)
    rsi = TrendDiscovery.calculate_rsi(prices, 14)
    assert len(rsi) == len(prices)


# ═══════════════════════════════════════════════════════════
# 25-26: R² edge cases
# ═══════════════════════════════════════════════════════════

def test_r2_window_larger_than_data():
    prices = np.array([1.0, 2.0, 3.0])
    assert TrendDiscovery.calculate_r2(prices, 10) == 0.0


def test_r2_window_one():
    prices = np.array([1.0, 2.0, 3.0])
    assert TrendDiscovery.calculate_r2(prices, 1) == 0.0


# ═══════════════════════════════════════════════════════════
# 27: Mature trend (overbought + strong trend)
# ═══════════════════════════════════════════════════════════

def test_mature_trend_detection(td):
    """Relentless uptrend with RSI >> 80 and previous RSI dip should be mature_trend.

    Strategy requires:
      - score >= 70  (RSI dip + R² high + slope positive + return high)
      - R² 60d >= 0.7 (strong trend)
      - current RSI > 80

    So we need data where the crash is inside the 60d window for RSI min
    and the recovery pushes RSI to extreme overbought.
    """
    # crash (10 bars), then rocket for 50 bars (all within 60d window)
    crash = np.linspace(100, 40, 10)
    rocket = [crash[-1]]
    for _ in range(60):
        rocket.append(rocket[-1] * 1.028)  # +2.8 %/day
    prices = np.concatenate([crash, np.array(rocket)])
    vol = np.linspace(1e6, 2e6, len(prices))
    result = td.analyze_stock(prices, vol)
    assert result.signal == "mature_trend"
    assert result.hold_suggestion == "take_profit"


# ═══════════════════════════════════════════════════════════
# 28: Custom thresholds
# ═══════════════════════════════════════════════════════════

def test_custom_thresholds():
    td_strict = TrendDiscovery(rsi_oversold_threshold=10.0, r2_strong_min=0.9)
    prices = _make_rsi_oversold_bounce(90)
    vol = np.ones(len(prices)) * 1e6
    result = td_strict.analyze_stock(prices, vol)
    assert isinstance(result.score, float)


# ═══════════════════════════════════════════════════════════
# 29: Volume None handling
# ═══════════════════════════════════════════════════════════

def test_none_volumes(td):
    prices = _make_uptrend(100)
    result = td.analyze_stock(prices, None, code="VOL", name="NoVol")
    assert isinstance(result, TrendCandidate)


# ═══════════════════════════════════════════════════════════
# 30: Total return calculation
# ═══════════════════════════════════════════════════════════

def test_total_return_calculation(td):
    start_val = 100.0
    end_val = 150.0
    prices = np.linspace(start_val, end_val, 100)
    vol = np.ones(100) * 1e6
    result = td.analyze_stock(prices, vol)
    expected = (prices[-1] / prices[-61] - 1) * 100
    assert abs(result.total_return_60d - expected) < 0.5
