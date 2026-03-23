"""
Factor: crypto_realized_vol_24h
Description: Realized volatility of returns (24h)
Category: crypto
"""

FACTOR_NAME = "crypto_realized_vol_24h"
FACTOR_DESC = "Realized volatility of returns over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = higher realized volatility."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 2:
        return 0.5

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    vol = variance ** 0.5

    # Typical hourly vol range: 0.1% to 3%
    score = vol / 0.03
    return max(0.0, min(1.0, score))
