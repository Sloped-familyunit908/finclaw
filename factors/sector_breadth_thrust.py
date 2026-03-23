"""
Factor: breadth_thrust
Description: Market breadth indicator — % of positive 5-day returns proxy
Category: rotation
"""

FACTOR_NAME = "breadth_thrust"
FACTOR_DESC = "Breadth thrust — market breadth proxy from rolling positive-return days ratio"
FACTOR_CATEGORY = "rotation"


def compute(closes, highs, lows, volumes, idx):
    """
    Market breadth proxy using single-stock data.
    
    Since we only have one stock's data, we approximate "breadth" by
    measuring the consistency of positive returns across multiple
    timeframes — a stock in a strong market tends to have positive
    returns across many sub-windows.
    
    Check 5-day returns at multiple overlapping windows:
    - [idx-4:idx], [idx-5:idx-1], [idx-6:idx-2], etc.
    
    High % of positive sub-windows = strong breadth
    Low % = weak breadth
    """
    num_windows = 10
    window_size = 5

    if idx < num_windows + window_size:
        return 0.5

    positive_windows = 0
    total_windows = 0

    for offset in range(num_windows):
        end = idx - offset
        start = end - window_size

        if start < 0 or closes[start] <= 0:
            continue

        ret = (closes[end] - closes[start]) / closes[start]
        total_windows += 1

        if ret > 0:
            positive_windows += 1

    if total_windows == 0:
        return 0.5

    # Breadth ratio: 0 to 1
    breadth = positive_windows / total_windows

    # High breadth (>0.7) = strong market, momentum works
    # Low breadth (<0.3) = weak market, be cautious
    # Map directly since breadth is already in [0, 1]
    return max(0.0, min(1.0, breadth))
