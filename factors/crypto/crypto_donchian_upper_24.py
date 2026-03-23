"""
Factor: crypto_donchian_upper_24
Description: Price position vs 24-bar Donchian upper channel
Category: crypto
"""

FACTOR_NAME = "crypto_donchian_upper_24"
FACTOR_DESC = "Price position vs 24-bar Donchian upper channel"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price near/above 24-bar high channel."""
    lookback = 24
    if idx < lookback:
        return 0.5

    upper = max(highs[idx - lookback:idx])
    lower = min(lows[idx - lookback:idx])
    r = upper - lower
    if r <= 0:
        return 0.5

    position = (closes[idx - 1] - lower) / r
    return max(0.0, min(1.0, position))
