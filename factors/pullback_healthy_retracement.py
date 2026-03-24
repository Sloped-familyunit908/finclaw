"""
Factor: pullback_healthy_retracement
Description: After a >15% rally over 20 days, a 3-8% pullback on declining
  volume = healthy consolidation, not breakdown.
Category: pullback_strategy
"""

FACTOR_NAME = "pullback_healthy_retracement"
FACTOR_DESC = (
    "Healthy 3-8% pullback on declining volume after a 15%+ rally"
)
FACTOR_CATEGORY = "pullback_strategy"


def compute(closes, highs, lows, volumes, idx):
    """
    Logic
    -----
    1. Find peak in last 10 bars
    2. Measure rally: from 20 bars before peak to peak — need >15%
    3. Measure pullback from peak to now — 3-8% is "healthy"
    4. Bonus: volume declining during pullback (avg of last 3-5 bars < avg of rally phase)

    Score high when pullback is in the healthy range + volume is drying up.
    Score low when pullback is too deep (>12%) or too shallow (<1%).
    """
    if idx < 30:
        return 0.5

    # ── Find recent peak (highest close in last 10 bars) ──
    peak_start = max(0, idx - 9)
    peak_val = closes[peak_start]
    peak_idx = peak_start
    for i in range(peak_start, idx + 1):
        if closes[i] > peak_val:
            peak_val = closes[i]
            peak_idx = i

    # Need peak to be at least 3 bars ago (pullback needs time)
    bars_since_peak = idx - peak_idx
    if bars_since_peak < 2:
        return 0.5  # no pullback yet

    # ── Measure rally: 20 bars before peak to peak ──
    rally_base_idx = max(0, peak_idx - 20)
    rally_base = closes[rally_base_idx]
    if rally_base <= 0:
        return 0.5
    rally_pct = (peak_val - rally_base) / rally_base

    if rally_pct < 0.15:
        return 0.5  # no significant rally preceded this

    # ── Measure pullback from peak ──
    if peak_val <= 0:
        return 0.5
    pullback_pct = (peak_val - closes[idx]) / peak_val

    # Classify pullback depth
    if pullback_pct < 0.01:
        return 0.5  # barely pulled back
    elif pullback_pct <= 0.03:
        depth_score = 0.5  # very shallow
    elif pullback_pct <= 0.05:
        depth_score = 1.0  # ideal healthy pullback
    elif pullback_pct <= 0.08:
        depth_score = 0.85  # still healthy
    elif pullback_pct <= 0.12:
        depth_score = 0.4  # getting deep
    else:
        return 0.15  # too deep — likely breakdown, not pullback

    # ── Volume analysis: declining during pullback? ──
    # Compare average volume during pullback vs average during rally
    pb_bars = min(bars_since_peak, 5)
    pb_vol = sum(volumes[idx - pb_bars + 1 : idx + 1]) / max(pb_bars, 1)

    rally_bars = min(peak_idx - rally_base_idx, 10)
    if rally_bars <= 0:
        vol_score = 0.5
    else:
        rally_vol_start = max(0, peak_idx - rally_bars)
        rally_vol = sum(volumes[rally_vol_start : peak_idx + 1]) / max(rally_bars, 1)
        if rally_vol <= 0:
            vol_score = 0.5
        else:
            vol_ratio = pb_vol / rally_vol
            if vol_ratio < 0.4:
                vol_score = 1.0  # volume dried up significantly
            elif vol_ratio < 0.6:
                vol_score = 0.8
            elif vol_ratio < 0.8:
                vol_score = 0.6
            else:
                vol_score = 0.3  # volume still high during pullback — selling pressure

    score = 0.4 + 0.6 * depth_score * (0.4 + 0.6 * vol_score)

    return max(0.0, min(1.0, score))
