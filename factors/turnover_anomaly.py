"""
Auto-generated factor: turnover_anomaly
Description: Abnormal turnover detection — today's amount vs 20-day average, z-score style
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "turnover_anomaly"
FACTOR_DESC = "Abnormal turnover detection — today's amount vs 20-day average, z-score style"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Z-score of today's volume*close relative to 20-day mean, normalized to [0,1]."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Calculate turnover (volume * close) for last 20 days
    turnovers = []
    for i in range(idx - lookback + 1, idx + 1):
        turnovers.append(volumes[i] * closes[i])

    today_turnover = turnovers[-1]

    # Mean
    mean_t = sum(turnovers) / float(lookback)

    # Std dev
    sq_diff_sum = 0.0
    for t in turnovers:
        sq_diff_sum += (t - mean_t) ** 2
    std_t = (sq_diff_sum / float(lookback)) ** 0.5

    if std_t <= 0:
        return 0.5

    z_score = (today_turnover - mean_t) / std_t

    # Normalize: z-score from [-2, +2] maps to [0, 1]
    score = (z_score + 2.0) / 4.0
    return max(0.0, min(1.0, score))
