"""
Factor: crypto_stoch_cross
Description: %K crossing %D stochastic signal
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_cross"
FACTOR_DESC = "%K crossing %D stochastic signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = bullish cross (%K above %D), <0.5 = bearish."""
    lookback_k = 14
    smooth = 3
    if idx < lookback_k + smooth:
        return 0.5

    def calc_k(i):
        highest = max(highs[i - lookback_k:i])
        lowest = min(lows[i - lookback_k:i])
        r = highest - lowest
        if r <= 0:
            return 0.5
        return (closes[i - 1] - lowest) / r

    def calc_d(i):
        return sum(calc_k(i - smooth + 1 + j) for j in range(smooth)) / smooth

    k_now = calc_k(idx)
    d_now = calc_d(idx)
    k_prev = calc_k(idx - 1)
    d_prev = calc_d(idx - 1)

    crossed_up = k_prev <= d_prev and k_now > d_now
    crossed_down = k_prev >= d_prev and k_now < d_now

    if crossed_up:
        return 0.85
    elif crossed_down:
        return 0.15

    score = 0.5 + (k_now - d_now) * 2.0
    return max(0.0, min(1.0, score))
