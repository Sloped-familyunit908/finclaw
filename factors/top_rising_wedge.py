"""
Factor: top_rising_wedge
Description: Converging higher highs and higher lows — rising wedge (bearish)
Category: top_escape
"""

FACTOR_NAME = "top_rising_wedge"
FACTOR_DESC = "Higher highs converging with higher lows — rising wedge bearish pattern"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Rising wedge: both highs and lows are making higher values,
    but the distance between them is shrinking (converging).
    This is a bearish pattern — the rally is losing strength.
    """
    lookback = 15
    if idx < lookback:
        return 0.5

    # Collect highs and lows over lookback period
    period_highs = highs[idx - lookback + 1 : idx + 1]
    period_lows = lows[idx - lookback + 1 : idx + 1]

    # Check for higher highs: compare first third vs last third
    third = lookback // 3
    if third < 2:
        return 0.5

    early_highs = period_highs[:third]
    late_highs = period_highs[-third:]
    early_lows = period_lows[:third]
    late_lows = period_lows[-third:]

    avg_early_high = sum(early_highs) / len(early_highs)
    avg_late_high = sum(late_highs) / len(late_highs)
    avg_early_low = sum(early_lows) / len(early_lows)
    avg_late_low = sum(late_lows) / len(late_lows)

    # Both highs and lows should be rising
    if avg_late_high <= avg_early_high or avg_late_low <= avg_early_low:
        return 0.5

    # Calculate the range (high - low) convergence
    early_range = avg_early_high - avg_early_low
    late_range = avg_late_high - avg_late_low

    if early_range <= 0:
        return 0.5

    # Convergence: late range should be smaller than early range
    convergence_ratio = 1.0 - (late_range / early_range)

    if convergence_ratio <= 0:
        return 0.5  # Not converging — not a wedge

    # The highs should be getting closer together (decelerating)
    mid_highs = period_highs[third : 2 * third]
    avg_mid_high = sum(mid_highs) / len(mid_highs)

    high_accel1 = avg_mid_high - avg_early_high
    high_accel2 = avg_late_high - avg_mid_high

    deceleration = 0.0
    if high_accel1 > 0:
        deceleration = 1.0 - (high_accel2 / high_accel1) if high_accel2 < high_accel1 else 0.0

    # Score based on convergence strength and deceleration
    conv_score = min(1.0, convergence_ratio / 0.40)  # 40% convergence = max
    decel_score = min(1.0, deceleration)

    score = 0.6 + 0.4 * (0.6 * conv_score + 0.4 * decel_score)

    return max(0.0, min(1.0, score))
