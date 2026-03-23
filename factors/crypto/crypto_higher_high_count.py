"""
Factor: crypto_higher_high_count
Description: Count of higher highs in last 24 bars — uptrend strength
Category: crypto
"""

FACTOR_NAME = "crypto_higher_high_count"
FACTOR_DESC = "Number of higher highs in last 24 bars — measures uptrend quality"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = many higher highs (strong uptrend)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    count = 0
    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] > highs[i - 1]:
            count += 1

    # Normalize: count/lookback. 50%+ higher highs = strong uptrend
    ratio = count / lookback
    score = ratio  # 0 to ~1
    return max(0.0, min(1.0, score))
