"""
Factor: gap_fill
Description: Gap down that's starting to fill (recovering from gap)
Category: candlestick
"""

FACTOR_NAME = "gap_fill"
FACTOR_DESC = "Gap down being filled — price recovering from gap down"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Detect gap down in last 5 days and measure how much it's been filled."""
    if idx < 5:
        return 0.5

    # Look for gap down in recent days
    best_gap_score = 0.5

    for gap_day in range(idx - 4, idx + 1):
        if gap_day < 1:
            continue

        prev_low = lows[gap_day - 1]
        day_high = highs[gap_day]

        # Gap down: today's high < yesterday's low
        if day_high < prev_low:
            gap_size = prev_low - day_high
            if prev_low <= 0:
                continue
            gap_pct = gap_size / prev_low

            # How much has been filled since gap day?
            current_close = closes[idx]
            # Fill percentage: how much of the gap has price recovered
            if gap_size > 0:
                filled = (current_close - day_high) / gap_size
                filled = max(0.0, min(1.0, filled))
            else:
                filled = 0.0

            # Filling a gap = bullish
            if filled > 0.8:
                score = 0.85
            elif filled > 0.5:
                score = 0.7
            elif filled > 0.2:
                score = 0.6
            else:
                # Gap exists but not filling
                score = 0.4

            if score > best_gap_score:
                best_gap_score = score

    return max(0.0, min(1.0, best_gap_score))
