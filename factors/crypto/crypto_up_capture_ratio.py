"""
Factor: crypto_up_capture_ratio
Description: Performance in up bars vs down bars
Category: crypto
"""

FACTOR_NAME = "crypto_up_capture_ratio"
FACTOR_DESC = "Performance in up bars vs down bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = captures more upside than downside."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    up_returns = []
    down_returns = []
    for i in range(idx - lookback, idx):
        if i < 1 or closes[i - 1] <= 0:
            continue
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        if ret > 0:
            up_returns.append(ret)
        elif ret < 0:
            down_returns.append(ret)

    avg_up = sum(up_returns) / len(up_returns) if up_returns else 0
    avg_down = abs(sum(down_returns) / len(down_returns)) if down_returns else 0

    if avg_up + avg_down <= 0:
        return 0.5

    score = avg_up / (avg_up + avg_down)
    return max(0.0, min(1.0, score))
