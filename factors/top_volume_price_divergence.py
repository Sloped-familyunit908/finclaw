"""
Factor: top_volume_price_divergence
Description: Price rising but volume declining — smart money exiting
Category: top_escape
"""

FACTOR_NAME = "top_volume_price_divergence"
FACTOR_DESC = "Price rising on declining volume — rising on thin air, distribution"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Price rising but volume declining over 5+ days.
    'Rising on thin air' = smart money exiting while retail pushes price up.
    """
    lookback = 10
    if idx < lookback:
        return 0.5

    # Check price trend over last 5-10 days (rising)
    price_rising_count = 0
    vol_declining_count = 0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            price_rising_count += 1
        if volumes[i] < volumes[i - 1] and volumes[i - 1] > 0:
            vol_declining_count += 1

    # Need at least 5 of last 10 days with rising price
    if price_rising_count < 5:
        return 0.5

    # Check overall price direction
    price_change = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0
    if price_change <= 0:
        return 0.5

    # Check if volume is trending down while price goes up
    if vol_declining_count < 5:
        return 0.5

    # Calculate volume trend slope (simple: compare first half avg to second half avg)
    first_half_vol = sum(volumes[idx - lookback + 1 : idx - lookback // 2 + 1]) / (lookback // 2)
    second_half_vol = sum(volumes[idx - lookback // 2 + 1 : idx + 1]) / (lookback // 2)

    if first_half_vol <= 0:
        return 0.5

    vol_decline_ratio = 1.0 - (second_half_vol / first_half_vol)

    if vol_decline_ratio <= 0:
        return 0.5  # Volume not actually declining

    # Score: more divergence (price up + volume down) = higher score
    price_score = min(1.0, price_change / 0.10)  # 10% rise = max
    vol_score = min(1.0, vol_decline_ratio / 0.50)  # 50% vol decline = max

    score = 0.6 + 0.4 * price_score * vol_score

    return max(0.0, min(1.0, score))
