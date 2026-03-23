"""
Factor: smart_money_flow
Description: Detect institutional buying vs retail selling via large volume bars
Category: flow
"""

FACTOR_NAME = "smart_money_flow"
FACTOR_DESC = "Detect institutional buying vs retail selling — large volume bars with positive close = institutional accumulation"
FACTOR_CATEGORY = "flow"


def compute(closes, highs, lows, volumes, idx):
    """
    Smart money flow: detect institutional accumulation over last 10 days.
    
    Logic: Large volume bars (>2x avg) with positive close = institutional buying.
    Large volume bars with negative close = institutional selling.
    Net score over 10 days normalized to [0, 1].
    """
    lookback = 10
    vol_avg_window = 20

    if idx < vol_avg_window:
        return 0.5

    # Compute average volume over last 20 days (excluding today)
    vol_sum = 0.0
    for i in range(idx - vol_avg_window, idx):
        vol_sum += volumes[i]
    avg_vol = vol_sum / vol_avg_window

    if avg_vol <= 0:
        return 0.5

    # Scan last 10 days for institutional activity
    start = max(1, idx - lookback + 1)
    institutional_score = 0.0
    count = 0

    for i in range(start, idx + 1):
        vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1.0

        if vol_ratio > 2.0:
            # Large volume bar — likely institutional
            daily_return = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] > 0 else 0.0
            # Weight by volume magnitude
            weight = min(vol_ratio / 2.0, 3.0)  # cap at 3x weight
            if daily_return > 0:
                institutional_score += weight  # institutional buying
            elif daily_return < 0:
                institutional_score -= weight  # institutional selling
            count += 1

    if count == 0:
        return 0.5  # no large volume bars detected

    # Normalize: typical range is -3 to +3 per bar, max ~30 total
    # Use softer normalization
    max_possible = count * 3.0
    if max_possible > 0:
        normalized = institutional_score / max_possible
    else:
        normalized = 0.0

    # Map from [-1, 1] to [0, 1]
    score = 0.5 + normalized * 0.5

    return max(0.0, min(1.0, score))
