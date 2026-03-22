"""
Factor: volume_breakout
Description: Price breakout on above-average volume
Category: volume
"""

FACTOR_NAME = "volume_breakout"
FACTOR_DESC = "Price breakout on above-average volume"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Price at 20-day high with volume above 20-day average."""
    if idx < 20:
        return 0.5

    # Check if price is at or near 20-day high
    recent_high = max(highs[idx - 19:idx])  # Exclude today
    current_close = closes[idx]

    # Volume check
    avg_vol = sum(volumes[idx - 19:idx]) / 19  # Exclude today from avg
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    # Price breakout above previous resistance
    if current_close > recent_high:
        breakout_pct = (current_close - recent_high) / recent_high if recent_high > 0 else 0

        if vol_ratio > 1.5:
            # Strong breakout on high volume
            score = 0.8 + min(breakout_pct * 10, 0.15) + min((vol_ratio - 1.5) * 0.05, 0.05)
        elif vol_ratio > 1.0:
            # Breakout on decent volume
            score = 0.65 + min(breakout_pct * 10, 0.1)
        else:
            # Breakout on low volume (suspicious)
            score = 0.55
    elif current_close > recent_high * 0.98:
        # Near breakout
        score = 0.55 if vol_ratio > 1.0 else 0.5
    else:
        score = 0.45

    return max(0.0, min(1.0, score))
