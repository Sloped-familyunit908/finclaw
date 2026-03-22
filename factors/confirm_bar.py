FACTOR_NAME = "confirm_bar"
FACTOR_DESC = "Up bar on increasing volume after a bottom signal — confirmation"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if idx < 2 or closes[idx - 1] == 0:
        return 0.5
    # Today is an up bar
    is_up = closes[idx] > closes[idx - 1]
    if not is_up:
        return 0.5
    # Volume is increasing
    vol_increasing = volumes[idx] > volumes[idx - 1]
    # Check for recent bottom signal: was there a down bar with close near high in last 3 days?
    bottom_signal = False
    for i in range(idx - 3, idx):
        if i < 1:
            continue
        if closes[i] < closes[i - 1]:  # down bar
            spread = highs[i] - lows[i]
            if spread > 0:
                close_pos = (closes[i] - lows[i]) / spread
                if close_pos > 0.6:  # close near high
                    bottom_signal = True
                    break
    if is_up and vol_increasing and bottom_signal:
        # Confirmation bar — bullish
        avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
        vol_strength = volumes[idx] / avg_vol if avg_vol > 0 else 1.0
        score = 0.7 + min(vol_strength - 1.0, 0.5) * 0.2
        return max(0.0, min(1.0, score))
    elif is_up and vol_increasing:
        return 0.6
    return 0.5
