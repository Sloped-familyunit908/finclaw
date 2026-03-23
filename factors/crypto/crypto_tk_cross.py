"""
Factor: crypto_tk_cross
Description: Tenkan crosses Kijun (golden/death cross signal)
Category: crypto
"""

FACTOR_NAME = "crypto_tk_cross"
FACTOR_DESC = "Tenkan crosses Kijun (golden/death cross signal)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = bullish cross (tenkan above kijun), <0.5 = bearish."""
    if idx < 27:
        return 0.5

    def calc_tenkan_kijun(i):
        t = (max(highs[i - 9:i]) + min(lows[i - 9:i])) / 2.0
        k = (max(highs[i - 26:i]) + min(lows[i - 26:i])) / 2.0
        return t, k

    t_now, k_now = calc_tenkan_kijun(idx)
    t_prev, k_prev = calc_tenkan_kijun(idx - 1)

    if k_now <= 0:
        return 0.5

    # Current spread
    spread = (t_now - k_now) / k_now
    # Cross detection
    crossed_up = t_prev <= k_prev and t_now > k_now
    crossed_down = t_prev >= k_prev and t_now < k_now

    if crossed_up:
        return 0.85
    elif crossed_down:
        return 0.15

    score = 0.5 + spread * 20.0
    return max(0.0, min(1.0, score))
