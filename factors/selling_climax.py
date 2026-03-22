FACTOR_NAME = "selling_climax"
FACTOR_DESC = "Ultra-wide spread down bar on ultra-high volume — exhaustion bottom, bullish"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if idx < 1 or closes[idx - 1] == 0:
        return 0.5
    # Down bar?
    is_down = closes[idx] < closes[idx - 1]
    if not is_down:
        return 0.5
    # Ultra-wide spread
    spread = highs[idx] - lows[idx]
    avg_spread = 0.0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        avg_spread += highs[i] - lows[i]
    avg_spread /= LOOKBACK
    # Ultra-high volume
    avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
    if avg_spread == 0 or avg_vol == 0:
        return 0.5
    spread_ratio = spread / avg_spread
    vol_ratio = volumes[idx] / avg_vol
    if spread_ratio > 2.0 and vol_ratio > 2.0:
        # Selling climax — exhaustion bottom, bullish
        score = 0.85
    elif spread_ratio > 1.5 and vol_ratio > 1.5:
        score = 0.7
    else:
        score = 0.5
    return max(0.0, min(1.0, score))
