"""
Factor: breadth_sector_rotation
Description: Hot vs cold price range grouping — sector rotation proxy
Category: market_breadth
"""

FACTOR_NAME = "breadth_sector_rotation"
FACTOR_DESC = "Price range group momentum — proxy for sector rotation health"
FACTOR_CATEGORY = "market_breadth"


def compute(closes, highs, lows, volumes, idx):
    """Proxy for sector rotation using price range momentum.
    Stocks in a strong momentum regime (recent return positive,
    volume confirming) are in "hot" sectors.
    Uses the stock's own momentum relative to its historical pattern.
    """
    if idx < 20:
        return 0.5

    # Short-term momentum (5d)
    if closes[idx - 5] <= 0:
        return 0.5
    mom_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5]

    # Medium-term momentum (20d)
    if closes[idx - 20] <= 0:
        return 0.5
    mom_20d = (closes[idx] - closes[idx - 20]) / closes[idx - 20]

    # "Hot sector" proxy: both short and medium momentum positive
    if mom_5d > 0 and mom_20d > 0:
        # Hot — momentum is aligned
        strength = min(1.0, (mom_5d + mom_20d) / 0.15)
        score = 0.6 + 0.4 * strength
    elif mom_5d > 0 and mom_20d <= 0:
        # Rotating in — short momentum turning positive
        score = 0.55
    elif mom_5d <= 0 and mom_20d > 0:
        # Rotating out — short momentum turning negative
        score = 0.45
    else:
        # Cold — both negative
        weakness = min(1.0, abs(mom_5d + mom_20d) / 0.15)
        score = 0.4 - 0.4 * weakness

    return max(0.0, min(1.0, score))
