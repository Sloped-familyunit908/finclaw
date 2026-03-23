"""
Factor: crypto_fib_382_retracement
Description: Is price near 38.2% retracement of last 48h swing
Category: crypto
"""

FACTOR_NAME = "crypto_fib_382_retracement"
FACTOR_DESC = "Is price near 38.2% retracement of last 48h swing"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price is near 38.2% Fibonacci level."""
    lookback = 48
    if idx < lookback:
        return 0.5

    swing_high = max(highs[idx - lookback:idx])
    swing_low = min(lows[idx - lookback:idx])
    swing_range = swing_high - swing_low
    if swing_range <= 0:
        return 0.5

    fib_level = swing_high - 0.382 * swing_range
    distance = abs(closes[idx - 1] - fib_level) / swing_range

    score = max(0.0, 1.0 - distance * 5.0)
    return max(0.0, min(1.0, score))
