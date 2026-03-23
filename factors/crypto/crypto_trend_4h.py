"""
Factor: crypto_trend_4h
Description: 4-bar EMA direction and strength
Category: crypto
"""

FACTOR_NAME = "crypto_trend_4h"
FACTOR_DESC = "4-bar EMA direction and strength — short-term trend signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong uptrend, Low = strong downtrend."""
    lookback = 8
    if idx < lookback:
        return 0.5

    # Compute 4-bar EMA
    multiplier = 2.0 / (4 + 1)
    ema = closes[idx - lookback]
    for i in range(idx - lookback + 1, idx + 1):
        ema = (closes[i] - ema) * multiplier + ema

    # Also compute EMA from a few bars ago for direction
    ema_prev = closes[idx - lookback]
    for i in range(idx - lookback + 1, idx - 1):
        ema_prev = (closes[i] - ema_prev) * multiplier + ema_prev

    if closes[idx] <= 0:
        return 0.5

    # Direction: price vs EMA
    deviation = (closes[idx] - ema) / closes[idx]

    # EMA slope
    ema_slope = (ema - ema_prev) / closes[idx] if closes[idx] > 0 else 0

    # Combine: deviation + slope
    combined = deviation * 0.6 + ema_slope * 0.4

    # Scale: ±2% → [0, 1]
    score = 0.5 + combined / 0.04 * 0.5

    return max(0.0, min(1.0, score))
