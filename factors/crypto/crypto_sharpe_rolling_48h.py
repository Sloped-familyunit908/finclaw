"""
Factor: crypto_sharpe_rolling_48h
Description: Rolling 48h Sharpe ratio of returns
Category: crypto
"""

FACTOR_NAME = "crypto_sharpe_rolling_48h"
FACTOR_DESC = "Rolling 48-hour Sharpe ratio — risk-adjusted return measure"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = good risk-adjusted returns."""
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

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    std_ret = variance ** 0.5

    if std_ret <= 0:
        return 0.5

    sharpe = mean_ret / std_ret
    # Typical hourly Sharpe: -0.5 to 0.5
    score = 0.5 + sharpe
    return max(0.0, min(1.0, score))
