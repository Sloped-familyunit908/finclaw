"""
Factor: crypto_wick_ratio_lower
Description: Lower wick / total range averaged over 12 bars
Category: crypto
"""

FACTOR_NAME = "crypto_wick_ratio_lower"
FACTOR_DESC = "Lower wick / total range averaged over 12 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = large lower wicks (buying pressure)."""
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
        lower_wick = min(open_approx, closes[i]) - lows[i]
        if lower_wick < 0:
            lower_wick = 0
        ratios.append(lower_wick / total_range)

    avg_ratio = sum(ratios) / len(ratios)
    return max(0.0, min(1.0, avg_ratio))
