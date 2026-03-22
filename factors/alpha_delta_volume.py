FACTOR_NAME = "alpha_delta_volume"
FACTOR_DESC = "Change in average volume: avg_vol_5d / avg_vol_20d"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    avg5 = sum(volumes[idx - 4:idx + 1]) / 5.0
    avg20 = sum(volumes[idx - 19:idx + 1]) / 20.0
    if avg20 == 0:
        return 0.5
    ratio = avg5 / avg20  # >1 = increasing volume
    # Map [0.5, 2.0] to [0, 1]
    score = (ratio - 0.5) / 1.5
    return max(0.0, min(1.0, score))
