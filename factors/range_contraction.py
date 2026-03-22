"""
Auto-generated factor: range_contraction
Description: Range contraction — narrowing daily range often precedes breakout
Category: volatility
Generated: seed
"""

FACTOR_NAME = "range_contraction"
FACTOR_DESC = "Range contraction — narrowing daily range often precedes breakout"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Range contraction — narrowing daily range often precedes breakout"""

    if idx < 20:
        return 0.5
    
    # Average True Range ratio: recent 5 day vs 20 day
    def true_range(i):
        if i < 1:
            return highs[i] - lows[i]
        return max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
    
    atr_5 = sum(true_range(idx - j) for j in range(5)) / 5.0
    atr_20 = sum(true_range(idx - j) for j in range(20)) / 20.0
    
    if atr_20 <= 0:
        return 0.5
    
    ratio = atr_5 / atr_20
    # Contraction (ratio < 1) is bullish (breakout coming)
    # ratio 0.3 -> score 1.0, ratio 1.5 -> score 0.0
    score = 1.0 - (ratio - 0.3) / 1.2
    return max(0.0, min(1.0, score))

