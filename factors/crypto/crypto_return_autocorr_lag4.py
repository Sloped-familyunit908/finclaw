"""
Factor: crypto_return_autocorr_lag4
Description: Lag-4 autocorrelation of hourly returns
Category: crypto
"""

FACTOR_NAME = "crypto_return_autocorr_lag4"
FACTOR_DESC = "Lag-4 autocorrelation of returns"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = positive lag-4 autocorrelation."""
    lookback = 24
    lag = 4
    if idx < lookback + lag + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback - lag, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)

    if len(returns) < lag + 2:
        return 0.5

    mean_r = sum(returns) / len(returns)

    num = 0.0
    den = 0.0
    for i in range(lag, len(returns)):
        num += (returns[i] - mean_r) * (returns[i - lag] - mean_r)
        den += (returns[i] - mean_r) ** 2

    if den == 0:
        return 0.5

    autocorr = num / den

    score = 0.5 + autocorr * 0.5
    return max(0.0, min(1.0, score))
