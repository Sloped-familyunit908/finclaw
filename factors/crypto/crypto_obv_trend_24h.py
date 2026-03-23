"""
Factor: crypto_obv_trend_24h
Description: OBV slope over 24 bars (accumulation/distribution)
Category: crypto
"""

FACTOR_NAME = "crypto_obv_trend_24h"
FACTOR_DESC = "OBV slope over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = OBV rising (accumulation)."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    # Build OBV for the lookback window
    obv_start = 0
    obv_end = 0
    for i in range(idx - lookback, idx + 1):
        if i == idx - lookback:
            continue
        if closes[i] > closes[i - 1]:
            obv_end += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_end -= volumes[i]

    # OBV at midpoint
    obv_mid = 0
    half = lookback // 2
    for i in range(idx - lookback, idx - half + 1):
        if i == idx - lookback:
            continue
        if closes[i] > closes[i - 1]:
            obv_mid += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv_mid -= volumes[i]

    avg_vol = sum(volumes[idx - lookback:idx + 1]) / (lookback + 1)
    if avg_vol <= 0:
        return 0.5

    slope = (obv_end - obv_mid) / (avg_vol * lookback + 1e-10)
    score = 0.5 + slope * 2.0
    return max(0.0, min(1.0, score))
