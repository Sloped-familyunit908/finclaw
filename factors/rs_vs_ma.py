"""
Auto-generated factor: rs_vs_ma
Description: Price relative strength vs its own MA50 (trending above or below)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "rs_vs_ma"
FACTOR_DESC = "Price relative strength vs its own MA50 (trending above or below)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Relative strength vs MA50."""

    lookback = 50
    if idx < lookback:
        return 0.5

    # MA50
    total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total += closes[i]
    ma50 = total / lookback

    if ma50 < 1e-10:
        return 0.5

    # Percentage above/below MA50
    rs = (closes[idx] - ma50) / ma50

    # Map from [-10%, +10%] to [0, 1]
    score = 0.5 + rs * 5.0
    return max(0.0, min(1.0, score))
