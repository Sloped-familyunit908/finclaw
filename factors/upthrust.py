FACTOR_NAME = "upthrust"
FACTOR_DESC = "Bar that marks up above resistance but closes below — bearish trap"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Find resistance: highest close in last 20 days (excluding today)
    resistance = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 1, idx):
        if closes[i] > resistance:
            resistance = closes[i]
    # Upthrust: high > resistance but close < resistance
    if highs[idx] > resistance and closes[idx] < resistance:
        # How far above resistance did it go?
        penetration = (highs[idx] - resistance) / resistance if resistance > 0 else 0
        # How far below did it close?
        rejection = (resistance - closes[idx]) / resistance if resistance > 0 else 0
        # Strong upthrust = bearish
        score = 0.3 - (penetration + rejection) * 5.0
        return max(0.0, min(1.0, score))
    return 0.5
