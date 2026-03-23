"""
Factor: crypto_doji_frequency
Description: Count of doji candles (body < 10% of range) in last 12 bars
Category: crypto
"""

FACTOR_NAME = "crypto_doji_frequency"
FACTOR_DESC = "Frequency of doji candles in last 12 bars — indecision signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = many doji candles (indecision/reversal)."""
    lookback = 12
    if idx < lookback:
        return 0.5

    count = 0
    for i in range(idx - lookback, idx):
        rng = highs[i] - lows[i]
        if rng > 0:
            # Estimate open as previous close
            open_est = closes[i - 1] if i > 0 else closes[i]
            body = abs(closes[i] - open_est)
            if body / rng < 0.10:
                count += 1

    # Normalize: 0/12 → 0.5, 6/12 → 1.0
    score = 0.5 + (count / lookback)
    return max(0.0, min(1.0, score))
