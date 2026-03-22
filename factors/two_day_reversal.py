"""
Auto-generated factor: two_day_reversal
Description: Big down day followed by big up day (or vice versa)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "two_day_reversal"
FACTOR_DESC = "Big down day followed by big up day (or vice versa)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect two-day reversal patterns."""

    if idx < 3:
        return 0.5

    # Yesterday's return
    ret_yest = (closes[idx - 1] - closes[idx - 2]) / closes[idx - 2] if closes[idx - 2] > 0 else 0.0
    # Today's return
    ret_today = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    threshold = 0.015  # 1.5% move

    # Bullish reversal: big down yesterday, big up today
    if ret_yest < -threshold and ret_today > threshold:
        strength = abs(ret_today) * 10.0
        score = 0.5 + strength
        return max(0.0, min(1.0, score))

    # Bearish reversal: big up yesterday, big down today
    if ret_yest > threshold and ret_today < -threshold:
        strength = abs(ret_today) * 10.0
        score = 0.5 - strength
        return max(0.0, min(1.0, score))

    return 0.5
