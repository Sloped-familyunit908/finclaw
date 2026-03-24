"""
Factor: top_acceleration_exhaustion
Description: Price momentum slowing after strong rally — exhaustion at top
Category: top_escape
"""

FACTOR_NAME = "top_acceleration_exhaustion"
FACTOR_DESC = "5-day return >10% but last 2 days <1% each — momentum exhaustion at top"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Rate of price increase slowing down.
    If 5-day return > 10% but last 2 days < 1% each,
    momentum is exhausting at the top.
    """
    if idx < 5:
        return 0.5

    if closes[idx - 5] <= 0:
        return 0.5

    # 5-day return
    five_day_return = (closes[idx] - closes[idx - 5]) / closes[idx - 5]

    if five_day_return < 0.05:
        return 0.5  # Not a strong rally

    # Last 2 days' individual returns
    if closes[idx - 1] <= 0 or closes[idx - 2] <= 0:
        return 0.5

    day1_return = abs(closes[idx] - closes[idx - 1]) / closes[idx - 1]
    day2_return = abs(closes[idx - 1] - closes[idx - 2]) / closes[idx - 2]

    # Both recent days should have small moves
    if day1_return > 0.02 or day2_return > 0.02:
        return 0.5  # Still moving — not exhaustion

    # Score based on contrast between rally strength and recent stall
    rally_score = min(1.0, five_day_return / 0.15)  # 15% rally = max

    # The smaller recent moves are, the stronger exhaustion
    stall_score = 1.0 - max(day1_return, day2_return) / 0.02

    # Check if returns are also decelerating (day -3 to -4 had bigger moves)
    decel_bonus = 0.0
    if idx >= 4 and closes[idx - 3] > 0:
        day3_return = abs(closes[idx - 2] - closes[idx - 3]) / closes[idx - 3]
        if day3_return > max(day1_return, day2_return) * 2:
            decel_bonus = 0.1

    score = 0.6 + 0.3 * rally_score * stall_score + decel_bonus

    return max(0.0, min(1.0, score))
