"""
Auto-generated factor: closing_strength
Description: Where does close sit within today's range — institutional buying lifts close to high
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "closing_strength"
FACTOR_DESC = "Where does close sit within today's range — institutional buying lifts close to high"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Average over last 5 days of (close - low) / (high - low)."""

    lookback = 5
    if idx < lookback:
        return 0.5

    total = 0.0
    valid_days = 0

    for i in range(idx - lookback + 1, idx + 1):
        day_range = highs[i] - lows[i]
        if day_range <= 0:
            continue
        strength = (closes[i] - lows[i]) / day_range
        total += strength
        valid_days += 1

    if valid_days == 0:
        return 0.5

    score = total / float(valid_days)
    return max(0.0, min(1.0, score))
