"""Qlib Alpha158 CNTD: Net positive vs negative day count difference."""
FACTOR_NAME = "qlib_cntd_20d"
FACTOR_DESC = "Fraction of up days minus fraction of down days over 20 days"
FACTOR_CATEGORY = "qlib_alpha158"

WINDOW = 20


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = more up days, <0.5 = more down days."""
    if idx < WINDOW:
        return 0.5

    cnt_pos = 0
    cnt_neg = 0

    for i in range(idx - WINDOW + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            cnt_pos += 1
        elif closes[i] < closes[i - 1]:
            cnt_neg += 1

    cntp = cnt_pos / float(WINDOW)
    cntn = cnt_neg / float(WINDOW)
    cntd = cntp - cntn  # in [-1, 1]

    score = 0.5 + cntd * 0.5  # map to [0, 1]
    return max(0.0, min(1.0, score))
