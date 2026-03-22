"""
Factor: consecutive_volume_increase
Description: Volume increasing for 3+ consecutive days
Category: volume
"""

FACTOR_NAME = "consecutive_volume_increase"
FACTOR_DESC = "Volume increasing for 3+ consecutive days"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Count consecutive days of increasing volume. More = stronger signal."""
    if idx < 3:
        return 0.5

    consecutive = 0
    for i in range(idx, 0, -1):
        if volumes[i] > volumes[i - 1]:
            consecutive += 1
        else:
            break

    # 0 days = 0.5, 3+ days = increasingly bullish
    # Also consider if price is moving up with volume
    price_up = closes[idx] > closes[idx - 1] if idx > 0 else False

    if consecutive >= 5:
        score = 0.9 if price_up else 0.6
    elif consecutive >= 4:
        score = 0.8 if price_up else 0.55
    elif consecutive >= 3:
        score = 0.7 if price_up else 0.55
    elif consecutive >= 2:
        score = 0.6 if price_up else 0.5
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
