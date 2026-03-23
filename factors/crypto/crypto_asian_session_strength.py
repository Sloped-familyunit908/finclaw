"""
Factor: crypto_asian_session_strength
Description: Returns during Asian session hours (idx%24 in [0-8], UTC 0-8)
Category: crypto
"""

FACTOR_NAME = "crypto_asian_session_strength"
FACTOR_DESC = "Strength of returns during Asian trading session (UTC 0-8)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong positive returns during Asian hours."""
    if idx < 48:
        return 0.5

    # Collect returns during Asian session hours over last ~7 days
    returns = []
    for i in range(max(1, idx - 168), idx + 1):
        hour = i % 24
        if 0 <= hour <= 8:
            if closes[i - 1] > 0:
                ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                returns.append(ret)

    if len(returns) < 3:
        return 0.5

    avg_ret = sum(returns) / len(returns)
    # Scale: -0.5% → 0.0, 0 → 0.5, +0.5% → 1.0
    score = 0.5 + avg_ret * 100.0
    return max(0.0, min(1.0, score))
