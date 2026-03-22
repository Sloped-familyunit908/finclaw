FACTOR_NAME = "mass_index"
FACTOR_DESC = "Mass Index: detects reversals via EMA ratio sum over 25 days"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 35

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    mult = 2.0 / 10.0
    # Compute single EMA and double EMA of (high - low)
    ema1 = highs[idx - LOOKBACK + 1] - lows[idx - LOOKBACK + 1]
    ema2 = ema1
    ratios = []
    for i in range(idx - LOOKBACK + 2, idx + 1):
        hl = highs[i] - lows[i]
        ema1 = (hl - ema1) * mult + ema1
        ema2 = (ema1 - ema2) * mult + ema2
        if ema2 != 0:
            ratios.append(ema1 / ema2)
    if len(ratios) < 25:
        return 0.5
    mass = sum(ratios[-25:])
    # Mass Index > 27 then drops below 26.5 = reversal bulge
    # Typical range: 20-30. Higher = potential reversal
    # If price is below average (downtrend), reversal = bullish
    avg_close = sum(closes[idx - 19:idx + 1]) / 20.0
    if closes[idx] < avg_close:
        # Downtrend — reversal signal is bullish
        score = (mass - 20.0) / 10.0
    else:
        # Uptrend — reversal signal is bearish
        score = 1.0 - (mass - 20.0) / 10.0
    return max(0.0, min(1.0, score))
