FACTOR_NAME = "stopping_volume"
FACTOR_DESC = "Very high volume on a down bar but close near high — buying stopping the decline"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if idx < 1 or closes[idx - 1] == 0:
        return 0.5
    # Down bar from previous close
    is_down = closes[idx] < closes[idx - 1]
    if not is_down:
        return 0.5
    # High volume
    avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
    if avg_vol == 0:
        return 0.5
    vol_ratio = volumes[idx] / avg_vol
    # Close near high
    spread = highs[idx] - lows[idx]
    if spread == 0:
        return 0.5
    close_position = (closes[idx] - lows[idx]) / spread  # 1.0 = close at high
    if vol_ratio > 1.5 and close_position > 0.6:
        # Stopping volume — bullish
        score = 0.6 + close_position * 0.2 + min(vol_ratio - 1.5, 1.0) * 0.1
        return max(0.0, min(1.0, score))
    return 0.5
