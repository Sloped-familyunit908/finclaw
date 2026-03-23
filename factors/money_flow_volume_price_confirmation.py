"""
Factor: volume_price_confirmation
Description: Price-volume alignment — price up on increasing volume = strong, price up on decreasing volume = weak
Category: flow
"""

FACTOR_NAME = "volume_price_confirmation"
FACTOR_DESC = "Price-volume confirmation — score based on alignment of price direction and volume trend"
FACTOR_CATEGORY = "flow"


def compute(closes, highs, lows, volumes, idx):
    """
    Volume-price confirmation over 5-10 days.
    
    Price up + volume up = bullish confirmation (score > 0.5)
    Price up + volume down = weak rally (score ~ 0.4)
    Price down + volume up = distribution (score ~ 0.3)
    Price down + volume down = weak decline / selling exhaustion (score ~ 0.6)
    """
    lookback = 10

    if idx < lookback:
        return 0.5

    confirmation_score = 0.0
    total_weight = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        if i < 1:
            continue

        price_change = closes[i] - closes[i - 1]
        vol_change = volumes[i] - volumes[i - 1]

        price_up = price_change > 0
        vol_up = vol_change > 0

        # Recency weight: more recent days matter more
        recency = 1.0 + (i - (idx - lookback + 1)) / lookback
        total_weight += recency

        if price_up and vol_up:
            # Bullish confirmation — strong move
            confirmation_score += 1.0 * recency
        elif price_up and not vol_up:
            # Weak rally — price up but volume declining
            confirmation_score += 0.3 * recency
        elif not price_up and vol_up:
            # Distribution — selling on high volume
            confirmation_score -= 0.5 * recency
        else:
            # Price down, volume down — selling exhaustion, mildly bullish
            confirmation_score += 0.2 * recency

    if total_weight <= 0:
        return 0.5

    # Normalize to [-1, 1]
    normalized = confirmation_score / total_weight

    # Map to [0, 1]
    score = 0.5 + normalized * 0.5

    return max(0.0, min(1.0, score))
