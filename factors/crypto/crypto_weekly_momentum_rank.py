"""
Factor: crypto_weekly_momentum_rank
Description: 168h (1 week) return normalized — weekly momentum
Category: crypto
"""

FACTOR_NAME = "crypto_weekly_momentum_rank"
FACTOR_DESC = "Weekly momentum — 168-hour return normalized to [0,1]"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong weekly positive momentum."""
    lookback = 168
    if idx < lookback:
        return 0.5

    if closes[idx - lookback] <= 0:
        return 0.5

    weekly_ret = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    # Map: -10% → 0.0, 0% → 0.5, +10% → 1.0
    score = 0.5 + weekly_ret * 5.0
    return max(0.0, min(1.0, score))
