"""
Factor: sector_momentum_rank
Description: Rank stock's momentum within its price-range peer group
Category: rotation
"""

FACTOR_NAME = "sector_momentum_rank"
FACTOR_DESC = "Sector momentum rank — momentum rank within price-range peer group proxy"
FACTOR_CATEGORY = "rotation"


def compute(closes, highs, lows, volumes, idx):
    """
    Sector momentum rank proxy using price-range based grouping.
    
    Since we don't have sector labels, we use the stock's own
    price dynamics as a proxy: compare short-term momentum (5-day)
    against medium-term momentum (20-day).
    
    If short-term momentum is accelerating relative to medium-term,
    the stock is gaining relative strength within its "group".
    
    Score > 0.5 = accelerating momentum (leading)
    Score < 0.5 = decelerating momentum (lagging)
    """
    if idx < 20:
        return 0.5

    # 5-day momentum (recent)
    if closes[idx - 5] <= 0:
        return 0.5
    mom_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5]

    # 20-day momentum (medium-term)
    if closes[idx - 20] <= 0:
        return 0.5
    mom_20d = (closes[idx] - closes[idx - 20]) / closes[idx - 20]

    # Expected 5-day based on 20-day rate
    # If 20-day return is R over 20 days, expected 5-day is roughly R/4
    expected_5d = mom_20d / 4.0

    # Momentum acceleration
    acceleration = mom_5d - expected_5d

    # Also consider volume confirmation
    recent_vol = 0.0
    older_vol = 0.0
    for i in range(idx - 4, idx + 1):
        recent_vol += volumes[i]
    for i in range(idx - 19, idx - 14):
        older_vol += volumes[i]

    recent_avg_vol = recent_vol / 5.0
    older_avg_vol = older_vol / 5.0

    vol_boost = 1.0
    if older_avg_vol > 0:
        vol_ratio = recent_avg_vol / older_avg_vol
        if vol_ratio > 1.5:
            vol_boost = 1.2  # volume confirms momentum
        elif vol_ratio < 0.5:
            vol_boost = 0.8  # weak volume dampens signal

    # Normalize acceleration: +-5% maps to [0, 1]
    score = 0.5 + (acceleration * vol_boost) / 0.10

    return max(0.0, min(1.0, score))
