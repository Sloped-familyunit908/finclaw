"""
Auto-generated factor: trend_acceleration
Description: Is the trend accelerating or decelerating — second derivative of price
Category: momentum
Generated: seed
"""

FACTOR_NAME = "trend_acceleration"
FACTOR_DESC = "Is the trend accelerating or decelerating — second derivative of price"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Compare recent 5-day return vs previous 5-day return."""

    if idx < 10:
        return 0.5

    # Recent 5-day return (idx-4 to idx)
    prev_close_recent = closes[idx - 5]
    if prev_close_recent <= 0:
        return 0.5
    recent_return = (closes[idx] - prev_close_recent) / prev_close_recent

    # Previous 5-day return (idx-9 to idx-5)
    prev_close_earlier = closes[idx - 10]
    if prev_close_earlier <= 0:
        return 0.5
    previous_return = (closes[idx - 5] - prev_close_earlier) / prev_close_earlier

    # Acceleration = recent_return - previous_return
    acceleration = recent_return - previous_return

    # Normalize: acceleration from [-0.10, +0.10] maps to [0, 1]
    score = (acceleration + 0.10) / 0.20
    return max(0.0, min(1.0, score))
