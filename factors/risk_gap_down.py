"""
Factor: risk_gap_down
Description: Open significantly below previous close — gap down risk
Category: risk_warning
"""

FACTOR_NAME = "risk_gap_down"
FACTOR_DESC = "Open >2% below previous close — overnight bad news gap down"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Gap down: today's open significantly below yesterday's close.
    Approximate open as: if today's low < yesterday's close by >2%, gap down.
    Since we don't have open prices, use low vs prev close as proxy.
    Also check if close is below previous close to confirm the gap held.
    """
    if idx < 1:
        return 0.5

    prev_close = closes[idx - 1]
    if prev_close <= 0:
        return 0.5

    # Approximate gap: today's high < prev close means definite gap down
    # More common: today's low < prev close significantly
    # Best proxy without open: if the low is far below prev close
    # and the close is also below prev close

    # Use the gap between prev close and today's low as a proxy for gap size
    gap = (prev_close - lows[idx]) / prev_close

    if gap < 0.02:
        return 0.5  # Less than 2% gap — not significant

    # Check if close confirmed the gap (stayed down)
    close_gap = (prev_close - closes[idx]) / prev_close

    if close_gap <= 0:
        # Gap filled — less risky
        return 0.55

    # Score based on gap size
    gap_score = min(1.0, gap / 0.08)  # 8% gap = max score

    # Unfilled gap is worse
    fill_ratio = close_gap / gap if gap > 0 else 0
    fill_bonus = min(0.2, fill_ratio * 0.2)

    score = 0.6 + 0.3 * gap_score + fill_bonus

    return max(0.0, min(1.0, score))
