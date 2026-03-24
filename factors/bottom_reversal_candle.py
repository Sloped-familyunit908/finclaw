"""
Factor: bottom_reversal_candle
Description: Bullish reversal candle after 3+ red candles — classic bottom pattern
Category: bottom_confirmation
"""

FACTOR_NAME = "bottom_reversal_candle"
FACTOR_DESC = "Bullish reversal candle after 3+ consecutive red candles"
FACTOR_CATEGORY = "bottom_confirmation"


def compute(closes, highs, lows, volumes, idx):
    """Detect bullish reversal: after 3+ red candles, a green candle that
    closes above the midpoint of the previous red candle.

    Classic reversal pattern: bears are exhausted, bulls reclaim territory.
    The further the green candle closes into the previous red candle's body,
    the stronger the signal.
    """
    if idx < 5:
        return 0.5

    # Today must be a green candle (close > prev_close as open proxy)
    close_today = closes[idx]
    open_proxy_today = closes[idx - 1]

    if close_today <= open_proxy_today:
        # Today is not a green candle
        return 0.5

    # Count consecutive red candles before today
    red_count = 0
    for i in range(idx - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            red_count += 1
        else:
            break

    if red_count < 3:
        # Not enough consecutive red candles
        if red_count == 2:
            # Partial signal
            return 0.55
        return 0.5

    # Previous candle's body midpoint (red candle: close < open)
    prev_close = closes[idx - 1]
    prev_open_proxy = closes[idx - 2]
    prev_body_top = max(prev_close, prev_open_proxy)
    prev_body_bottom = min(prev_close, prev_open_proxy)
    prev_midpoint = (prev_body_top + prev_body_bottom) / 2.0

    # Check if today's close is above the midpoint of previous red candle
    closes_above_midpoint = close_today > prev_midpoint

    if not closes_above_midpoint:
        # Green candle but doesn't reclaim enough territory
        if red_count >= 3:
            return 0.6  # still somewhat positive after long decline
        return 0.5

    # Score based on strength of reversal
    if prev_body_top > prev_body_bottom:
        # How far into the previous candle did we close?
        penetration = (close_today - prev_body_bottom) / (prev_body_top - prev_body_bottom)
        penetration = min(penetration, 1.5)  # can close above prev open
    else:
        penetration = 1.0

    # More red candles before = stronger reversal
    exhaustion_bonus = min(0.15, (red_count - 3) * 0.05)

    if penetration >= 1.0:
        # Engulfing-like: closes above previous open
        base_score = 1.0
    elif penetration >= 0.5:
        # Closes above midpoint
        base_score = 0.8 + (penetration - 0.5) * 0.4
    else:
        base_score = 0.65

    score = base_score + exhaustion_bonus

    return max(0.0, min(1.0, score))
