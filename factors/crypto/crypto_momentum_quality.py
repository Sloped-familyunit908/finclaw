"""
Factor: crypto_momentum_quality
Description: Consistency of positive returns (% positive bars in last 24)
Category: crypto
"""

FACTOR_NAME = "crypto_momentum_quality"
FACTOR_DESC = "Consistency of positive returns over last 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 1.0 = all bars positive, 0.0 = all negative."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    positive_count = 0
    for i in range(idx - lookback, idx):
        if closes[i] > closes[i - 1]:
            positive_count += 1

    score = positive_count / lookback
    return max(0.0, min(1.0, score))
