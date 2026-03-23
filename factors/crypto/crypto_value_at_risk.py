"""
Factor: crypto_value_at_risk
Description: 5th percentile of 48h returns — left tail risk measure
Category: crypto
"""

FACTOR_NAME = "crypto_value_at_risk"
FACTOR_DESC = "Value at Risk proxy — 5th percentile of 48h returns (tail risk)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = low tail risk, Low = high tail risk."""
    lookback = 48
    if idx < lookback:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

    if len(returns) < 10:
        return 0.5

    returns.sort()

    # 5th percentile
    var_idx = max(0, int(len(returns) * 0.05))
    var_5 = returns[var_idx]

    # var_5 is typically negative (worst returns)
    # Map: -5% → 0.0, -1% → 0.5, 0% → 0.75, positive → 1.0
    score = 0.5 + var_5 * 10.0
    return max(0.0, min(1.0, score))
