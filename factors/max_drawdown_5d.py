"""
Factor: max_drawdown_5d
Description: Maximum drawdown in last 5 days
Category: volatility
"""

FACTOR_NAME = "max_drawdown_5d"
FACTOR_DESC = "Maximum drawdown in last 5 days — deeper drawdown = more oversold"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Max peak-to-trough decline in last 5 days. Deep = oversold potential."""
    period = 5
    if idx < period:
        return 0.5

    # Calculate max drawdown in the period
    peak = closes[idx - period + 1]
    max_dd = 0.0

    for i in range(idx - period + 1, idx + 1):
        if closes[i] > peak:
            peak = closes[i]
        if peak > 0:
            dd = (peak - closes[i]) / peak
            if dd > max_dd:
                max_dd = dd

    # Low drawdown = calm = 0.6 (slightly bullish)
    # Medium drawdown (3-5%) = 0.5
    # Deep drawdown (>10%) = 0.7 (oversold, bounce potential)
    # Very deep (>20%) = 0.6 (might be real trouble)

    if max_dd < 0.02:
        score = 0.6  # Calm, steady
    elif max_dd < 0.05:
        score = 0.5
    elif max_dd < 0.10:
        score = 0.55  # Starting to get oversold
    elif max_dd < 0.15:
        score = 0.65  # Oversold bounce potential
    elif max_dd < 0.25:
        score = 0.7  # Deep oversold
    else:
        score = 0.6  # Too deep, might be structural

    return max(0.0, min(1.0, score))
