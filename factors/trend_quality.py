"""
Auto-generated factor: trend_quality
Description: Combination of slope, R-squared, and ADX proxy (overall trend quality)
Category: composite
Generated: seed
"""

FACTOR_NAME = "trend_quality"
FACTOR_DESC = "Combination of slope, R-squared, and ADX proxy (overall trend quality)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Trend quality: slope + R-squared + ADX proxy combined."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Linear regression slope and R²
    n = lookback
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0
    sum_y2 = 0.0

    for i in range(n):
        x = float(i)
        y = closes[idx - lookback + 1 + i]
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_x2 += x * x
        sum_y2 += y * y

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.5

    slope = (n * sum_xy - sum_x * sum_y) / denom

    # R²
    ss_tot = n * sum_y2 - sum_y * sum_y
    if abs(ss_tot) < 1e-10:
        r_squared = 0.0
    else:
        ss_reg = (n * sum_xy - sum_x * sum_y) ** 2 / (denom * ss_tot)
        r_squared = max(0.0, min(1.0, ss_reg))

    # ADX proxy: average directional movement
    dm_plus_total = 0.0
    dm_minus_total = 0.0
    tr_total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        if up_move > down_move and up_move > 0:
            dm_plus_total += up_move
        if down_move > up_move and down_move > 0:
            dm_minus_total += down_move
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_total += tr

    if tr_total > 0:
        di_plus = dm_plus_total / tr_total
        di_minus = dm_minus_total / tr_total
        di_sum = di_plus + di_minus
        adx_proxy = abs(di_plus - di_minus) / di_sum if di_sum > 0 else 0.0
    else:
        adx_proxy = 0.0

    # Normalize slope
    avg_price = sum_y / n
    norm_slope = slope / avg_price if avg_price > 0 else 0.0

    # Combine: direction from slope, quality from R² and ADX
    quality = r_squared * 0.5 + adx_proxy * 0.5
    direction = 1.0 if norm_slope > 0 else -1.0

    score = 0.5 + direction * quality * 0.5
    return max(0.0, min(1.0, score))
