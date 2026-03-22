"""
Auto-generated factor: price_impact
Description: |daily return| / log(volume+1) - how much price moves per unit volume
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "price_impact"
FACTOR_DESC = "|daily return| / log(volume+1) - how much price moves per unit volume"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Price impact: |return| / ln(volume+1) averaged over 10 days."""

    lookback = 10
    if idx < lookback:
        return 0.5

    total_impact = 0.0
    valid = 0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0 and volumes[i] > 0:
            abs_ret = abs((closes[i] - closes[i - 1]) / closes[i - 1])
            # Natural log approximation without import:
            # ln(x) via iterative: use builtin **
            vol_log = 0.0
            v = float(volumes[i] + 1)
            # Fast log approximation: log(v) = log2(v) / log2(e)
            # Use: log(v) ~ (v**0.0001 - 1) / 0.0001 is bad for large v
            # Better: count powers of 10
            temp = v
            while temp > 10.0:
                vol_log += 2.302585  # ln(10)
                temp /= 10.0
            # Remaining part: ln(temp) for temp in [1, 10]
            # Approximation: ln(x) ~ (x-1) - (x-1)^2/2 for x near 1 is bad
            # Simple: ln(temp) ~ 2.302585 * (temp - 1) / (temp + 1) * 2  (rough)
            if temp > 1.0:
                t = (temp - 1.0) / (temp + 1.0)
                vol_log += 2.0 * t * (1.0 + t * t / 3.0 + t * t * t * t / 5.0)

            if vol_log > 0:
                impact = abs_ret / vol_log
                total_impact += impact
                valid += 1

    if valid == 0:
        return 0.5

    avg_impact = total_impact / valid

    # Lower price impact = more liquid = bullish
    score = 0.5 - avg_impact * 100.0
    return max(0.0, min(1.0, score))
