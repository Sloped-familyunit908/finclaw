"""
Factor: pullback_ma20_bounce
Description: Price pulled back to touch or slightly break below 20-day MA
  while MA20 is still rising. Classic retest of support in uptrend.
Category: pullback_strategy
"""

FACTOR_NAME = "pullback_ma20_bounce"
FACTOR_DESC = (
    "Price retests rising MA20 from above — classic uptrend support bounce"
)
FACTOR_CATEGORY = "pullback_strategy"


def _calc_ma(closes, end_idx, period):
    """Simple moving average ending at end_idx (inclusive)."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """
    Logic
    -----
    1. MA20 is rising (slope over last 5 bars > 0)
    2. Price is near MA20: touched it or dipped slightly below
       - Ideal: low touched MA20 but close is at or above  → bounce confirmed
       - OK: close slightly below MA20 (within 2%) → still plausible bounce
    3. Bonus: prior 5 bars were above MA20 → confirms this is a *pullback*
       to support, not a breakdown from below
    """
    if idx < 25:
        return 0.5

    ma20_now = _calc_ma(closes, idx, 20)
    ma20_prev = _calc_ma(closes, idx - 5, 20)

    if ma20_now is None or ma20_prev is None or ma20_prev <= 0:
        return 0.5

    # ── MA20 must be rising ──
    ma20_slope = (ma20_now - ma20_prev) / ma20_prev
    if ma20_slope <= 0:
        return 0.3  # flat/falling MA20 — not an uptrend bounce

    # ── Distance: how close is price to MA20? ──
    if ma20_now <= 0:
        return 0.5
    close_dist = (closes[idx] - ma20_now) / ma20_now      # % above/below
    low_dist = (lows[idx] - ma20_now) / ma20_now           # low wick vs MA20

    # Did the low touch or pierce MA20?
    low_touched = low_dist <= 0.005  # within 0.5% of MA20 or below

    # Close position relative to MA20
    if close_dist > 0.03:
        return 0.5  # price too far above MA20 — not a pullback
    if close_dist < -0.05:
        return 0.2  # broke well below — support failed

    # ── Bounce quality ──
    if low_touched and close_dist >= 0:
        # Perfect: low touched MA20, close recovered above → bounce confirmed
        touch_score = 1.0
    elif low_touched and close_dist >= -0.01:
        # Low touched, close barely below → possible bounce
        touch_score = 0.8
    elif -0.02 <= close_dist <= 0.01:
        # Close very near MA20, low may or may not have touched
        touch_score = 0.6
    else:
        touch_score = 0.3

    # ── Were prior bars above MA20? (confirms pullback, not breakdown) ──
    bars_above = 0
    for i in range(max(0, idx - 5), idx):
        ma20_i = _calc_ma(closes, i, 20)
        if ma20_i and closes[i] > ma20_i:
            bars_above += 1
    prior_above_score = min(1.0, bars_above / 3.0)

    # ── Slope strength ──
    slope_score = min(1.0, ma20_slope / 0.02)

    score = 0.4 + 0.6 * touch_score * slope_score * (0.5 + 0.5 * prior_above_score)

    return max(0.0, min(1.0, score))
