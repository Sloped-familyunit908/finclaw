"""
Factor: crypto_breakout_retest
Description: Price broke above resistance, pulled back to test it
Category: crypto
"""

FACTOR_NAME = "crypto_breakout_retest"
FACTOR_DESC = "Breakout and retest pattern detection"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 1 = bullish retest, near 0 = bearish retest."""
    lookback = 48
    check_window = 12
    if idx < lookback + check_window:
        return 0.5

    # Find resistance: max high in the lookback before the check window
    resistance = max(highs[idx - lookback - check_window:idx - check_window])

    # Did price break above resistance in check window?
    broke_above = False
    for i in range(idx - check_window, idx):
        if closes[i] > resistance:
            broke_above = True
            break

    if not broke_above:
        # Check for breakdown and retest from below
        support = min(lows[idx - lookback - check_window:idx - check_window])
        broke_below = False
        for i in range(idx - check_window, idx):
            if closes[i] < support:
                broke_below = True
                break

        if broke_below and closes[idx] >= support * 0.998 and closes[idx] <= support * 1.005:
            return 0.2  # Bearish retest of broken support
        return 0.5

    # Price broke above, is it now retesting resistance?
    if resistance <= 0:
        return 0.5

    dist_from_resistance = (closes[idx] - resistance) / resistance

    if -0.005 <= dist_from_resistance <= 0.01:
        # Sitting right on old resistance = successful retest
        return 0.8
    elif dist_from_resistance > 0.01:
        # Well above = strong breakout but no retest
        return 0.6
    else:
        # Fell back below = failed breakout
        return 0.3

    return 0.5
