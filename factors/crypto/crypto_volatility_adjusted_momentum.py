"""
Factor: crypto_volatility_adjusted_momentum
Description: Momentum / ATR (risk-adjusted momentum)
Category: crypto
"""

FACTOR_NAME = "crypto_volatility_adjusted_momentum"
FACTOR_DESC = "Momentum / ATR (risk-adjusted momentum)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = positive risk-adjusted momentum."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    # Momentum
    if closes[idx - lookback - 1] <= 0:
        return 0.5
    momentum = (closes[idx - 1] - closes[idx - lookback - 1]) / closes[idx - lookback - 1]

    # ATR
    atr_sum = 0.0
    for i in range(idx - lookback, idx):
        tr = highs[i] - lows[i]
        if i > 0:
            tr = max(tr, abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        atr_sum += tr
    atr = atr_sum / lookback

    if atr <= 0 or closes[idx - 1] <= 0:
        return 0.5

    atr_pct = atr / closes[idx - 1]
    if atr_pct <= 0:
        return 0.5

    adj_momentum = momentum / atr_pct
    score = 0.5 + adj_momentum * 0.1
    return max(0.0, min(1.0, score))
