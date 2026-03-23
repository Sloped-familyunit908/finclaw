"""
Factor: crypto_regime_momentum
Description: R-squared of price regression (high=trending, low=choppy)
Category: crypto
"""

FACTOR_NAME = "crypto_regime_momentum"
FACTOR_DESC = "R-squared of price regression (high=trending, low=choppy)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strongly trending, low = choppy/random."""
    lookback = 24
    if idx < lookback:
        return 0.5

    prices = closes[idx - lookback:idx]
    n = len(prices)
    mean_x = (n - 1) / 2.0
    mean_y = sum(prices) / n

    ss_xy = 0.0
    ss_xx = 0.0
    ss_yy = 0.0
    for i in range(n):
        dx = i - mean_x
        dy = prices[i] - mean_y
        ss_xy += dx * dy
        ss_xx += dx * dx
        ss_yy += dy * dy

    if ss_xx <= 0 or ss_yy <= 0:
        return 0.5

    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    return max(0.0, min(1.0, r_squared))
