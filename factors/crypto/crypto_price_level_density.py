"""
Factor: crypto_price_level_density
Description: How many closes are near current price (congestion zone)
Category: crypto
"""

FACTOR_NAME = "crypto_price_level_density"
FACTOR_DESC = "Price level density - congestion zone detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more price levels clustered near current price."""
    lookback = 48
    if idx < lookback:
        return 0.5

    price = closes[idx]
    if price <= 0:
        return 0.5

    # Count closes within 0.5% of current price
    threshold = price * 0.005
    nearby_count = 0

    for i in range(idx - lookback, idx):
        if abs(closes[i] - price) <= threshold:
            nearby_count += 1

    # Normalize: 0 to lookback mapped to 0 to 1
    # High density (many nearby) is notable
    score = nearby_count / (lookback * 0.5)  # Expect at most ~50% to be nearby
    return max(0.0, min(1.0, score))
