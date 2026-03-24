"""
Factor: risk_declining_rsi_trend
Description: RSI making lower highs even if price flat — hidden weakness
Category: risk_warning
"""

FACTOR_NAME = "risk_declining_rsi_trend"
FACTOR_DESC = "RSI lower highs over 20 bars even with flat price — hidden bearish weakness"
FACTOR_CATEGORY = "risk_warning"


def _calc_rsi(closes, end_idx, period=14):
    """Calculate RSI at a given index."""
    if end_idx < period:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute(closes, highs, lows, volumes, idx):
    """RSI has been making lower highs over 20 bars even if price is flat.
    Hidden weakness — momentum declining beneath the surface.
    """
    lookback = 20
    if idx < lookback + 14:  # Need enough data for RSI + lookback
        return 0.5

    # Calculate RSI for each bar in lookback period
    rsi_values = []
    for i in range(idx - lookback + 1, idx + 1):
        rsi_values.append(_calc_rsi(closes, i))

    # Find RSI peaks (local maxima)
    rsi_peaks = []
    for i in range(1, len(rsi_values) - 1):
        if rsi_values[i] > rsi_values[i - 1] and rsi_values[i] > rsi_values[i + 1]:
            rsi_peaks.append(rsi_values[i])

    if len(rsi_peaks) < 2:
        return 0.5

    # Check if RSI peaks are declining
    declining_count = 0
    for i in range(1, len(rsi_peaks)):
        if rsi_peaks[i] < rsi_peaks[i - 1]:
            declining_count += 1

    if declining_count == 0:
        return 0.5

    decline_ratio = declining_count / (len(rsi_peaks) - 1)

    if decline_ratio < 0.5:
        return 0.5  # Not a clear declining trend

    # Check if price is roughly flat while RSI declines (hidden divergence)
    if closes[idx - lookback + 1] > 0:
        price_change = abs(closes[idx] - closes[idx - lookback + 1]) / closes[idx - lookback + 1]
    else:
        price_change = 0

    # Flat price + declining RSI = highest risk
    if price_change < 0.05:  # Price within 5% = "flat"
        flatness_bonus = 0.15
    else:
        flatness_bonus = 0.0

    score = 0.55 + 0.3 * decline_ratio + flatness_bonus

    return max(0.0, min(1.0, score))
