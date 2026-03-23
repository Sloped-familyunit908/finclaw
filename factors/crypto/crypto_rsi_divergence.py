"""
Factor: crypto_rsi_divergence
Description: RSI declining while price rises — bearish divergence (4-bar window)
Category: crypto
"""

FACTOR_NAME = "crypto_rsi_divergence"
FACTOR_DESC = "RSI divergence — RSI declining while price rises signals bearish reversal"
FACTOR_CATEGORY = "crypto"


def _rsi(closes, end_idx, period=14):
    """Compute RSI at end_idx."""
    if end_idx < period:
        return 50.0

    gains = []
    losses = []
    for i in range(end_idx - period + 1, end_idx + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = bearish divergence, High = bullish divergence."""
    if idx < 24:
        return 0.5

    window = 4

    rsi_current = _rsi(closes, idx)
    rsi_prev = _rsi(closes, idx - window)

    price_change = closes[idx] - closes[idx - window]
    rsi_change = rsi_current - rsi_prev

    if closes[idx - window] <= 0:
        return 0.5

    price_pct = price_change / closes[idx - window]

    # Bearish divergence: price up but RSI down
    if price_pct > 0.005 and rsi_change < -5:
        strength = min(abs(rsi_change) / 20.0, 1.0)
        score = 0.5 - strength * 0.4

    # Bullish divergence: price down but RSI up
    elif price_pct < -0.005 and rsi_change > 5:
        strength = min(abs(rsi_change) / 20.0, 1.0)
        score = 0.5 + strength * 0.4

    else:
        # No divergence — map RSI to score
        score = rsi_current / 100.0

    return max(0.0, min(1.0, score))
