"""
Quality Factor: Price vs 200-day Moving Average
=================================================
Price position relative to 200-bar (or max available) moving average.
Below 200MA by >20% = long-term downtrend = avoid.
Score: (price/MA200 - 0.8) / 0.4 clamped [0,1].

Category: quality_filter
"""

FACTOR_NAME = "quality_price_vs_200d_ma"
FACTOR_DESC = "Price vs 200-day MA — below by >20% means long-term downtrend"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    # Use 200 days or max available (at least 60)
    window = min(200, idx + 1)
    if window < 60:
        return 0.5

    # Compute simple moving average
    total = 0.0
    for i in range(idx - window + 1, idx + 1):
        total += closes[i]
    ma = total / window

    if ma <= 0:
        return 0.5

    ratio = closes[idx] / ma
    # Map ratio: 0.8 -> 0.0, 1.0 -> 0.5, 1.2 -> 1.0
    score = (ratio - 0.8) / 0.4
    return max(0.0, min(1.0, score))
