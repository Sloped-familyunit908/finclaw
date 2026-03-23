"""
Factor: crypto_distribution_pattern
Description: Rising price with declining candle body size — distribution
Category: crypto
"""

FACTOR_NAME = "crypto_distribution_pattern"
FACTOR_DESC = "Rising price with declining candle body size — distribution pattern (bearish)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = distribution detected (bearish)."""
    lookback = 12
    if idx < lookback:
        return 0.5

    # Check if price is rising over the lookback
    if closes[idx - lookback] <= 0:
        return 0.5
    price_change = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    if price_change <= 0.01:
        # Price not rising enough to detect distribution
        return 0.5

    # Compute candle body sizes (abs(close - open), approximated as abs(close - prev_close))
    first_half_bodies = []
    second_half_bodies = []
    half = lookback // 2

    for i in range(idx - lookback + 1, idx - half + 1):
        body = abs(closes[i] - closes[i - 1])
        first_half_bodies.append(body)

    for i in range(idx - half + 1, idx + 1):
        body = abs(closes[i] - closes[i - 1])
        second_half_bodies.append(body)

    if not first_half_bodies or not second_half_bodies:
        return 0.5

    avg_body_1 = sum(first_half_bodies) / len(first_half_bodies)
    avg_body_2 = sum(second_half_bodies) / len(second_half_bodies)

    if avg_body_1 <= 0:
        return 0.5

    # Body declining while price rising = distribution
    body_decline = (avg_body_1 - avg_body_2) / avg_body_1

    if body_decline <= 0:
        return 0.5

    # Scale: 30%+ decline in body size = strong distribution signal
    strength = min(body_decline / 0.3, 1.0)
    # Also factor in how much price has risen (stronger signal if bigger rise)
    price_factor = min(price_change / 0.05, 1.0)

    score = 0.5 - strength * price_factor * 0.4

    return max(0.0, min(1.0, score))
