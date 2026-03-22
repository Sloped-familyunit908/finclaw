"""
Auto-generated factor: mean_reversion_speed
Description: How quickly price reverts to mean — fast reversion = stronger mean reversion tendency
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "mean_reversion_speed"
FACTOR_DESC = "How quickly price reverts to mean — fast reversion = stronger mean reversion tendency"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Measure avg days to revert to 20-day MA over recent 60 days."""

    if idx < 80:
        return 0.5

    # We need 60 days of data, each needing a 20-day MA
    # So total lookback = 60 + 20 = 80

    reversion_times = []
    days_away = 0
    was_above = None

    for i in range(idx - 59, idx + 1):
        # Calculate 20-day MA at day i
        ma20 = sum(closes[i - 19:i + 1]) / 20.0

        if ma20 <= 0:
            continue

        currently_above = closes[i] > ma20

        if was_above is None:
            was_above = currently_above
            days_away = 0
            continue

        if currently_above == was_above:
            days_away += 1
        else:
            # Crossed the MA — record reversion time
            if days_away > 0:
                reversion_times.append(days_away)
            days_away = 0
            was_above = currently_above

    if len(reversion_times) == 0:
        return 0.5

    avg_reversion = sum(reversion_times) / float(len(reversion_times))

    # Fast reversion (< 3 days) → score 1.0
    # Slow reversion (> 10 days) → score 0.0
    # Linear between 3 and 10
    score = 1.0 - (avg_reversion - 3.0) / 7.0
    return max(0.0, min(1.0, score))
