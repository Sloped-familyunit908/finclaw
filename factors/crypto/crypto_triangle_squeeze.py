"""
Factor: crypto_triangle_squeeze
Description: Converging high-low range over 48 bars — breakout imminent
Category: crypto
"""

FACTOR_NAME = "crypto_triangle_squeeze"
FACTOR_DESC = "Triangle/squeeze pattern — converging price range suggesting imminent breakout"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong squeeze/convergence (breakout likely)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Compare range of first half vs second half
    first_half_ranges = []
    second_half_ranges = []
    half = lookback // 2

    for i in range(idx - lookback, idx - half):
        if lows[i] > 0:
            first_half_ranges.append((highs[i] - lows[i]) / lows[i])

    for i in range(idx - half, idx):
        if lows[i] > 0:
            second_half_ranges.append((highs[i] - lows[i]) / lows[i])

    if not first_half_ranges or not second_half_ranges:
        return 0.5

    avg_first = sum(first_half_ranges) / len(first_half_ranges)
    avg_second = sum(second_half_ranges) / len(second_half_ranges)

    if avg_first <= 0:
        return 0.5

    # Also check that max-min range is converging
    first_overall = max(highs[idx - lookback:idx - half]) - min(lows[idx - lookback:idx - half])
    second_overall = max(highs[idx - half:idx]) - min(lows[idx - half:idx])

    if first_overall <= 0:
        return 0.5

    range_ratio = second_overall / first_overall
    bar_ratio = avg_second / avg_first

    # Both converging = strong squeeze
    convergence = (1.0 - range_ratio) * 0.5 + (1.0 - bar_ratio) * 0.5
    score = 0.5 + convergence * 0.5
    return max(0.0, min(1.0, score))
