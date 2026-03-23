"""
Factor: crypto_hourly_seasonality
Description: Hour-of-day effect for crypto markets
Category: crypto
"""

FACTOR_NAME = "crypto_hourly_seasonality"
FACTOR_DESC = "Hour-of-day seasonality — US/Asia session transitions create predictable crypto patterns"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Uses idx % 24 as hour-of-day proxy (for 1h data).
    Historically, crypto tends to be more bullish during:
    - US market open (14:00-16:00 UTC) 
    - Asian morning (00:00-02:00 UTC)
    And weaker during low-liquidity periods (06:00-10:00 UTC).
    """
    hour = idx % 24

    # Hourly bias scores based on typical crypto patterns
    # Higher = more bullish historically
    hourly_scores = {
        0: 0.60,   # Asia open - moderate bullish
        1: 0.58,
        2: 0.55,
        3: 0.50,
        4: 0.48,
        5: 0.45,   # Low liquidity
        6: 0.42,
        7: 0.40,   # Weakest
        8: 0.43,
        9: 0.45,
        10: 0.48,  # Europe warming up
        11: 0.50,
        12: 0.52,
        13: 0.55,  # US pre-market
        14: 0.62,  # US market open - strongest
        15: 0.65,
        16: 0.60,
        17: 0.55,
        18: 0.52,
        19: 0.50,
        20: 0.48,  # US evening wind-down
        21: 0.50,
        22: 0.52,
        23: 0.55,  # Pre-Asia
    }

    return hourly_scores.get(hour, 0.5)
