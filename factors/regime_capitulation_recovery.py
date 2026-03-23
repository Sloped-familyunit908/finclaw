"""
Factor: capitulation_recovery
Description: Enhanced capitulation detection — consecutive red days with increasing volume then reversal
Category: sentiment
"""

FACTOR_NAME = "capitulation_recovery"
FACTOR_DESC = "Capitulation recovery — 3+ consecutive red days with increasing volume, then reversal candle"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Enhanced capitulation detection.
    
    Look for: 3+ consecutive red days with increasing volume,
    followed by a reversal candle (bullish).
    
    Score based on how strong the capitulation signal is:
    - 0.5 = no signal
    - 0.6-0.7 = mild capitulation forming
    - 0.8-1.0 = strong capitulation with reversal (buy signal)
    """
    if idx < 5:
        return 0.5

    # Check if today is a potential reversal candle
    is_green_today = closes[idx] > closes[idx - 1] if idx >= 1 else False
    today_lower_shadow = closes[idx] - lows[idx] if closes[idx] > lows[idx] else 0.0
    today_body = abs(closes[idx] - closes[idx - 1]) if idx >= 1 else 0.0
    today_range = highs[idx] - lows[idx]

    # Strong reversal: close near high, long lower shadow
    reversal_strength = 0.0
    if today_range > 0:
        close_position = (closes[idx] - lows[idx]) / today_range
        reversal_strength = close_position  # 1.0 = closed at high

    # Count consecutive red days before today
    red_days = 0
    volume_increasing = True
    total_decline = 0.0

    for i in range(idx - 1, max(idx - 15, 0), -1):
        if i < 1:
            break

        if closes[i] < closes[i - 1]:
            red_days += 1
            if closes[i - 1] > 0:
                total_decline += (closes[i - 1] - closes[i]) / closes[i - 1]

            # Check if volume is increasing during decline
            if i < idx - 1 and volumes[i] < volumes[i + 1]:
                # Not strictly increasing, slightly relax
                pass
            if i > 1 and volumes[i] < volumes[i - 1]:
                volume_increasing = False
        else:
            break

    if red_days < 3:
        return 0.5  # no capitulation pattern

    # Calculate capitulation score
    # More red days = stronger signal
    red_score = min(red_days / 7.0, 1.0)  # 3-7 days

    # Larger total decline = stronger signal
    decline_score = min(total_decline / 0.15, 1.0)  # up to 15% decline

    # Volume increasing during decline is key
    vol_score = 0.7 if volume_increasing else 0.4

    # Combine
    capitulation_strength = (red_score * 0.3 + decline_score * 0.3 + vol_score * 0.4)

    # Apply reversal bonus
    if is_green_today:
        # Reversal candle confirms capitulation
        base_score = 0.5 + capitulation_strength * 0.5 * reversal_strength
    else:
        # Still in capitulation, moderate bullish (contrarian)
        base_score = 0.5 + capitulation_strength * 0.2

    return max(0.0, min(1.0, base_score))
