"""
Factor: crypto_obv_divergence
Description: Price up + OBV down (bearish divergence) or vice versa
Category: crypto
"""

FACTOR_NAME = "crypto_obv_divergence"
FACTOR_DESC = "OBV-price divergence detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 0 = bearish divergence, near 1 = bullish divergence."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    # Price direction
    if closes[idx - lookback] <= 0:
        return 0.5
    price_change = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    # OBV direction over lookback
    obv = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]

    avg_vol = sum(volumes[idx - lookback:idx + 1]) / (lookback + 1)
    if avg_vol <= 0:
        return 0.5

    obv_normalized = obv / (avg_vol * lookback)

    # Divergence: price and OBV moving in opposite directions
    if price_change > 0.01 and obv_normalized < -0.1:
        # Bearish divergence
        strength = min(abs(obv_normalized), 1.0)
        return max(0.0, 0.5 - strength * 0.4)
    elif price_change < -0.01 and obv_normalized > 0.1:
        # Bullish divergence
        strength = min(abs(obv_normalized), 1.0)
        return min(1.0, 0.5 + strength * 0.4)

    return 0.5
