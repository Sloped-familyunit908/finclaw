"""
Factor: risk_consecutive_losses
Description: 5+ consecutive red days — clear downtrend
Category: risk_warning
"""

FACTOR_NAME = "risk_consecutive_losses"
FACTOR_DESC = "5+ consecutive red days — trend clearly down, don't fight it"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Count consecutive red (down) days ending at current bar.
    5+ consecutive losses = strong risk warning.
    """
    if idx < 1:
        return 0.5

    # Count consecutive down days
    consecutive = 0
    for i in range(idx, 0, -1):
        if closes[i] < closes[i - 1]:
            consecutive += 1
        else:
            break

    if consecutive < 3:
        return 0.5

    if consecutive < 5:
        # 3-4 days: mild warning
        score = 0.5 + (consecutive - 3) * 0.1
        return max(0.0, min(1.0, score))

    # 5+ consecutive losses
    if consecutive >= 8:
        return 1.0
    elif consecutive >= 7:
        return 0.95
    elif consecutive >= 6:
        return 0.85
    elif consecutive >= 5:
        return 0.75

    return 0.5
