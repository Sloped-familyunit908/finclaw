"""
Auto-generated factor: unusual_volume_spike
Description: Volume today / max(volume last 60 days) - how unusual is today
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "unusual_volume_spike"
FACTOR_DESC = "Volume today / max(volume last 60 days) - how unusual is today"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Unusual volume spike: today vs max of last 60 days."""

    lookback = 60
    if idx < lookback:
        return 0.5

    # Find max volume in lookback period (excluding today)
    max_vol = 0.0
    for i in range(idx - lookback, idx):
        if volumes[i] > max_vol:
            max_vol = volumes[i]

    if max_vol < 1e-10:
        return 0.5

    ratio = volumes[idx] / max_vol

    # If ratio > 1, today is new high volume (unusual)
    # Check direction for bullish/bearish
    daily_return = (closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    if ratio > 1.0:
        # New volume high!
        if daily_return > 0:
            score = 0.5 + ratio * 0.2
        else:
            score = 0.5 - ratio * 0.2
    else:
        # Normal volume
        score = 0.5

    return max(0.0, min(1.0, score))
