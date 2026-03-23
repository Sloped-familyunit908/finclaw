"""
Factor: crypto_us_session_strength
Description: Returns during US session hours (idx%24 in [14-22], UTC 14-22)
Category: crypto
"""

FACTOR_NAME = "crypto_us_session_strength"
FACTOR_DESC = "Strength of returns during US trading session (UTC 14-22)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong positive returns during US hours."""
    if idx < 48:
        return 0.5

    returns = []
    for i in range(max(1, idx - 168), idx + 1):
        hour = i % 24
        if 14 <= hour <= 22:
            if closes[i - 1] > 0:
                ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                returns.append(ret)

    if len(returns) < 3:
        return 0.5

    avg_ret = sum(returns) / len(returns)
    score = 0.5 + avg_ret * 100.0
    return max(0.0, min(1.0, score))
