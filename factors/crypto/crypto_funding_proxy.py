"""
Factor: crypto_funding_proxy
Description: Price premium of current vs 24h-ago — funding/basis proxy
Category: crypto
"""

FACTOR_NAME = "crypto_funding_proxy"
FACTOR_DESC = "Funding rate proxy — price premium relative to 24h ago"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = positive premium (bullish funding), Low = discount."""
    if idx < 24:
        return 0.5

    if closes[idx - 24] <= 0:
        return 0.5

    premium = (closes[idx] - closes[idx - 24]) / closes[idx - 24]

    # Map: -2% → 0.0, 0% → 0.5, +2% → 1.0
    score = 0.5 + premium * 25.0
    return max(0.0, min(1.0, score))
