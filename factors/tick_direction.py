"""
Auto-generated factor: tick_direction
Description: Close above or below midpoint of day's range (uptick/downtick proxy)
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "tick_direction"
FACTOR_DESC = "Close above or below midpoint of day's range (uptick/downtick proxy)"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Tick direction: where close sits vs midpoint of range."""

    lookback = 5
    if idx < lookback:
        return 0.5

    total = 0.0
    valid = 0
    for i in range(idx - lookback + 1, idx + 1):
        day_range = highs[i] - lows[i]
        if day_range <= 0:
            continue
        midpoint = (highs[i] + lows[i]) / 2.0
        position = (closes[i] - midpoint) / (day_range / 2.0)
        total += position
        valid += 1

    if valid == 0:
        return 0.5

    avg_position = total / valid
    # Map from [-1, 1] to [0, 1]
    score = 0.5 + avg_position * 0.5
    return max(0.0, min(1.0, score))
