"""
Auto-generated factor: volume_price_divergence
Description: Classic divergence: price making new lows but volume declining — bullish signal
Category: technical
Generated: seed
"""

FACTOR_NAME = "volume_price_divergence"
FACTOR_DESC = "Classic divergence: price making new lows but volume declining — bullish signal"
FACTOR_CATEGORY = "technical"


def compute(closes, highs, lows, volumes, idx):
    """Detect price-volume divergence over last 20 days."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Price trend: linear regression slope approximation using first half vs second half
    half = lookback // 2

    price_first_half = 0.0
    price_second_half = 0.0
    vol_first_half = 0.0
    vol_second_half = 0.0

    for i in range(half):
        price_first_half += closes[idx - lookback + 1 + i]
        vol_first_half += volumes[idx - lookback + 1 + i]

    for i in range(half):
        price_second_half += closes[idx - half + 1 + i]
        vol_second_half += volumes[idx - half + 1 + i]

    avg_price_first = price_first_half / float(half)
    avg_price_second = price_second_half / float(half)
    avg_vol_first = vol_first_half / float(half)
    avg_vol_second = vol_second_half / float(half)

    if avg_price_first <= 0 or avg_vol_first <= 0:
        return 0.5

    price_trend = (avg_price_second - avg_price_first) / avg_price_first
    vol_trend = (avg_vol_second - avg_vol_first) / avg_vol_first

    # Scoring based on divergence patterns:
    # Price down + Volume down = bullish divergence → high score
    # Price up + Volume up = confirmation → neutral (0.5)
    # Price down + Volume up = distribution → low score
    # Price up + Volume down = weakening rally → slightly below neutral

    if price_trend < 0 and vol_trend < 0:
        # Bullish divergence — the more negative the price and less volume, the better
        intensity = min(abs(price_trend) * 10, 1.0)
        score = 0.5 + 0.5 * intensity
    elif price_trend > 0 and vol_trend > 0:
        # Confirmation — neutral
        score = 0.5
    elif price_trend < 0 and vol_trend > 0:
        # Distribution — bearish
        intensity = min(abs(price_trend) * 10, 1.0)
        score = 0.5 - 0.5 * intensity
    else:
        # Price up + volume down — weakening rally
        score = 0.4

    return max(0.0, min(1.0, score))
