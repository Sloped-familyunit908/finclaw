"""
Factor: crypto_regime_mean_revert
Description: Hurst exponent proxy — autocorrelation based mean reversion detection
Category: crypto
"""

FACTOR_NAME = "crypto_regime_mean_revert"
FACTOR_DESC = "Hurst exponent proxy — autocorrelation based mean reversion detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. <0.5 = mean-reverting, >0.5 = trending."""
    lookback = 48
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback, idx):
        if i < 1 or closes[i - 1] <= 0:
            returns.append(0)
            continue
        returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 10:
        return 0.5

    # Autocorrelation lag-1
    mean_r = sum(returns) / len(returns)
    num = 0.0
    den = 0.0
    for i in range(1, len(returns)):
        num += (returns[i] - mean_r) * (returns[i - 1] - mean_r)
        den += (returns[i] - mean_r) ** 2

    if den <= 0:
        return 0.5

    autocorr = num / den
    # Negative autocorr = mean reverting, positive = trending
    score = 0.5 + autocorr * 0.5
    return max(0.0, min(1.0, score))
