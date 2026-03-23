"""
Factor: crypto_hammer_signal
Description: Hammer pattern — long lower wick, small body, at potential bottom
Category: crypto
"""

FACTOR_NAME = "crypto_hammer_signal"
FACTOR_DESC = "Hammer candlestick pattern detection — bullish reversal signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = hammer pattern at bottom (bullish)."""
    if idx < 24:
        return 0.5

    rng = highs[idx] - lows[idx]
    if rng <= 0:
        return 0.5

    # Estimate open
    open_est = closes[idx - 1]
    body = abs(closes[idx] - open_est)
    upper_wick = highs[idx] - max(closes[idx], open_est)
    lower_wick = min(closes[idx], open_est) - lows[idx]

    # Hammer: lower wick > 2x body, upper wick < body, small body
    is_hammer = (lower_wick > body * 2.0 and
                 upper_wick < body * 1.0 and
                 body / rng < 0.33)

    if not is_hammer:
        return 0.5

    # Check if at potential bottom (near 24h low)
    low_24h = min(lows[idx - 24:idx])
    if low_24h <= 0:
        return 0.5

    near_bottom = (lows[idx] - low_24h) / low_24h < 0.01

    if near_bottom:
        # Strong hammer at bottom
        strength = min(lower_wick / rng, 1.0)
        score = 0.5 + strength * 0.4
        return max(0.0, min(1.0, score))

    return 0.55  # Weak hammer signal
