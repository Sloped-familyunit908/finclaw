"""
Factor: crypto_williams_r_48
Description: Williams %R over 48 bars
Category: crypto
"""

FACTOR_NAME = "crypto_williams_r_48"
FACTOR_DESC = "Williams %R over 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 0 = overbought, 1 = oversold."""
    lookback = 48
    if idx < lookback:
        return 0.5

    highest = max(highs[idx - lookback:idx])
    lowest = min(lows[idx - lookback:idx])
    r = highest - lowest
    if r <= 0:
        return 0.5

    williams_r = (highest - closes[idx - 1]) / r
    return max(0.0, min(1.0, williams_r))
