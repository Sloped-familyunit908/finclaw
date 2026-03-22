"""
Factor: acceleration
Description: Change in momentum (2nd derivative)
Category: momentum
"""

FACTOR_NAME = "acceleration"
FACTOR_DESC = "Price acceleration — change in momentum (2nd derivative of price)"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """2nd derivative: momentum of momentum. Positive = accelerating up."""
    period = 5
    if idx < period * 2:
        return 0.5

    prev = closes[idx - period]
    prev_prev = closes[idx - period * 2]

    if prev <= 0 or prev_prev <= 0:
        return 0.5

    # Current momentum (5-day ROC)
    current_momentum = (closes[idx] - prev) / prev

    # Previous momentum (5-day ROC, 5 days ago)
    prev_momentum = (prev - prev_prev) / prev_prev

    # Acceleration = change in momentum
    accel = current_momentum - prev_momentum

    # Normalize: -0.05 → 0.0, 0 → 0.5, +0.05 → 1.0
    score = 0.5 + accel * 10.0

    return max(0.0, min(1.0, score))
