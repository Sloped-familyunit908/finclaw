"""
Auto-generated factor: closing_drive
Description: (Close - Low) / (High - Low) - close position within day's range
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "closing_drive"
FACTOR_DESC = "(Close - Low) / (High - Low) - close position within day's range"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Closing drive: where close sits in day's range."""

    lookback = 5
    if idx < lookback:
        return 0.5

    total = 0.0
    valid = 0

    for i in range(idx - lookback + 1, idx + 1):
        day_range = highs[i] - lows[i]
        if day_range <= 0:
            continue
        drive = (closes[i] - lows[i]) / day_range
        total += drive
        valid += 1

    if valid == 0:
        return 0.5

    avg_drive = total / valid
    return max(0.0, min(1.0, avg_drive))
