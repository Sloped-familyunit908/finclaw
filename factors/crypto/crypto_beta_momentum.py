"""
Factor: crypto_beta_momentum
Description: Momentum adjusted for market beta
Category: crypto
"""

FACTOR_NAME = "crypto_beta_momentum"
FACTOR_DESC = "Beta-adjusted momentum — momentum signal normalized by volatility"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Returns float in [0, 1].
    Momentum (12-bar return) adjusted by rolling volatility (beta proxy).
    High = strong risk-adjusted momentum, Low = weak.
    """
    import math

    momentum_period = 12
    vol_period = 24
    if idx < vol_period:
        return 0.5

    # Raw momentum
    if closes[idx - momentum_period] <= 0:
        return 0.5
    raw_momentum = (closes[idx] - closes[idx - momentum_period]) / closes[idx - momentum_period]

    # Rolling volatility (as beta proxy / risk measure)
    returns = []
    for i in range(idx - vol_period + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 10:
        return 0.5

    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    vol = math.sqrt(var) if var > 0 else 0

    if vol <= 0:
        return 0.5

    # Risk-adjusted momentum (like Sharpe ratio of recent period)
    risk_adj_momentum = raw_momentum / vol

    # Typical range: -3 to +3 (like Sharpe)
    # Map: -3 → 0, 0 → 0.5, +3 → 1.0
    score = 0.5 + risk_adj_momentum / 6.0

    return max(0.0, min(1.0, score))
