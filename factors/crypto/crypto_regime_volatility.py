"""
Factor: crypto_regime_volatility
Description: Current 24h vol vs 168h vol (expanding or contracting)
Category: crypto
"""

FACTOR_NAME = "crypto_regime_volatility"
FACTOR_DESC = "Current 24h vol vs 168h vol (expanding or contracting)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = volatility expanding, <0.5 = contracting."""
    short_lb = 24
    long_lb = 168
    if idx < long_lb + 1:
        return 0.5

    def calc_vol(start, end):
        returns = []
        for i in range(start, end):
            if i < 1 or closes[i - 1] <= 0:
                continue
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if len(returns) < 2:
            return 0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / len(returns)
        return var ** 0.5

    short_vol = calc_vol(idx - short_lb, idx)
    long_vol = calc_vol(idx - long_lb, idx)

    if long_vol <= 0:
        return 0.5

    ratio = short_vol / long_vol
    score = 0.5 + (ratio - 1.0) * 0.3
    return max(0.0, min(1.0, score))
