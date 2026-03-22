"""
Auto-generated factor: value_quality
Description: Below MA20 but high volume + improving RSI (value + quality combo)
Category: composite
Generated: seed
"""

FACTOR_NAME = "value_quality"
FACTOR_DESC = "Below MA20 but high volume + improving RSI (value + quality combo)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Value quality: below MA20 with high volume and improving RSI."""

    rsi_period = 14
    lookback = 20
    if idx < lookback + rsi_period:
        return 0.5

    # MA20
    total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        total += closes[i]
    ma20 = total / lookback

    # Below MA20 (value)
    below_ma20 = closes[idx] < ma20

    # Volume vs average
    vol_total = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback
    high_volume = volumes[idx] > avg_vol * 1.2

    # RSI
    def _rsi_at(end_idx):
        gains = 0.0
        losses = 0.0
        for j in range(end_idx - rsi_period + 1, end_idx + 1):
            change = closes[j] - closes[j - 1]
            if change > 0:
                gains += change
            else:
                losses -= change
        avg_gain = gains / rsi_period
        avg_loss = losses / rsi_period
        if avg_loss < 1e-10:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    rsi_now = _rsi_at(idx)
    rsi_5d_ago = _rsi_at(idx - 5) if idx >= rsi_period + 5 else rsi_now
    improving_rsi = rsi_now > rsi_5d_ago

    score = 0.5
    if below_ma20:
        score += 0.1
    if high_volume:
        score += 0.1
    if improving_rsi:
        score += 0.1
    if below_ma20 and high_volume and improving_rsi:
        score = 0.85

    return max(0.0, min(1.0, score))
