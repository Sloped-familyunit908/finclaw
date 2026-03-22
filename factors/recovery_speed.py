"""
Factor: recovery_speed
Description: How fast is price recovering from recent low
Category: momentum
"""

FACTOR_NAME = "recovery_speed"
FACTOR_DESC = "Recovery speed from recent low — fast recovery = strong demand"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Measure how quickly price is recovering from its 20-day low."""
    lookback = 20
    if idx < lookback:
        return 0.5

    # Find the recent low and when it occurred
    recent_low = lows[idx - lookback + 1]
    low_idx = idx - lookback + 1
    for i in range(idx - lookback + 1, idx + 1):
        if lows[i] < recent_low:
            recent_low = lows[i]
            low_idx = i

    if recent_low <= 0:
        return 0.5

    # Days since low
    days_since_low = idx - low_idx
    if days_since_low == 0:
        # At the low right now
        return 0.35

    # Recovery percentage
    recovery_pct = (closes[idx] - recent_low) / recent_low

    # Speed = recovery per day
    speed = recovery_pct / days_since_low

    # Fast recovery (>1% per day) = very bullish
    # Slow recovery (<0.2% per day) = weak
    if speed > 0.01:
        score = 0.85
    elif speed > 0.005:
        score = 0.7
    elif speed > 0.002:
        score = 0.6
    elif speed > 0:
        score = 0.55
    else:
        # Still declining
        score = 0.35

    return max(0.0, min(1.0, score))
