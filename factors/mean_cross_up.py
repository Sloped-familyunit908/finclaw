"""
Auto-generated factor: mean_cross_up
Description: Price crossing above 20-day SMA from below
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "mean_cross_up"
FACTOR_DESC = "Price crossing above 20-day SMA from below"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Detect price crossing above 20-day SMA."""

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

    was_below = closes[idx - 1] < sma_yesterday
    is_above = closes[idx] > sma_today

    if was_below and is_above:
        # Bullish cross
        return 0.85
    elif closes[idx] > sma_today:
        return 0.6
    elif closes[idx] < sma_today:
        return 0.4
    else:
        return 0.5
