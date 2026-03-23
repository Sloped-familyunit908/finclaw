"""Qlib Alpha158 CORD: Correlation between return changes and volume changes."""
FACTOR_NAME = "qlib_cord_20d"
FACTOR_DESC = "Correlation between daily return ratio and volume change ratio over 20 days"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = positive return-volume change correlation."""
    if idx < WINDOW + 1:
        return 0.5

    rets = []
    vol_changes = []

    for i in range(idx - WINDOW + 1, idx + 1):
        if closes[i - 1] == 0 or volumes[i - 1] == 0:
            continue
        ret = closes[i] / closes[i - 1]  # price change ratio
        vol_chg = volumes[i] / (volumes[i - 1] + 1e-12)  # volume change ratio
        rets.append(ret)
        vol_changes.append(vol_chg)

    n = len(rets)
    if n < 5:
        return 0.5

    mean_r = sum(rets) / n
    mean_v = sum(vol_changes) / n

    cov = 0.0
    var_r = 0.0
    var_v = 0.0

    for i in range(n):
        dr = rets[i] - mean_r
        dv = vol_changes[i] - mean_v
        cov += dr * dv
        var_r += dr * dr
        var_v += dv * dv

    denom = (var_r * var_v) ** 0.5
    if denom < 1e-12:
        return 0.5

    corr = cov / denom  # in [-1, 1]
    score = 0.5 + corr * 0.5  # map to [0, 1]

    return max(0.0, min(1.0, score))
