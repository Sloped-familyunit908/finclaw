"""
Factor: crypto_trend_consistency
Description: Percentage of bars moving in trend direction over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_trend_consistency"
FACTOR_DESC = "Trend consistency — fraction of bars moving in dominant direction"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = consistent uptrend, Low = consistent downtrend."""
    lookback = 24
    if idx < lookback:
        return 0.5

    up_count = 0
    down_count = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_count += 1
        elif closes[i] < closes[i - 1]:
            down_count += 1

    total = up_count + down_count
    if total == 0:
        return 0.5

    # Determine trend direction from overall move
    overall = closes[idx] - closes[idx - lookback]
    if overall > 0:
        consistency = up_count / total
        score = 0.5 + consistency * 0.5
    elif overall < 0:
        consistency = down_count / total
        score = 0.5 - consistency * 0.5
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
