"""
Auto-generated factor: mean_cross_down
Description: Price crossing below 20-day SMA from above (bearish, low score)
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "mean_cross_down"
FACTOR_DESC = "Price crossing below 20-day SMA from above (bearish, low score)"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Detect price crossing below 20-day SMA (bearish)."""

    lookback = 21
    if idx < lookback:
        return 0.5

    # SMA today
    total_today = 0.0
    for i in range(idx - 19, idx + 1):
        total_today += closes[i]
    sma_today = total_today / 20.0

    # SMA yesterday
    total_yesterday = 0.0
    for i in range(idx - 20, idx):
        total_yesterday += closes[i]
    sma_yesterday = total_yesterday / 20.0

    was_above = closes[idx - 1] > sma_yesterday
    is_below = closes[idx] < sma_today

    if was_above and is_below:
        # Bearish cross
        return 0.15
    elif closes[idx] < sma_today:
        return 0.4
    elif closes[idx] > sma_today:
        return 0.6
    else:
        return 0.5
