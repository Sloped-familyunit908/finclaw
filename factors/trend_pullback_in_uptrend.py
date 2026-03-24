"""
Factor: trend_pullback_in_uptrend
Description: Pullback to MA20 in an uptrend — buy-the-dip signal
Category: trend_following
"""

FACTOR_NAME = "trend_pullback_in_uptrend"
FACTOR_DESC = "Price pulls back to rising MA20 — buy the dip in uptrend"
FACTOR_CATEGORY = "trend_following"


def _calc_ma(closes, end_idx, period):
    """Simple moving average."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """In an uptrend (MA20 rising), a pullback to MA20 = buy the dip.
    Score high if price is near MA20 AND MA20 slope is positive.
    """
    if idx < 25:
        return 0.5

    ma20_now = _calc_ma(closes, idx, 20)
    ma20_prev = _calc_ma(closes, idx - 5, 20)

    if ma20_now is None or ma20_prev is None:
        return 0.5

    # Check if MA20 is rising (uptrend)
    if ma20_prev <= 0:
        return 0.5

    ma20_slope = (ma20_now - ma20_prev) / ma20_prev

    if ma20_slope <= 0:
        return 0.5  # MA20 not rising — not an uptrend

    # Check if price is near MA20 (within 2% above or below)
    if ma20_now <= 0:
        return 0.5

    distance = (closes[idx] - ma20_now) / ma20_now

    # We want price NEAR the MA20 (within ±2%), slightly below is ideal
    if distance > 0.03:
        return 0.5  # Price too far above MA20 — not a pullback
    if distance < -0.05:
        return 0.5  # Price too far below — broken support

    # Perfect pullback: price right at or slightly below MA20
    # Best case: distance between -2% and 0%
    if -0.02 <= distance <= 0.005:
        nearness_score = 1.0
    elif -0.05 <= distance < -0.02:
        nearness_score = 0.5
    else:
        nearness_score = max(0.0, 1.0 - distance / 0.03)

    # MA20 slope strength
    slope_score = min(1.0, ma20_slope / 0.03)  # 3% rise over 5 days = max

    score = 0.6 + 0.4 * nearness_score * slope_score

    return max(0.0, min(1.0, score))
