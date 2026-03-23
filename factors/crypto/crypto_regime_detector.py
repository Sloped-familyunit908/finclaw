"""
Factor: crypto_regime_detector
Description: Trending (>0.7) vs mean-reverting (<0.3) vs neutral
Category: crypto
"""

FACTOR_NAME = "crypto_regime_detector"
FACTOR_DESC = "Market regime: trending vs mean-reverting vs neutral"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.7 = trending, below 0.3 = mean-reverting, mid = neutral."""
    lookback = 48
    if idx < lookback + 1:
        return 0.5

    # Method: Compare ABS(sum of returns) vs sum of ABS(returns)
    # Trending: returns accumulate in one direction
    # Mean-reverting: returns cancel out
    signed_sum = 0.0
    abs_sum = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            signed_sum += ret
            abs_sum += abs(ret)

    if abs_sum <= 0:
        return 0.5

    # Efficiency ratio: |net move| / total path
    efficiency = abs(signed_sum) / abs_sum

    # Also check autocorrelation as secondary signal
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    autocorr = 0.0
    if len(returns) > 2:
        mean_r = sum(returns) / len(returns)
        num = sum((returns[i] - mean_r) * (returns[i - 1] - mean_r) for i in range(1, len(returns)))
        den = sum((r - mean_r) ** 2 for r in returns)
        if den > 0:
            autocorr = num / den  # -1 to +1

    # Combine: efficiency (0 to 1) and autocorrelation (-1 to +1)
    # Both positive = trending, both negative/zero = mean reverting
    regime = efficiency * 0.6 + (autocorr + 1) / 2 * 0.4
    return max(0.0, min(1.0, regime))
