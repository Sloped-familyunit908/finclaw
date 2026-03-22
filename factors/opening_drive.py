"""
Auto-generated factor: opening_drive
Description: (High - Open) / (High - Low) - how much of range was upward from open
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "opening_drive"
FACTOR_DESC = "(High - Open) / (High - Low) - how much of range was upward from open"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Opening drive: upward portion of range from open proxy."""

    lookback = 5
    if idx < lookback:
        return 0.5

    # Since we don't have explicit open, use previous close as open proxy
    total = 0.0
    valid = 0

    for i in range(idx - lookback + 1, idx + 1):
        day_range = highs[i] - lows[i]
        if day_range <= 0:
            continue
        open_proxy = closes[i - 1] if i > 0 else lows[i]
        upward = highs[i] - open_proxy
        drive = upward / day_range
        total += drive
        valid += 1

    if valid == 0:
        return 0.5

    avg_drive = total / valid
    # Clamp to [0, 1] since drive can exceed 1 or be negative
    return max(0.0, min(1.0, avg_drive))
