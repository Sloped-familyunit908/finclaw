"""
Factor: crypto_body_momentum
Description: Running sum of body direction (close-open) over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_body_momentum"
FACTOR_DESC = "Running sum of body direction (close-open) over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = bullish body momentum, <0.5 = bearish."""
    lookback = 24
    if idx < lookback:
        return 0.5

    body_sum = 0.0
    range_sum = 0.0
    for i in range(idx - lookback, idx):
        open_approx = closes[i - 1] if i > 0 else closes[i]
        body_sum += closes[i] - open_approx
        range_sum += highs[i] - lows[i]

    if range_sum <= 0:
        return 0.5

    ratio = body_sum / range_sum
    score = 0.5 + ratio * 0.5
    return max(0.0, min(1.0, score))
