"""
Factor: crypto_spread_proxy
Description: (high-low)/close as bid-ask spread proxy
Category: crypto
"""

FACTOR_NAME = "crypto_spread_proxy"
FACTOR_DESC = "High-low range relative to close as bid-ask spread proxy"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = tight spread (liquid), Low = wide spread (illiquid)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    if closes[idx] <= 0:
        return 0.5

    current_spread = (highs[idx] - lows[idx]) / closes[idx]

    # Rolling average spread over lookback
    spreads = []
    for i in range(idx - lookback, idx):
        if closes[i] > 0:
            spreads.append((highs[i] - lows[i]) / closes[i])

    if not spreads:
        return 0.5

    avg_spread = sum(spreads) / len(spreads)
    if avg_spread <= 0:
        return 0.5

    # Ratio of current spread to average
    ratio = current_spread / avg_spread

    # Tight spread (ratio < 1) = good liquidity = bullish → high score
    # Wide spread (ratio > 1) = poor liquidity = risky → low score
    score = 1.0 - min(ratio / 3.0, 1.0)

    return max(0.0, min(1.0, score))
