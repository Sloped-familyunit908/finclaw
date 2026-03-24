"""
Quality Factor: Trend Persistence
===================================
What % of the last 60 days was the stock above its 20-day MA?
If >70% = strong trend stock.  If <30% = chronic underperformer.

Category: quality_filter
"""

FACTOR_NAME = "quality_trend_persistence"
FACTOR_DESC = "Pct of last 60 days above 20-day MA — chronic underperformers score low"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = 60
    ma_window = 20
    min_days = ma_window + lookback

    if idx < min_days:
        # Use whatever is available (at least ma_window + 10)
        if idx < ma_window + 10:
            return 0.5
        lookback = idx - ma_window

    days_above = 0
    for day in range(idx - lookback + 1, idx + 1):
        # Compute 20-day MA at this day
        if day < ma_window:
            continue
        total = 0.0
        for j in range(day - ma_window + 1, day + 1):
            total += closes[j]
        ma20 = total / ma_window
        if closes[day] > ma20:
            days_above += 1

    if lookback <= 0:
        return 0.5

    pct_above = days_above / lookback
    # Map: 0.0 -> 0.0, 0.5 -> 0.5, 1.0 -> 1.0 (linear)
    return max(0.0, min(1.0, pct_above))
