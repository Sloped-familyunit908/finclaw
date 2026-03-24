"""
Factor: bottom_volume_decline_stabilize
Description: Volume declining while price stops making new lows — selling exhaustion
Category: bottom_confirmation
"""

FACTOR_NAME = "bottom_volume_decline_stabilize"
FACTOR_DESC = "Volume declining 3+ days while price stabilizes — selling exhaustion signal"
FACTOR_CATEGORY = "bottom_confirmation"


def compute(closes, highs, lows, volumes, idx):
    """Detect volume declining over 3+ days while price stops making new lows.

    Volume drying up after a crash = sellers are exhausted. If price also
    stops making new lows, it's a strong bottom formation signal.

    Score 1.0 if:
    - Volume has decreased each of last 3 days
    - Price didn't make a new low in last 2 days
    """
    if idx < 5:
        return 0.5

    # Check volume declining for last 3 days
    vol_declining = True
    for i in range(idx - 2, idx + 1):
        if i < 1:
            vol_declining = False
            break
        if volumes[i] >= volumes[i - 1]:
            vol_declining = False
            break

    if not vol_declining:
        # Check if at least 2 of last 3 days had declining volume
        decline_count = 0
        for i in range(idx - 1, idx + 1):
            if i >= 1 and volumes[i] < volumes[i - 1]:
                decline_count += 1
        if decline_count < 2:
            return 0.5

    # Check price stabilization: no new low in last 2 days
    # Compare today's and yesterday's low against the low from 3 days ago
    lookback_low = min(lows[idx - 4:idx - 1]) if idx >= 4 else lows[idx - 1]
    price_stabilized = (lows[idx] >= lookback_low * 0.995 and
                        lows[idx - 1] >= lookback_low * 0.995)

    if not price_stabilized:
        # Price still making new lows — not stabilized yet
        if vol_declining:
            return 0.6  # volume declining is still somewhat positive
        return 0.5

    # Both conditions met
    if vol_declining:
        # Perfect signal: volume declining 3 days + price stabilized
        score = 1.0
    else:
        # Partial: 2 of 3 days declining + price stabilized
        score = 0.8

    # Bonus: volume is significantly below average (extreme dry-up)
    if idx >= 20:
        avg_vol = sum(volumes[idx - 19:idx + 1]) / 20
        if avg_vol > 0:
            vol_ratio = volumes[idx] / avg_vol
            if vol_ratio < 0.5:
                score = min(1.0, score + 0.1)

    return max(0.0, min(1.0, score))
