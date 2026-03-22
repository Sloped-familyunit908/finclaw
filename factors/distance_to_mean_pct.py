"""
Auto-generated factor: distance_to_mean_pct
Description: Percentage distance from 20-day SMA
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "distance_to_mean_pct"
FACTOR_DESC = "Percentage distance from 20-day SMA"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Percentage distance from 20-day SMA, mapped to [0,1]."""

    lookback = 20
    if idx < lookback:
        return 0.5

    total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total += closes[i]
    sma = total / lookback

    if sma < 1e-10:
        return 0.5

    dist_pct = (closes[idx] - sma) / sma * 100.0

    # Map from [-10%, +10%] to [0, 1]
    # Below mean (negative) = oversold = bullish for reversion = high score
    score = 0.5 - (dist_pct / 20.0)
    return max(0.0, min(1.0, score))
