"""
Quality Factor: Earnings Momentum Proxy
==========================================
If a stock has been consistently declining for 3+ months on average volume,
it likely has deteriorating fundamentals.  Use price trend slope over 60 days
as a proxy.  Negative steep slope = bad earnings trajectory.

Category: quality_filter
"""

FACTOR_NAME = "quality_earnings_momentum_proxy"
FACTOR_DESC = "60-day price slope as earnings proxy — steep decline = bad fundamentals"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = 60
    if idx < lookback:
        lookback = idx + 1
    if lookback < 20:
        return 0.5

    # Linear regression slope over lookback period
    n = lookback
    mean_x = (n - 1) / 2.0
    mean_y = 0.0
    for i in range(n):
        mean_y += closes[idx - n + 1 + i]
    mean_y /= n

    if mean_y <= 0:
        return 0.5

    ss_xy = 0.0
    ss_xx = 0.0
    for i in range(n):
        dx = i - mean_x
        dy = closes[idx - n + 1 + i] - mean_y
        ss_xy += dx * dy
        ss_xx += dx * dx

    if ss_xx <= 0:
        return 0.5

    slope = ss_xy / ss_xx
    # Normalize slope as daily % change relative to mean price
    slope_pct = (slope / mean_y) * 100.0

    # Map: -1.0% daily -> 0.0 (terrible), 0.0% -> 0.5 (neutral), +1.0% -> 1.0 (great)
    score = 0.5 + slope_pct / 2.0
    return max(0.0, min(1.0, score))
