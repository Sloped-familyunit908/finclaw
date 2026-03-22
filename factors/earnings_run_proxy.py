"""
Auto-generated factor: earnings_run_proxy
Description: Gradual price increase with tightening range (anticipation pattern)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "earnings_run_proxy"
FACTOR_DESC = "Gradual price increase with tightening range (anticipation pattern)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect gradual price increase with tightening daily range."""

    lookback = 15
    if idx < lookback:
        return 0.5

    # Check price trend: gradual up
    up_days = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_days += 1
    up_ratio = up_days / float(lookback)

    # Overall return
    total_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0.0

    # Range tightening: compare first half range to second half range
    first_half_range = 0.0
    for i in range(idx - lookback, idx - lookback // 2):
        first_half_range += highs[i] - lows[i]

    second_half_range = 0.0
    for i in range(idx - lookback // 2, idx + 1):
        second_half_range += highs[i] - lows[i]

    range_tightening = first_half_range > second_half_range * 1.2 if second_half_range > 0 else False

    # Anticipation pattern: gradual up + tightening range
    score = 0.5
    if total_return > 0.02 and up_ratio > 0.55:
        score += 0.15
    if range_tightening:
        score += 0.15
    if total_return > 0.02 and up_ratio > 0.55 and range_tightening:
        score = 0.85

    return max(0.0, min(1.0, score))
