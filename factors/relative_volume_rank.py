"""
Auto-generated factor: relative_volume_rank
Description: Volume relative to its own 60-day history — proxy for cross-sectional volume rank
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "relative_volume_rank"
FACTOR_DESC = "Volume relative to its own 60-day history — proxy for cross-sectional volume rank"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Percentile rank of today's volume within last 60 days of volumes."""

    lookback = 60
    if idx < lookback:
        return 0.5

    today_vol = volumes[idx]
    # Collect last 60 days of volume (including today)
    window = volumes[idx - lookback + 1:idx + 1]

    # Count how many values are less than or equal to today's volume
    count_le = 0
    for v in window:
        if v <= today_vol:
            count_le += 1

    # Percentile rank
    score = count_le / float(lookback)
    return max(0.0, min(1.0, score))
