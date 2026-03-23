"""
Factor: crypto_wick_ratio_upper
Description: Upper wick / total range averaged over 12 bars
Category: crypto
"""

FACTOR_NAME = "crypto_wick_ratio_upper"
FACTOR_DESC = "Upper wick / total range averaged over 12 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = large upper wicks (selling pressure)."""
    lookback = 12
    if idx < lookback:
        return 0.5

    ratios = []
    for i in range(idx - lookback, idx):
        total_range = highs[i] - lows[i]
        if total_range <= 0:
            ratios.append(0.5)
            continue
        open_approx = closes[i - 1] if i > 0 else closes[i]
        upper_wick = highs[i] - max(open_approx, closes[i])
        if upper_wick < 0:
            upper_wick = 0
        ratios.append(upper_wick / total_range)

    avg_ratio = sum(ratios) / len(ratios)
    return max(0.0, min(1.0, avg_ratio))
