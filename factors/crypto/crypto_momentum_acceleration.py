"""
Factor: crypto_momentum_acceleration
Description: Rate of change of momentum (second derivative of price)
Category: crypto
"""

FACTOR_NAME = "crypto_momentum_acceleration"
FACTOR_DESC = "Momentum acceleration — second derivative of price; accelerating = trend, decelerating = reversal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Computes the second derivative of price (acceleration of momentum).
    Uses 12h and 24h momentum for crypto-appropriate timeframes.
    
    Positive acceleration = trend strengthening → bullish
    Negative acceleration = trend weakening → bearish
    """
    period = 12  # 12 hours for crypto
    if idx < period * 2:
        return 0.5

    prev = closes[idx - period]
    prev_prev = closes[idx - period * 2]

    if prev <= 0 or prev_prev <= 0:
        return 0.5

    # Current momentum (12h ROC)
    current_momentum = (closes[idx] - prev) / prev

    # Previous momentum (12h ROC, 12h ago)
    prev_momentum = (prev - prev_prev) / prev_prev

    # Acceleration = change in momentum
    accel = current_momentum - prev_momentum

    # Normalize: -0.04 → 0.0, 0 → 0.5, +0.04 → 1.0
    score = 0.5 + accel * 12.5
    return max(0.0, min(1.0, score))
