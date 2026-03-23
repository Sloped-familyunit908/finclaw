"""
Factor: crypto_round_number_proximity
Description: Distance to nearest round number (100, 1000, 10000 etc)
Category: crypto
"""

FACTOR_NAME = "crypto_round_number_proximity"
FACTOR_DESC = "Distance to nearest round number (100, 1000, 10000 etc)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = very close to a round number."""
    if idx < 1:
        return 0.5

    price = closes[idx - 1]
    if price <= 0:
        return 0.5

    # Determine round number magnitude based on price
    if price >= 10000:
        round_size = 1000
    elif price >= 1000:
        round_size = 100
    elif price >= 100:
        round_size = 10
    elif price >= 10:
        round_size = 1
    else:
        round_size = 0.1

    nearest_round = round(price / round_size) * round_size
    distance = abs(price - nearest_round) / round_size

    score = max(0.0, 1.0 - distance * 2.0)
    return max(0.0, min(1.0, score))
