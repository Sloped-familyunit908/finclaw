"""
Factor: crypto_range_breakout
Description: Price breaking out of 48h high/low range
Category: crypto
"""

FACTOR_NAME = "crypto_range_breakout"
FACTOR_DESC = "48h range breakout — price breaking out of 48-bar high/low channel, strong signal in crypto"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Measures where current price sits relative to the 48h high-low range.
    Breakout above range → very bullish (>0.8)
    Near top of range → bullish (0.6-0.8)  
    Middle → neutral (0.5)
    Near bottom → bearish (0.2-0.4)
    Breakout below → very bearish (<0.2)
    """
    lookback = 48
    if idx < lookback:
        return 0.5

    # Calculate 48h range (excluding current bar)
    range_high = max(highs[idx - lookback:idx])
    range_low = min(lows[idx - lookback:idx])

    range_size = range_high - range_low
    if range_size <= 0:
        return 0.5

    current_price = closes[idx]

    # Position within range (can be >1 or <0 for breakouts)
    position = (current_price - range_low) / range_size

    # Allow breakout extension:
    # position > 1.0 = breakout above → extra bullish
    # position < 0.0 = breakout below → extra bearish
    # Clamp at 0-1 but with breakout bonus
    if position > 1.0:
        # Breakout above: 1.0 + proportional bonus
        score = 0.8 + min((position - 1.0) * 0.5, 0.2)
    elif position < 0.0:
        # Breakout below
        score = 0.2 + max(position * 0.5, -0.2)
    else:
        # Within range: linear mapping 0.2 to 0.8
        score = 0.2 + position * 0.6

    return max(0.0, min(1.0, score))
