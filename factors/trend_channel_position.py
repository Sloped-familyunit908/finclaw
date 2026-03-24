"""
Factor: trend_channel_position
Description: Position within a linear regression channel
Category: trend_following
"""

FACTOR_NAME = "trend_channel_position"
FACTOR_DESC = "Position in linear regression channel — above center = bullish"
FACTOR_CATEGORY = "trend_following"


def compute(closes, highs, lows, volumes, idx):
    """Calculate position within a linear regression channel.
    Above the regression line = bullish (score > 0.5).
    Below = bearish (score < 0.5).
    """
    period = 20
    if idx < period:
        return 0.5

    # Linear regression using least squares
    n = period
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_xx = 0.0

    for i in range(n):
        x = float(i)
        y = closes[idx - period + 1 + i]
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_xx += x * x

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.5

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # Regression value at current point
    reg_value = intercept + slope * (n - 1)

    # Calculate standard error for channel width
    sse = 0.0
    for i in range(n):
        predicted = intercept + slope * i
        actual = closes[idx - period + 1 + i]
        sse += (actual - predicted) ** 2
    std_err = (sse / n) ** 0.5

    if std_err <= 0:
        return 0.5

    # Current price position: how many std_errs above/below regression
    deviation = (closes[idx] - reg_value) / std_err

    # Map deviation to [0, 1]: -2σ → 0, 0 → 0.5, +2σ → 1.0
    score = 0.5 + deviation / 4.0

    return max(0.0, min(1.0, score))
