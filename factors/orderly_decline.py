"""
Auto-generated factor: orderly_decline
Description: Steady decline with decreasing volume (orderly, not panic - sets up reversal)
Category: composite
Generated: seed
"""

FACTOR_NAME = "orderly_decline"
FACTOR_DESC = "Steady decline with decreasing volume (orderly, not panic - sets up reversal)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Orderly decline: steady down on declining volume."""

    lookback = 15
    if idx < lookback:
        return 0.5

    # Check price declining
    down_days = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] < closes[i - 1]:
            down_days += 1
    down_ratio = down_days / float(lookback)

    # Total decline
    total_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0.0

    # Volume trend: declining
    vol_first_half = 0.0
    vol_second_half = 0.0
    half = lookback // 2
    for i in range(idx - lookback + 1, idx - lookback + 1 + half):
        vol_first_half += volumes[i]
    for i in range(idx - half + 1, idx + 1):
        vol_second_half += volumes[i]

    volume_declining = vol_second_half < vol_first_half * 0.8

    # Orderly decline: steady down + declining volume = selling exhaustion
    if total_return < -0.03 and down_ratio > 0.55 and volume_declining:
        # Bullish setup: orderly decline suggesting reversal
        score = 0.7 + abs(total_return) * 2.0
        return max(0.0, min(1.0, score))
    elif total_return < -0.03 and volume_declining:
        return 0.6

    return 0.5
