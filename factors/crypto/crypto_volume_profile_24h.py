"""
Factor: crypto_volume_profile_24h
Description: Volume distribution across last 24 candles — accumulation vs distribution
Category: crypto
"""

FACTOR_NAME = "crypto_volume_profile_24h"
FACTOR_DESC = "24h volume profile — detects accumulation (buying on dips) vs distribution (selling on rallies)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Analyzes volume distribution relative to price movement over 24h.
    Accumulation: high volume on down moves, low volume on up moves → bullish (smart money buying)
    Distribution: high volume on up moves, low volume on down moves → bearish (smart money selling)
    
    Similar to Chaikin Money Flow adapted for crypto's 24/7 nature.
    """
    lookback = 24
    if idx < lookback:
        return 0.5

    up_volume = 0.0
    down_volume = 0.0
    total_volume = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        vol = volumes[i]
        total_volume += vol

        high = highs[i]
        low = lows[i]
        close = closes[i]

        # Money flow multiplier: where close falls in high-low range
        hl_range = high - low
        if hl_range > 0:
            mf_multiplier = ((close - low) - (high - close)) / hl_range
        else:
            mf_multiplier = 0.0

        if mf_multiplier > 0:
            up_volume += vol * mf_multiplier
        else:
            down_volume += vol * abs(mf_multiplier)

    if total_volume <= 0:
        return 0.5

    # Net flow ratio
    net_flow = (up_volume - down_volume) / total_volume

    # net_flow ranges roughly -1 to +1
    # Map to 0-1: -1 → 0.0, 0 → 0.5, +1 → 1.0
    score = 0.5 + net_flow * 0.5
    return max(0.0, min(1.0, score))
