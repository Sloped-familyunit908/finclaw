"""
Factor: crypto_pin_bar
Description: Long wick in one direction, rejection signal
Category: crypto
"""

FACTOR_NAME = "crypto_pin_bar"
FACTOR_DESC = "Pin bar pattern — long wick rejection signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = bullish pin bar (lower wick reject), Low = bearish pin bar."""
    if idx < 24:
        return 0.5

    rng = highs[idx] - lows[idx]
    if rng <= 0:
        return 0.5

    open_est = closes[idx - 1]
    body = abs(closes[idx] - open_est)
    upper_wick = highs[idx] - max(closes[idx], open_est)
    lower_wick = min(closes[idx], open_est) - lows[idx]

    # Pin bar needs small body and one dominant wick
    if body / rng > 0.33:
        return 0.5

    # Bullish pin bar: lower wick > 60% of range
    if lower_wick / rng > 0.60:
        strength = lower_wick / rng
        score = 0.5 + (strength - 0.6) * 2.5  # Scale 0.6→0.5, 1.0→1.5 clamped
        return max(0.0, min(1.0, score))

    # Bearish pin bar: upper wick > 60% of range
    if upper_wick / rng > 0.60:
        strength = upper_wick / rng
        score = 0.5 - (strength - 0.6) * 2.5
        return max(0.0, min(1.0, score))

    return 0.5
