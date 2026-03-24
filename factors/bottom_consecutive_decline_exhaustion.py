"""
Factor: bottom_consecutive_decline_exhaustion
Description: After 3+ consecutive declining days with deceleration — exhaustion reversal
Category: bottom_confirmation
"""

FACTOR_NAME = "bottom_consecutive_decline_exhaustion"
FACTOR_DESC = "3+ consecutive red days with decelerating body size — bears exhausted"
FACTOR_CATEGORY = "bottom_confirmation"


def compute(closes, highs, lows, volumes, idx):
    """After 3+ consecutive declining days, score based on how extended the
    decline is. But ONLY score high if the most recent candle shows
    deceleration (smaller body than previous).

    More consecutive red days = higher chance of reversal, but the key
    confirmation is that the decline is losing steam (smaller candles).

    This differs from just counting consecutive down days — it requires
    the deceleration signal to avoid catching the middle of a waterfall.
    """
    if idx < 5:
        return 0.5

    # Count consecutive declining days
    consecutive = 0
    for i in range(idx, 0, -1):
        if closes[i] < closes[i - 1]:
            consecutive += 1
        else:
            break

    if consecutive < 3:
        return 0.5

    # Check deceleration: today's body smaller than yesterday's
    today_body = abs(closes[idx] - closes[idx - 1])
    prev_body = abs(closes[idx - 1] - closes[idx - 2])

    if prev_body <= 0:
        # Previous day was flat — can't determine deceleration
        return 0.55

    is_decelerating = today_body < prev_body

    if not is_decelerating:
        # Decline is accelerating, not exhaustion — dangerous
        if consecutive >= 5:
            # But extremely extended declines are still somewhat interesting
            return 0.55
        return 0.5

    # Deceleration ratio: the smaller today vs yesterday, the stronger
    decel_ratio = 1.0 - (today_body / prev_body)  # 0 = same size, 1 = tiny body
    decel_ratio = max(0.0, min(1.0, decel_ratio))

    # Score based on consecutive days + deceleration strength
    if consecutive >= 7:
        base_score = 0.95
    elif consecutive >= 5:
        base_score = 0.85
    elif consecutive >= 4:
        base_score = 0.75
    else:  # consecutive == 3
        base_score = 0.65

    # Deceleration bonus
    decel_bonus = decel_ratio * 0.15

    # Additional check: deceleration for 2 consecutive days is even stronger
    if idx >= 3:
        prev_prev_body = abs(closes[idx - 2] - closes[idx - 3])
        if prev_prev_body > 0 and prev_body < prev_prev_body:
            # Two days of deceleration — very strong exhaustion
            decel_bonus += 0.05

    score = base_score + decel_bonus

    return max(0.0, min(1.0, score))
