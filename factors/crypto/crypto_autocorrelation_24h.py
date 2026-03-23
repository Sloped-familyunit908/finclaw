"""
Factor: crypto_autocorrelation_24h
Description: Lag-1 autocorrelation of 24h returns
Category: crypto
"""

FACTOR_NAME = "crypto_autocorrelation_24h"
FACTOR_DESC = "Lag-1 autocorrelation of hourly returns over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = positive autocorrelation (trending), Low = negative (mean-reverting)."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback, idx):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

    if len(returns) < 6:
        return 0.5

    mean_ret = sum(returns) / len(returns)

    # Autocorrelation at lag 1
    numerator = 0.0
    denominator = 0.0
    for i in range(1, len(returns)):
        numerator += (returns[i] - mean_ret) * (returns[i - 1] - mean_ret)
        denominator += (returns[i] - mean_ret) ** 2

    if denominator <= 0:
        return 0.5

    autocorr = numerator / denominator  # Range [-1, 1]

    # Map: -1 → 0.0, 0 → 0.5, 1 → 1.0
    score = 0.5 + autocorr * 0.5
    return max(0.0, min(1.0, score))
