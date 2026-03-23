"""
Factor: crypto_stoch_d_3
Description: %D smoothed stochastic (3-period SMA of %K)
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_d_3"
FACTOR_DESC = "%D smoothed stochastic (3-period SMA of %K)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Smoothed %D stochastic."""
    lookback_k = 14
    smooth = 3
    if idx < lookback_k + smooth - 1:
        return 0.5

    k_values = []
    for j in range(smooth):
        i = idx - smooth + 1 + j
        highest = max(highs[i - lookback_k:i])
        lowest = min(lows[i - lookback_k:i])
        r = highest - lowest
        if r <= 0:
            k_values.append(0.5)
        else:
            k_values.append((closes[i - 1] - lowest) / r)

    d = sum(k_values) / len(k_values)
    return max(0.0, min(1.0, d))
