FACTOR_NAME = "test_bar"
FACTOR_DESC = "Down bar that closes near high on low volume — testing for supply, bullish if none"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if idx < 1 or closes[idx - 1] == 0:
        return 0.5
    # Price dipped (low < previous close) but closed near high
    dipped = lows[idx] < closes[idx - 1]
    if not dipped:
        return 0.5
    spread = highs[idx] - lows[idx]
    if spread == 0:
        return 0.5
    close_position = (closes[idx] - lows[idx]) / spread
    # Low volume
    avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
    if avg_vol == 0:
        return 0.5
    vol_ratio = volumes[idx] / avg_vol
    if close_position > 0.7 and vol_ratio < 0.8:
        # Test bar — low volume test successful = bullish
        score = 0.7 + close_position * 0.15 + (1.0 - vol_ratio) * 0.1
        return max(0.0, min(1.0, score))
    return 0.5
