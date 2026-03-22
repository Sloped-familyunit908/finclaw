"""
Auto-generated factor: kyle_lambda_proxy
Description: Price impact per unit volume (regression slope of |return| on volume)
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "kyle_lambda_proxy"
FACTOR_DESC = "Price impact per unit volume (regression slope of |return| on volume)"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Kyle's lambda proxy: slope of |return| regressed on volume."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Collect data for regression
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0
    n = 0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0 and volumes[i] > 0:
            x = float(volumes[i])
            y = abs((closes[i] - closes[i - 1]) / closes[i - 1])
            sum_x += x
            sum_y += y
            sum_xy += x * y
            sum_x2 += x * x
            n += 1

    if n < 5:
        return 0.5

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-20:
        return 0.5

    # Slope of regression
    slope = (n * sum_xy - sum_x * sum_y) / denom

    # Higher lambda = higher price impact = less liquid = bearish
    # Lower lambda = more liquid = bullish
    # Normalize slope
    score = 0.5 - slope * 1e6
    return max(0.0, min(1.0, score))
