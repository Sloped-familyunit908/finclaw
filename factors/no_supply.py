FACTOR_NAME = "no_supply"
FACTOR_DESC = "Down bar with narrow spread and below-average volume — no real supply, bullish"
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
    # Narrow spread?
    spread = highs[idx] - lows[idx]
    avg_spread = 0.0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        avg_spread += highs[i] - lows[i]
    avg_spread /= LOOKBACK
    # Below-average volume?
    avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
    narrow = spread < avg_spread * 0.7 if avg_spread > 0 else False
    low_vol = volumes[idx] < avg_vol * 0.8 if avg_vol > 0 else False
    if narrow and low_vol:
        # No supply signal — bullish
        score = 0.8
    elif narrow or low_vol:
        score = 0.65
    else:
        score = 0.5
    return max(0.0, min(1.0, score))
