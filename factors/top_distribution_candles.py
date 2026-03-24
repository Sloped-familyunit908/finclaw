"""
Factor: top_distribution_candles
Description: Multiple doji/spinning top candles near highs — distribution
Category: top_escape
"""

FACTOR_NAME = "top_distribution_candles"
FACTOR_DESC = "Multiple small-body candles near 20-day high — indecision/distribution"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Count small-body candles (body < 30% of range) in last 5 bars
    when price is near 20-day high. Multiple doji/spinning tops at highs
    signal distribution and indecision.
    """
    if idx < 20:
        return 0.5

    # Check if near 20-day high
    high_20d = max(highs[idx - 19 : idx + 1])
    if high_20d <= 0:
        return 0.5

    price_nearness = closes[idx] / high_20d
    if price_nearness < 0.95:
        return 0.5  # Not near highs

    # Count small-body candles in last 5 bars
    small_body_count = 0
    lookback = min(5, idx + 1)

    for i in range(idx - lookback + 1, idx + 1):
        candle_range = highs[i] - lows[i]
        if candle_range <= 0:
            small_body_count += 1  # Doji
            continue

        # Use open approximation: open ≈ previous close
        if i > 0:
            body = abs(closes[i] - closes[i - 1])
        else:
            body = 0

        body_ratio = body / candle_range
        if body_ratio < 0.30:
            small_body_count += 1

    if small_body_count < 2:
        return 0.5

    # Score based on count of distribution candles
    nearness_bonus = (price_nearness - 0.95) / 0.05  # 0 to 1

    if small_body_count >= 4:
        base = 0.9
    elif small_body_count >= 3:
        base = 0.8
    else:  # 2
        base = 0.65

    score = base * (0.7 + 0.3 * nearness_bonus)

    return max(0.0, min(1.0, score))
