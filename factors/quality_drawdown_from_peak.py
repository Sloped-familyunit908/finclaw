"""
Quality Factor: Drawdown from Peak
=====================================
Current drawdown from 120-day peak.
If drawn down >40% = potentially in structural decline (like solar industry).
Score inversely: small drawdown = high score.

Category: quality_filter
"""

FACTOR_NAME = "quality_drawdown_from_peak"
FACTOR_DESC = "Drawdown from 120-day peak — large drawdown means structural decline"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = min(120, idx + 1)
    if lookback < 10:
        return 0.5

    # Find 120-day peak
    peak = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] > peak:
            peak = highs[i]

    if peak <= 0:
        return 0.5

    drawdown = (peak - closes[idx]) / peak  # 0.0 = no drawdown, 0.40 = 40% down

    # Map: 0.0 -> 1.0 (no drawdown = best), 0.40 -> 0.0 (40% drawdown = worst)
    score = 1.0 - drawdown / 0.40
    return max(0.0, min(1.0, score))
