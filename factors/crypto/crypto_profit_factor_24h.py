"""
Factor: crypto_profit_factor_24h
Description: Sum(positive returns) / abs(sum(negative returns)) over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_profit_factor_24h"
FACTOR_DESC = "Sum(positive returns) / abs(sum(negative returns)) over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = profit factor > 1 (more gains than losses)."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    gains = 0.0
    losses = 0.0
    for i in range(idx - lookback, idx):
        if i < 1:
            continue
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses += abs(change)

    if gains + losses <= 0:
        return 0.5

    pf = gains / (gains + losses)
    return max(0.0, min(1.0, pf))
