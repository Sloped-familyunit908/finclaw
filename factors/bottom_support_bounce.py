"""
Factor: bottom_support_bounce
Description: Price touches/breaks recent support then closes above it — support held
Category: bottom_confirmation
"""

FACTOR_NAME = "bottom_support_bounce"
FACTOR_DESC = "Price touches or breaks below 20-day support then bounces back above — support held"
FACTOR_CATEGORY = "bottom_confirmation"


def compute(closes, highs, lows, volumes, idx):
    """Detect price touching or slightly breaking below a recent support level
    (lowest low of last 20 bars) then closing meaningfully above it.

    'Support held' is one of the strongest bottom confirmation signals.
    The more violently the price bounced off support, the stronger the signal.
    """
    lookback = 20
    if idx < lookback + 1:
        return 0.5

    # Support = lowest low in the lookback period (excluding today)
    support = min(lows[idx - lookback:idx])
    if support <= 0:
        return 0.5

    today_low = lows[idx]
    today_close = closes[idx]
    today_high = highs[idx]

    # How close did today's low get to support?
    distance_pct = (today_low - support) / support if support > 0 else 1.0

    # Touched or broke below support (within 2% of support level)
    touched_support = distance_pct < 0.02

    # Slightly broke below support (went lower than support)
    broke_support = today_low < support

    if not touched_support and not broke_support:
        # Didn't get near support
        if distance_pct < 0.05:
            # Getting close to support — mild signal
            return 0.55
        return 0.5

    # Must close meaningfully above support
    close_above_support = today_close > support * 1.005  # at least 0.5% above

    if not close_above_support:
        # Touched support but couldn't close above it — support breaking
        return 0.4

    # Calculate bounce strength
    day_range = today_high - today_low
    if day_range > 0:
        bounce_strength = (today_close - today_low) / day_range
    else:
        bounce_strength = 0.5

    # Score based on how strongly price bounced off support
    if broke_support and bounce_strength > 0.7:
        # Broke below support then bounced strongly — spring/shakeout pattern
        score = 1.0
    elif broke_support and bounce_strength > 0.5:
        # Broke below then moderate bounce
        score = 0.85
    elif touched_support and bounce_strength > 0.7:
        # Tested support exactly and bounced strongly
        score = 0.9
    elif touched_support and bounce_strength > 0.5:
        # Tested support with moderate bounce
        score = 0.75
    elif touched_support:
        # Weak bounce from support
        score = 0.6
    else:
        score = 0.55

    # Volume confirmation: higher volume on bounce day is bullish
    if idx >= 5:
        avg_vol = sum(volumes[idx - 4:idx]) / 4
        if avg_vol > 0 and volumes[idx] > avg_vol * 1.5:
            score = min(1.0, score + 0.1)

    return max(0.0, min(1.0, score))
