"""
Factor: crypto_trend_linearity
Description: R-squared of price vs time over 48 bars — trend quality measure
Category: crypto
"""

FACTOR_NAME = "crypto_trend_linearity"
FACTOR_DESC = "Trend linearity via R-squared of price vs time over 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = very linear trend (strong directional move)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    prices = closes[idx - lookback:idx]
    n = lookback

    # Linear regression
    x_mean = (n - 1) / 2.0
    y_mean = sum(prices) / n

    ss_xy = 0.0
    ss_xx = 0.0
    ss_yy = 0.0
    for i in range(n):
        x_diff = i - x_mean
        y_diff = prices[i] - y_mean
        ss_xy += x_diff * y_diff
        ss_xx += x_diff * x_diff
        ss_yy += y_diff * y_diff

    if ss_xx <= 0 or ss_yy <= 0:
        return 0.5

    r_squared = (ss_xy * ss_xy) / (ss_xx * ss_yy)
    return max(0.0, min(1.0, r_squared))
