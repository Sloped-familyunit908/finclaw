"""
Factor: crypto_head_shoulders
Description: Three peaks pattern detection (simplified) — reversal signal
Category: crypto
"""

FACTOR_NAME = "crypto_head_shoulders"
FACTOR_DESC = "Simplified head and shoulders pattern detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = head & shoulders top (bearish), High = inverse (bullish)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Find local maxima
    local_maxs = []
    for i in range(idx - lookback + 2, idx - 1):
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i + 1]:
            if highs[i] >= highs[i - 2]:
                local_maxs.append((i, highs[i]))

    if len(local_maxs) < 3:
        return 0.5

    # Check last 3 peaks: middle should be highest (head & shoulders top)
    # Or middle lowest (inverse head & shoulders)
    for k in range(len(local_maxs) - 2):
        p1 = local_maxs[k]
        p2 = local_maxs[k + 1]
        p3 = local_maxs[k + 2]

        # Minimum separation
        if p2[0] - p1[0] < 6 or p3[0] - p2[0] < 6:
            continue

        # Head & shoulders top: middle peak highest, shoulders similar
        if p2[1] > p1[1] and p2[1] > p3[1]:
            if p1[1] > 0:
                shoulder_diff = abs(p1[1] - p3[1]) / p1[1]
                if shoulder_diff < 0.03:  # Shoulders within 3%
                    head_prominence = (p2[1] - max(p1[1], p3[1])) / p2[1]
                    strength = min(head_prominence * 20.0, 1.0)
                    return max(0.0, min(1.0, 0.5 - strength * 0.4))

    # Check for inverse pattern with lows
    local_mins = []
    for i in range(idx - lookback + 2, idx - 1):
        if lows[i] <= lows[i - 1] and lows[i] <= lows[i + 1]:
            if lows[i] <= lows[i - 2]:
                local_mins.append((i, lows[i]))

    if len(local_mins) >= 3:
        for k in range(len(local_mins) - 2):
            p1 = local_mins[k]
            p2 = local_mins[k + 1]
            p3 = local_mins[k + 2]
            if p2[0] - p1[0] < 6 or p3[0] - p2[0] < 6:
                continue
            if p2[1] < p1[1] and p2[1] < p3[1]:
                if p1[1] > 0:
                    shoulder_diff = abs(p1[1] - p3[1]) / p1[1]
                    if shoulder_diff < 0.03:
                        head_prominence = (min(p1[1], p3[1]) - p2[1]) / p2[1] if p2[1] > 0 else 0
                        strength = min(head_prominence * 20.0, 1.0)
                        return max(0.0, min(1.0, 0.5 + strength * 0.4))

    return 0.5
