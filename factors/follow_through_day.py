"""
Auto-generated factor: follow_through_day
Description: Big up day (+2%+) on above-average volume after a decline
Category: composite
Generated: seed
"""

FACTOR_NAME = "follow_through_day"
FACTOR_DESC = "Big up day (+2%+) on above-average volume after a decline"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Follow-through day: big rally after decline with volume."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Today's return
    daily_return = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    # Volume check
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback
    above_avg_vol = volumes[idx] > avg_vol

    # Check for prior decline (last 10-20 days down trend)
    decline_window = 10
    if idx >= decline_window + 3:
        prior_return = (closes[idx - 3] - closes[idx - 3 - decline_window]) / closes[idx - 3 - decline_window] if closes[idx - 3 - decline_window] > 0 else 0.0
        had_decline = prior_return < -0.05
    else:
        had_decline = False

    # Follow-through: +2% day on above-avg volume after decline
    big_up = daily_return > 0.02

    if big_up and above_avg_vol and had_decline:
        strength = daily_return * 10.0
        score = 0.5 + strength
        return max(0.0, min(1.0, score))

    if big_up and above_avg_vol:
        return 0.7

    if big_up:
        return 0.6

    return 0.5
