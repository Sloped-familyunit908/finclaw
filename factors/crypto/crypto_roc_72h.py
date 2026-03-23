"""
Factor: crypto_roc_72h
Description: Rate of change over 72 bars
Category: crypto
"""

FACTOR_NAME = "crypto_roc_72h"
FACTOR_DESC = "Rate of change over 72 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = positive momentum."""
    lookback = 72
    if idx < lookback:
        return 0.5

    if closes[idx - lookback] <= 0:
        return 0.5

    roc = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    # Typical 72-bar roc range: -20% to +20%
    score = 0.5 + (roc / 0.40)
    return max(0.0, min(1.0, score))
