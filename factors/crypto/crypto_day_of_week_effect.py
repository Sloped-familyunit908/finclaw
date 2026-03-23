"""
Factor: crypto_day_of_week_effect
Description: Historical performance by weekly cycle position (idx%168)
Category: crypto
"""

FACTOR_NAME = "crypto_day_of_week_effect"
FACTOR_DESC = "Weekly cycle effect — performance varies by day of week"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Reflects historical return at this weekly position."""
    if idx < 336:  # Need at least 2 weeks
        return 0.5

    weekly_pos = idx % 168  # Position in weekly cycle
    tolerance = 4  # +/- 4 hours around same weekly position

    returns = []
    # Look back through available data for same weekly position
    check_idx = idx - 168
    while check_idx > 0 and len(returns) < 8:
        for offset in range(-tolerance, tolerance + 1):
            ci = check_idx + offset
            if 0 < ci < len(closes) and closes[ci - 1] > 0:
                ret = (closes[ci] - closes[ci - 1]) / closes[ci - 1]
                returns.append(ret)
                break
        check_idx -= 168

    if len(returns) < 2:
        return 0.5

    avg_ret = sum(returns) / len(returns)
    score = 0.5 + avg_ret * 200.0  # Scale small returns
    return max(0.0, min(1.0, score))
