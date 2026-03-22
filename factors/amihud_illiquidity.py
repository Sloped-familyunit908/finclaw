"""
Auto-generated factor: amihud_illiquidity
Description: |return| / volume - Amihud illiquidity measure (lower = more liquid = better)
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "amihud_illiquidity"
FACTOR_DESC = "|return| / volume - Amihud illiquidity measure (lower = more liquid = better)"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Amihud illiquidity: avg |return| / volume over 20 days."""

    lookback = 20
    if idx < lookback:
        return 0.5

    total_illiq = 0.0
    valid = 0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0 and volumes[i] > 0:
            abs_ret = abs((closes[i] - closes[i - 1]) / closes[i - 1])
            illiq = abs_ret / volumes[i]
            total_illiq += illiq
            valid += 1

    if valid == 0:
        return 0.5

    avg_illiq = total_illiq / valid

    # Lower illiquidity = more liquid = generally better
    # Use sigmoid-like mapping: very liquid = high score
    score = 1.0 / (1.0 + avg_illiq * 1e8)
    return max(0.0, min(1.0, score))
