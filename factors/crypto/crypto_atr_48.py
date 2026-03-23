"""
Factor: crypto_atr_48
Description: ATR over 48 bars (slow volatility)
Category: crypto
"""

FACTOR_NAME = "crypto_atr_48"
FACTOR_DESC = "Average True Range over 48 bars (slow volatility)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = higher volatility."""
    period = 48
    if idx < period + 1:
        return 0.5

    atr_sum = 0.0
    for i in range(idx - period + 1, idx + 1):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        atr_sum += max(tr1, tr2, tr3)

    atr = atr_sum / period

    if closes[idx] <= 0:
        return 0.5

    atr_pct = atr / closes[idx]

    # Typical range: 0.5% to 5% for crypto
    score = atr_pct / 0.05
    return max(0.0, min(1.0, score))
