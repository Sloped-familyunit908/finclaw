"""
Factor: trend_adx_strength
Description: ADX-like trend strength indicator
Category: trend_following
"""

FACTOR_NAME = "trend_adx_strength"
FACTOR_DESC = "ADX trend strength — high ADX = strong trend in either direction"
FACTOR_CATEGORY = "trend_following"


def compute(closes, highs, lows, volumes, idx):
    """ADX-like trend strength. Uses directional movement concept.
    High score = strong trend (bullish or bearish).
    """
    period = 14
    if idx < period + 1:
        return 0.5

    # Calculate +DM, -DM, and TR
    plus_dm_sum = 0.0
    minus_dm_sum = 0.0
    tr_sum = 0.0

    for i in range(idx - period + 1, idx + 1):
        # True range
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_sum += tr

        # Directional movement
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm_sum += up_move
        if down_move > up_move and down_move > 0:
            minus_dm_sum += down_move

    if tr_sum <= 0:
        return 0.5

    # +DI and -DI
    plus_di = (plus_dm_sum / tr_sum) * 100.0
    minus_di = (minus_dm_sum / tr_sum) * 100.0

    di_sum = plus_di + minus_di
    if di_sum <= 0:
        return 0.5

    # DX = |+DI - -DI| / (+DI + -DI)
    dx = abs(plus_di - minus_di) / di_sum * 100.0

    # ADX is typically a smoothed DX, but we use DX directly as a proxy
    # Normalize: ADX < 20 = weak trend, > 40 = strong trend
    # Map to [0, 1]: 0-20 → 0-0.5, 20-50 → 0.5-1.0
    if dx < 20:
        score = dx / 40.0  # 0→0, 20→0.5
    else:
        score = 0.5 + min(0.5, (dx - 20) / 60.0)

    return max(0.0, min(1.0, score))
