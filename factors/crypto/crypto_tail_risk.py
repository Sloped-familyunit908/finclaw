"""
Factor: crypto_tail_risk
Description: Kurtosis of 48h returns — fat tail detection
Category: crypto
"""

FACTOR_NAME = "crypto_tail_risk"
FACTOR_DESC = "Kurtosis of 48h returns — detects fat tails and extreme risk"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = normal distribution, Low = fat tails (risky)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Compute returns
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

    if len(returns) < 20:
        return 0.5

    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / len(returns)

    if var <= 0:
        return 0.5

    # Kurtosis: E[(X-mu)^4] / var^2 - 3 (excess kurtosis)
    m4 = sum((r - mean_r) ** 4 for r in returns) / len(returns)
    kurtosis = m4 / (var ** 2) - 3.0

    # Normal distribution has kurtosis = 0 (excess)
    # Fat tails: kurtosis > 0
    # Thin tails: kurtosis < 0
    # Crypto typically has kurtosis 2-10+

    # Map: kurtosis 0 → 0.7 (normal, good), kurtosis 6+ → 0.1 (fat tails, risky)
    score = 0.7 - min(max(kurtosis, 0), 6.0) / 6.0 * 0.6

    return max(0.0, min(1.0, score))
