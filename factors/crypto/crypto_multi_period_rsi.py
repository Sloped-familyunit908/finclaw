"""
Factor: crypto_multi_period_rsi
Description: Average of RSI(6), RSI(12), RSI(24) — multi-timeframe RSI
Category: crypto
"""

FACTOR_NAME = "crypto_multi_period_rsi"
FACTOR_DESC = "Multi-period RSI — average of RSI(6), RSI(12), RSI(24)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Combined RSI across three periods."""
    if idx < 48:
        return 0.5

    def calc_rsi(period):
        if idx < period + 1:
            return 0.5
        gains = 0.0
        losses = 0.0
        for i in range(idx - period, idx):
            change = closes[i + 1] - closes[i]
            if change > 0:
                gains += change
            else:
                losses += abs(change)

        if gains + losses == 0:
            return 0.5
        rs = gains / losses if losses > 0 else 100.0
        rsi = 1.0 - 1.0 / (1.0 + rs)
        return rsi

    rsi_6 = calc_rsi(6)
    rsi_12 = calc_rsi(12)
    rsi_24 = calc_rsi(24)

    avg_rsi = (rsi_6 + rsi_12 + rsi_24) / 3.0
    return max(0.0, min(1.0, avg_rsi))
