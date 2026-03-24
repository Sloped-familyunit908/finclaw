"""
Factor: pullback_volume_dry_up
Description: Volume decreasing during pullback phase (last 3-5 bars declining).
  Low volume pullback = no panic selling = pullback will end soon.
Category: pullback_strategy
"""

FACTOR_NAME = "pullback_volume_dry_up"
FACTOR_DESC = (
    "Volume drying up during pullback — no panic selling, reversal imminent"
)
FACTOR_CATEGORY = "pullback_strategy"


def _calc_ma(closes, end_idx, period):
    """Simple moving average ending at end_idx (inclusive)."""
    if end_idx < period - 1:
        return None
    return sum(closes[end_idx - period + 1 : end_idx + 1]) / period


def compute(closes, highs, lows, volumes, idx):
    """
    Logic
    -----
    1. Detect we're in a pullback: price declining over last 3-5 bars
    2. Check if volume is also declining each bar (or at least trending down)
    3. Compare pullback volume to pre-pullback average volume
    4. Lower volume during pullback → higher score

    "Volume leads price" — if volume dries up during a dip, sellers are
    exhausted and a bounce is likely.
    """
    if idx < 25:
        return 0.5

    # ── Step 1: Are we in a pullback? (price declining recently) ──
    # Check last 5 bars
    pb_len = min(5, idx)
    price_change = closes[idx] - closes[idx - pb_len]
    if price_change >= 0:
        return 0.5  # price not declining — no pullback to evaluate

    # ── Step 2: Volume declining bar-over-bar? ──
    declining_bars = 0
    for i in range(idx - pb_len + 1, idx + 1):
        if volumes[i] < volumes[i - 1]:
            declining_bars += 1

    # At least half the bars should show declining volume
    vol_trend_score = declining_bars / max(pb_len, 1)

    # ── Step 3: Pullback volume vs prior average ──
    # Average volume of last pb_len bars (pullback phase)
    pb_vol = sum(volumes[idx - pb_len + 1 : idx + 1]) / max(pb_len, 1)

    # Average volume of 10 bars before the pullback
    pre_start = max(0, idx - pb_len - 10)
    pre_end = idx - pb_len
    pre_bars = pre_end - pre_start
    if pre_bars <= 0:
        return 0.5
    pre_vol = sum(volumes[pre_start : pre_end + 1]) / max(pre_bars, 1)

    if pre_vol <= 0:
        return 0.5

    vol_ratio = pb_vol / pre_vol

    if vol_ratio < 0.3:
        ratio_score = 1.0  # volume dried up dramatically
    elif vol_ratio < 0.5:
        ratio_score = 0.85
    elif vol_ratio < 0.7:
        ratio_score = 0.65
    elif vol_ratio < 0.9:
        ratio_score = 0.45
    else:
        ratio_score = 0.2  # volume not declining — sellers still active

    # ── Step 4: Context — is there an uptrend to bounce into? ──
    ma20 = _calc_ma(closes, idx, 20)
    trend_bonus = 1.0
    if ma20 is not None and ma20 > 0:
        ma20_prev = _calc_ma(closes, max(0, idx - 5), 20)
        if ma20_prev and ma20_prev > 0 and (ma20 - ma20_prev) / ma20_prev > 0:
            trend_bonus = 1.0  # uptrend — volume dry-up is more meaningful
        else:
            trend_bonus = 0.6  # downtrend — volume dry-up less reliable

    # ── Combine ──
    raw = 0.3 + 0.7 * (0.5 * vol_trend_score + 0.5 * ratio_score) * trend_bonus

    return max(0.0, min(1.0, raw))
