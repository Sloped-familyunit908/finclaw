"""
Factor: crypto_vol_of_vol
Description: Volatility of ATR itself (meta-volatility)
Category: crypto
"""

FACTOR_NAME = "crypto_vol_of_vol"
FACTOR_DESC = "Volatility of ATR - meta-volatility indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = ATR itself is volatile (unstable regime)."""
    lookback = 24
    atr_period = 12
    if idx < atr_period + lookback + 1:
        return 0.5

    # Compute ATR at multiple points
    atr_values = []
    for t in range(idx - lookback + 1, idx + 1):
        if t < atr_period + 1:
            continue
        atr_sum = 0.0
        for i in range(t - atr_period + 1, t + 1):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            atr_sum += max(tr1, tr2, tr3)
        atr_values.append(atr_sum / atr_period)

    if len(atr_values) < 2:
        return 0.5

    mean_atr = sum(atr_values) / len(atr_values)
    if mean_atr <= 0:
        return 0.5

    variance = sum((a - mean_atr) ** 2 for a in atr_values) / len(atr_values)
    vol_of_vol = (variance ** 0.5) / mean_atr

    # Typical range: 0 to 0.5
    score = vol_of_vol / 0.5
    return max(0.0, min(1.0, score))
