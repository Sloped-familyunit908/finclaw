"""
Factor: crypto_volume_price_trend
Description: Price change * volume cumulated over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_volume_price_trend"
FACTOR_DESC = "Price change * volume cumulated over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = positive VPT (bullish), <0.5 = negative."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    vpt = 0.0
    for i in range(idx - lookback, idx):
        if i < 1 or closes[i - 1] <= 0:
            continue
        pct = (closes[i] - closes[i - 1]) / closes[i - 1]
        vpt += pct * volumes[i]

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    normalized = vpt / (avg_vol * lookback * 0.02)
    score = 0.5 + normalized * 0.5
    return max(0.0, min(1.0, score))
