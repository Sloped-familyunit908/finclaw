"""
Factor: fibonacci_retracement
Description: Price at key Fibonacci level of recent move
Category: support_resistance
"""

FACTOR_NAME = "fibonacci_retracement"
FACTOR_DESC = "Fibonacci retracement — price at 38.2%, 50%, or 61.8% level"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Check if price is near key Fibonacci retracement levels."""
    lookback = 30
    if idx < lookback:
        return 0.5

    # Find swing high and swing low in lookback period
    swing_high = max(highs[idx - lookback + 1:idx + 1])
    swing_low = min(lows[idx - lookback + 1:idx + 1])
    move = swing_high - swing_low

    if move <= 0:
        return 0.5

    price = closes[idx]

    # Fibonacci levels (retracement from high)
    fib_382 = swing_high - move * 0.382
    fib_500 = swing_high - move * 0.500
    fib_618 = swing_high - move * 0.618

    # Check proximity to each level (within 2% of the move)
    threshold = move * 0.02

    near_382 = abs(price - fib_382) < threshold
    near_500 = abs(price - fib_500) < threshold
    near_618 = abs(price - fib_618) < threshold

    # Find high and low indices to determine direction
    high_idx = idx - lookback + 1
    low_idx = idx - lookback + 1
    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] == swing_high:
            high_idx = i
        if lows[i] == swing_low:
            low_idx = i

    uptrend = high_idx > low_idx  # Move was up, now retracing down

    if near_618:
        # 61.8% retracement = deep, strong support
        score = 0.75 if uptrend else 0.35
    elif near_500:
        # 50% retracement
        score = 0.7 if uptrend else 0.35
    elif near_382:
        # 38.2% = shallow retracement, strong trend
        score = 0.7 if uptrend else 0.4
    else:
        # Not at a fib level
        if price > fib_382:
            score = 0.6  # Above all fib levels = strong
        elif price < fib_618:
            score = 0.35  # Below all fib levels = weak
        else:
            score = 0.5

    return max(0.0, min(1.0, score))
