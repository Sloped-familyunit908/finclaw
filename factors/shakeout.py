FACTOR_NAME = "shakeout"
FACTOR_DESC = "Bar that dips below support but closes above — bullish shakeout"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Find support: lowest close in last 20 days (excluding today)
    support = closes[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 1, idx):
        if closes[i] < support:
            support = closes[i]
    # Shakeout: low < support but close > support
    if lows[idx] < support and closes[idx] > support:
        if support == 0:
            return 0.5
        penetration = (support - lows[idx]) / support
        recovery = (closes[idx] - support) / support
        # Strong shakeout = bullish
        score = 0.7 + (penetration + recovery) * 5.0
        return max(0.0, min(1.0, score))
    return 0.5
