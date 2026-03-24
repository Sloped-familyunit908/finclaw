"""
Factor: risk_high_volatility
Description: ATR > 5% of price — extremely volatile
Category: risk_warning
"""

FACTOR_NAME = "risk_high_volatility"
FACTOR_DESC = "ATR >5% of price — extremely volatile, unpredictable"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """High volatility risk: ATR as percentage of price.
    ATR > 5% = dangerous, unpredictable moves.
    """
    period = 14
    if idx < period:
        return 0.5

    # Calculate ATR
    tr_sum = 0.0
    for i in range(idx - period + 1, idx + 1):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_sum += tr

    atr = tr_sum / period

    if closes[idx] <= 0:
        return 0.5

    atr_pct = atr / closes[idx]

    if atr_pct < 0.02:
        return 0.5  # Normal volatility

    if atr_pct < 0.05:
        # Elevated volatility
        score = 0.5 + (atr_pct - 0.02) / 0.03 * 0.3
    else:
        # Extreme volatility
        score = 0.8 + min(0.2, (atr_pct - 0.05) / 0.05 * 0.2)

    return max(0.0, min(1.0, score))
