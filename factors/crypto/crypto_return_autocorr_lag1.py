"""
Factor: crypto_return_autocorr_lag1
Description: Lag-1 autocorrelation of hourly returns (momentum vs reversal)
Category: crypto
"""

FACTOR_NAME = "crypto_return_autocorr_lag1"
FACTOR_DESC = "Lag-1 autocorrelation of returns"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = positive autocorr (trending), below = mean-reverting."""
    lookback = 24
    if idx < lookback + 2:
        return 0.5

    returns = []
    for i in range(idx - lookback, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)

    if len(returns) < 3:
        return 0.5

    mean_r = sum(returns) / len(returns)

    # Autocorrelation at lag 1
    num = 0.0
    den = 0.0
    for i in range(1, len(returns)):
        num += (returns[i] - mean_r) * (returns[i - 1] - mean_r)
        den += (returns[i] - mean_r) ** 2

    if den == 0:
        return 0.5

    autocorr = num / den  # Range: -1 to +1

    score = 0.5 + autocorr * 0.5
    return max(0.0, min(1.0, score))
