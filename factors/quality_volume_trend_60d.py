"""
Quality Factor: Volume Trend 60-day
======================================
Is average volume increasing or decreasing over 60 days?
Declining volume in a declining stock = losing interest = dying.
Increasing volume in rising stock = healthy interest.

Category: quality_filter
"""

FACTOR_NAME = "quality_volume_trend_60d"
FACTOR_DESC = "Volume trend direction over 60 days — dying stocks lose volume"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = 60
    if idx < lookback:
        lookback = idx + 1
    if lookback < 20:
        return 0.5

    # Compare recent 20d average volume vs older 20d average volume
    recent_start = idx - 19
    old_start = idx - lookback + 1
    old_end = old_start + 20

    if old_end > recent_start:
        # Not enough separation; use halves
        half = lookback // 2
        old_start = idx - lookback + 1
        old_end = old_start + half
        recent_start = idx - half + 1

    recent_vol = 0.0
    recent_count = 0
    for i in range(recent_start, idx + 1):
        recent_vol += volumes[i]
        recent_count += 1

    old_vol = 0.0
    old_count = 0
    for i in range(old_start, old_end):
        old_vol += volumes[i]
        old_count += 1

    if old_count == 0 or recent_count == 0:
        return 0.5

    avg_recent = recent_vol / recent_count
    avg_old = old_vol / old_count

    if avg_old <= 0:
        return 0.5

    vol_change = (avg_recent - avg_old) / avg_old  # positive = increasing volume

    # Also check price direction for context
    price_ret = 0.0
    if closes[idx - lookback + 1] > 0:
        price_ret = (closes[idx] - closes[idx - lookback + 1]) / closes[idx - lookback + 1]

    # Best case: volume up + price up = 1.0
    # Worst case: volume down + price down = 0.0
    # Volume up + price down = mixed (could be capitulation) = 0.4
    # Volume down + price up = thin rally = 0.6
    if price_ret > 0 and vol_change > 0:
        base = 0.7
    elif price_ret > 0 and vol_change <= 0:
        base = 0.5
    elif price_ret <= 0 and vol_change > 0:
        base = 0.4
    else:
        base = 0.2

    # Adjust by magnitude of volume change
    adjustment = min(abs(vol_change), 0.5) * 0.4  # max ±0.2
    if vol_change > 0:
        score = base + adjustment
    else:
        score = base - adjustment

    return max(0.0, min(1.0, score))
