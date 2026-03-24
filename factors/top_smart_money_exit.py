"""
Factor: top_smart_money_exit
Description: Large volume bars with close near low — smart money selling
Category: top_escape
"""

FACTOR_NAME = "top_smart_money_exit"
FACTOR_DESC = "High volume bars closing near lows — smart money distributing into buying"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Large volume bars with close near the LOW (not the high).
    Smart money is selling into retail buying, causing volume spikes
    but the close drifts to the low of the bar.
    """
    lookback = 10
    if idx < lookback:
        return 0.5

    # Calculate average volume
    vol_sum = sum(volumes[idx - lookback + 1 : idx + 1])
    avg_vol = vol_sum / lookback if lookback > 0 else 0

    if avg_vol <= 0:
        return 0.5

    # Count bars with high volume AND close near low
    smart_exit_count = 0
    total_score = 0.0

    check_bars = min(5, idx + 1)
    for i in range(idx - check_bars + 1, idx + 1):
        bar_range = highs[i] - lows[i]
        if bar_range <= 0 or avg_vol <= 0:
            continue

        vol_ratio = volumes[i] / avg_vol
        if vol_ratio < 1.5:
            continue  # Not high volume

        # Close position within bar (0 = at low, 1 = at high)
        close_position = (closes[i] - lows[i]) / bar_range

        if close_position < 0.35:
            # Close near low on high volume = selling pressure
            smart_exit_count += 1
            # Score this bar
            vol_strength = min(1.0, (vol_ratio - 1.5) / 2.5)  # 1.5x→0, 4x→1
            close_weakness = 1.0 - close_position / 0.35  # 0 at 0.35, 1 at 0
            total_score += vol_strength * close_weakness

    if smart_exit_count == 0:
        return 0.5

    avg_bar_score = total_score / smart_exit_count

    if smart_exit_count >= 3:
        base = 0.85
    elif smart_exit_count >= 2:
        base = 0.75
    else:
        base = 0.65

    score = base * (0.6 + 0.4 * avg_bar_score)

    return max(0.0, min(1.0, score))
