"""
Auto-generated factor: price_efficiency
Description: Price efficiency ratio — straight-line distance vs actual path, measures trend clarity
Category: momentum
Generated: seed
"""

FACTOR_NAME = "price_efficiency"
FACTOR_DESC = "Price efficiency ratio — straight-line distance vs actual path, measures trend clarity"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Price efficiency ratio — straight-line distance vs actual path, measures trend clarity"""

    if idx < 10:
        return 0.5
    
    lookback = min(10, idx)
    
    # Net price change (straight line)
    net_change = abs(closes[idx] - closes[idx - lookback])
    
    # Total path length (sum of absolute daily changes)
    total_path = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total_path += abs(closes[i] - closes[i - 1])
    
    if total_path <= 0:
        return 0.5
    
    # Efficiency = net / total, ranges from 0 (choppy) to 1 (straight line)
    efficiency = net_change / total_path
    
    # Direction bonus: upward trend is bullish
    if closes[idx] > closes[idx - lookback]:
        score = 0.5 + efficiency * 0.5  # 0.5 to 1.0
    else:
        score = 0.5 - efficiency * 0.5  # 0.0 to 0.5
    
    return max(0.0, min(1.0, score))

