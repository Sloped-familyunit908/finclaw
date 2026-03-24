"""
Factor: trend_price_above_all_ma
Description: Price above MA5, MA10, MA20, MA60 simultaneously
Category: trend_following
"""

FACTOR_NAME = "trend_price_above_all_ma"
FACTOR_DESC = "Price above MA5/MA10/MA20/MA60 — score = count of MAs below price / 4"
FACTOR_CATEGORY = "trend_following"


def _calc_ma(closes, end_idx, period):
    """Simple moving average."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """Score = count of MAs that price is above / 4.
    All 4 above = 1.0, none = 0.0.
    """
    if idx < 60:
        # Use available MAs only
        periods = [p for p in [5, 10, 20, 60] if idx >= p - 1]
        if not periods:
            return 0.5
    else:
        periods = [5, 10, 20, 60]

    above_count = 0
    total = len(periods)

    for period in periods:
        ma = _calc_ma(closes, idx, period)
        if ma is not None and closes[idx] > ma:
            above_count += 1

    if total == 0:
        return 0.5

    # Score from 0 to 1 based on fraction above
    score = above_count / total

    return max(0.0, min(1.0, score))
