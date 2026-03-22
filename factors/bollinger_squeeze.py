"""
Factor: bollinger_squeeze
Description: Bollinger Band width at recent minimum (squeeze before breakout)
Category: volatility
"""

FACTOR_NAME = "bollinger_squeeze"
FACTOR_DESC = "Bollinger Band squeeze — narrow bands indicate pending breakout"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Bollinger Band width relative to recent history. Tight = breakout coming."""
    period = 20
    lookback = 60  # Compare bandwidth over 60 days
    if idx < lookback:
        return 0.5

    def calc_bb_width(at_idx):
        """Calculate Bollinger Band width at a given index."""
        ma = sum(closes[at_idx - period + 1:at_idx + 1]) / period
        if ma <= 0:
            return 0.0
        variance = 0.0
        for i in range(at_idx - period + 1, at_idx + 1):
            variance += (closes[i] - ma) ** 2
        variance /= period
        std = variance ** 0.5
        # Bandwidth = (upper - lower) / middle = 4*std / ma
        return (4.0 * std) / ma

    current_width = calc_bb_width(idx)

    # Find min and max bandwidth in lookback period
    min_width = current_width
    max_width = current_width
    for d in range(1, lookback - period + 1):
        w = calc_bb_width(idx - d)
        if w < min_width:
            min_width = w
        if w > max_width:
            max_width = w

    width_range = max_width - min_width
    if width_range <= 0:
        return 0.5

    # How close is current width to the minimum (squeeze)
    squeeze_pct = 1.0 - (current_width - min_width) / width_range

    # High squeeze = high score (breakout likely)
    score = 0.3 + squeeze_pct * 0.6

    return max(0.0, min(1.0, score))
