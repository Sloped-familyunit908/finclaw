"""
Automatic Strategy Evolution Engine
====================================
Runs 24/7. Each generation:
1. Take current best strategy parameters
2. Mutate parameters randomly (genetic algorithm)
3. Backtest all mutations on local CSV data
4. Keep top performers
5. Repeat

Uses local CSV data only — no API calls needed.
Separate from the YAML-DSL evolution engine (engine.py).
This is pure numerical parameter optimization via genetic algorithms.

v2: 12-signal scoring system with MACD, Bollinger, KDJ, OBV, MA alignment,
    candle patterns, volume profile, support/resistance.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ────────────────── Weight keys (shared constant) ──────────────────

_WEIGHT_KEYS: List[str] = [
    "w_momentum",
    "w_mean_reversion",
    "w_volume",
    "w_trend",
    "w_pattern",
    "w_macd",
    "w_bollinger",
    "w_kdj",
    "w_obv",
    "w_support",
    "w_volume_profile",
]


@dataclass
class StrategyDNA:
    """All tunable parameters for a trading strategy."""

    # --- Selection thresholds ---
    min_score: int = 6
    rsi_buy_threshold: float = 35.0
    rsi_sell_threshold: float = 75.0
    r2_min: float = 0.5
    slope_min: float = 0.5  # daily %
    volume_ratio_min: float = 1.2

    # --- Execution ---
    hold_days: int = 3
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 20.0
    max_positions: int = 2

    # --- Golden dip specific ---
    dip_threshold_pct: float = 10.0  # pullback from high
    r2_trend_min: float = 0.6  # min R² for bull stock confirmation

    # --- Scoring weights (12 dimensions, auto-normalized to sum=1) ---
    # Original 5
    w_momentum: float = 0.1       # RSI + slope
    w_mean_reversion: float = 0.1 # RSI oversold
    w_volume: float = 0.1         # volume ratio
    w_trend: float = 0.1          # R² + MA alignment
    w_pattern: float = 0.1        # candle patterns
    # New 6
    w_macd: float = 0.1           # MACD golden/death cross
    w_bollinger: float = 0.1      # Bollinger Band position
    w_kdj: float = 0.1            # KDJ golden cross
    w_obv: float = 0.1            # OBV trend (price-volume)
    w_support: float = 0.05       # support/resistance proximity
    w_volume_profile: float = 0.05  # volume profile shape

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyDNA":
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# Valid ranges for each parameter — (min, max, is_int)
_PARAM_RANGES: Dict[str, Tuple[float, float, bool]] = {
    "min_score": (1, 10, True),
    "rsi_buy_threshold": (10.0, 50.0, False),
    "rsi_sell_threshold": (55.0, 95.0, False),
    "r2_min": (0.1, 0.95, False),
    "slope_min": (0.1, 3.0, False),
    "volume_ratio_min": (0.5, 5.0, False),
    "hold_days": (2, 20, True),  # A-share T+1: minimum 2 days (buy T+1, sell T+2)
    "stop_loss_pct": (0.5, 10.0, False),
    "take_profit_pct": (3.0, 50.0, False),
    "max_positions": (1, 10, True),
    "dip_threshold_pct": (3.0, 30.0, False),
    "r2_trend_min": (0.2, 0.95, False),
    # Original weights
    "w_momentum": (0.0, 1.0, False),
    "w_mean_reversion": (0.0, 1.0, False),
    "w_volume": (0.0, 1.0, False),
    "w_trend": (0.0, 1.0, False),
    "w_pattern": (0.0, 1.0, False),
    # New weights
    "w_macd": (0.0, 1.0, False),
    "w_bollinger": (0.0, 1.0, False),
    "w_kdj": (0.0, 1.0, False),
    "w_obv": (0.0, 1.0, False),
    "w_support": (0.0, 1.0, False),
    "w_volume_profile": (0.0, 1.0, False),
}


@dataclass
class EvolutionResult:
    """Result of one strategy evaluation."""

    dna: StrategyDNA
    annual_return: float
    max_drawdown: float
    win_rate: float
    sharpe: float
    calmar: float
    total_trades: int
    profit_factor: float
    fitness: float = 0.0

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "dna"}
        d["dna"] = self.dna.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EvolutionResult":
        dna = StrategyDNA.from_dict(d.pop("dna"))
        return cls(dna=dna, **d)


def compute_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Compute RSI indicator. Returns list same length as input (NaN-padded)."""
    rsi = [float("nan")] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)

    return rsi


def compute_linear_regression(
    values: List[float], window: int = 20
) -> Tuple[List[float], List[float]]:
    """Compute rolling R² and slope over a window.

    Returns (r2_list, slope_list), same length as input, NaN-padded.
    Slope is expressed as daily % return.
    """
    n = len(values)
    r2_out = [float("nan")] * n
    slope_out = [float("nan")] * n

    if n < window:
        return r2_out, slope_out

    for i in range(window - 1, n):
        segment = values[i - window + 1 : i + 1]
        mean_y = sum(segment) / window
        mean_x = (window - 1) / 2.0

        ss_xy = 0.0
        ss_xx = 0.0
        ss_yy = 0.0
        for j, y in enumerate(segment):
            dx = j - mean_x
            dy = y - mean_y
            ss_xy += dx * dy
            ss_xx += dx * dx
            ss_yy += dy * dy

        if ss_xx == 0 or ss_yy == 0:
            r2_out[i] = 0.0
            slope_out[i] = 0.0
            continue

        slope = ss_xy / ss_xx
        r2 = (ss_xy * ss_xy) / (ss_xx * ss_yy)
        # daily % slope relative to mean price
        slope_pct = (slope / mean_y) * 100.0 if mean_y != 0 else 0.0

        r2_out[i] = max(0.0, min(1.0, r2))
        slope_out[i] = slope_pct

    return r2_out, slope_out


def compute_volume_ratio(volumes: List[float], period: int = 20) -> List[float]:
    """Compute rolling volume ratio (current / average of past N days)."""
    n = len(volumes)
    ratios = [float("nan")] * n
    if n < period + 1:
        return ratios
    for i in range(period, n):
        avg = sum(volumes[i - period : i]) / period
        ratios[i] = volumes[i] / avg if avg > 0 else 0.0
    return ratios


# ────────────────── New Signal Functions (v2) ──────────────────


def _ema(values: List[float], period: int) -> List[float]:
    """Exponential moving average. Returns list same length, NaN-padded."""
    out = [float("nan")] * len(values)
    if len(values) < period:
        return out
    # Seed with SMA
    sma = sum(values[:period]) / period
    out[period - 1] = sma
    k = 2.0 / (period + 1)
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def compute_macd(
    closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[List[float], List[float], List[float]]:
    """MACD line, signal line, histogram. Returns 3 lists same length, NaN-padded."""
    n = len(closes)
    nan_list = [float("nan")] * n
    if n < slow + signal:
        return nan_list[:], nan_list[:], nan_list[:]

    fast_ema = _ema(closes, fast)
    slow_ema = _ema(closes, slow)

    macd_line = [float("nan")] * n
    for i in range(slow - 1, n):
        if not (math.isnan(fast_ema[i]) or math.isnan(slow_ema[i])):
            macd_line[i] = fast_ema[i] - slow_ema[i]

    # Signal line = EMA of MACD line
    # Collect valid MACD values for EMA seed
    valid_macd = [(i, macd_line[i]) for i in range(n) if not math.isnan(macd_line[i])]
    signal_line = [float("nan")] * n
    hist = [float("nan")] * n

    if len(valid_macd) >= signal:
        sma = sum(v for _, v in valid_macd[:signal]) / signal
        start_idx = valid_macd[signal - 1][0]
        signal_line[start_idx] = sma
        k = 2.0 / (signal + 1)
        vi = signal
        for i in range(start_idx + 1, n):
            if not math.isnan(macd_line[i]):
                signal_line[i] = macd_line[i] * k + signal_line[i - 1] * (1 - k)
            elif not math.isnan(signal_line[i - 1]):
                signal_line[i] = signal_line[i - 1]

        for i in range(n):
            if not (math.isnan(macd_line[i]) or math.isnan(signal_line[i])):
                hist[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, hist


def compute_bollinger_bands(
    closes: List[float], window: int = 20, num_std: int = 2
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Upper, middle, lower bands, and bandwidth percentage. NaN-padded."""
    n = len(closes)
    upper = [float("nan")] * n
    middle = [float("nan")] * n
    lower = [float("nan")] * n
    bw_pct = [float("nan")] * n

    if n < window:
        return upper, middle, lower, bw_pct

    for i in range(window - 1, n):
        seg = closes[i - window + 1: i + 1]
        mean = sum(seg) / window
        var = sum((x - mean) ** 2 for x in seg) / window
        std = math.sqrt(var)
        middle[i] = mean
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
        bw_pct[i] = (num_std * 2 * std / mean * 100) if mean > 0 else 0.0

    return upper, middle, lower, bw_pct


def compute_kdj(
    highs: List[float], lows: List[float], closes: List[float], n: int = 9
) -> Tuple[List[float], List[float], List[float]]:
    """KDJ indicator. Returns K, D, J lists. NaN-padded."""
    length = len(closes)
    k_out = [float("nan")] * length
    d_out = [float("nan")] * length
    j_out = [float("nan")] * length

    if length < n:
        return k_out, d_out, j_out

    k_val = 50.0
    d_val = 50.0

    for i in range(n - 1, length):
        highest = max(highs[i - n + 1: i + 1])
        lowest = min(lows[i - n + 1: i + 1])
        denom = highest - lowest
        rsv = ((closes[i] - lowest) / denom * 100) if denom > 0 else 50.0
        k_val = 2.0 / 3.0 * k_val + 1.0 / 3.0 * rsv
        d_val = 2.0 / 3.0 * d_val + 1.0 / 3.0 * k_val
        j_val = 3.0 * k_val - 2.0 * d_val
        k_out[i] = k_val
        d_out[i] = d_val
        j_out[i] = j_val

    return k_out, d_out, j_out


def compute_obv_trend(
    closes: List[float], volumes: List[float], window: int = 10
) -> List[float]:
    """OBV trend direction. Returns list of slopes (positive = accumulation). NaN-padded."""
    n = len(closes)
    trend = [float("nan")] * n
    if n < window + 1:
        return trend

    # Build OBV series
    obv = [0.0] * n
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            obv[i] = obv[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv[i] = obv[i - 1] - volumes[i]
        else:
            obv[i] = obv[i - 1]

    # Slope of OBV over window (linear regression slope, normalized)
    for i in range(window, n):
        seg = obv[i - window + 1: i + 1]
        mean_y = sum(seg) / window
        mean_x = (window - 1) / 2.0
        ss_xy = 0.0
        ss_xx = 0.0
        for j, y in enumerate(seg):
            dx = j - mean_x
            ss_xy += dx * (y - mean_y)
            ss_xx += dx * dx
        slope = ss_xy / ss_xx if ss_xx > 0 else 0.0
        # Normalize by avg volume to get comparable values
        avg_vol = sum(volumes[i - window + 1: i + 1]) / window
        trend[i] = slope / avg_vol if avg_vol > 0 else 0.0

    return trend


def compute_ma_alignment(closes: List[float]) -> List[float]:
    """MA5/10/20/60 alignment state. 1=bullish, -1=bearish, 0=mixed. NaN-padded."""
    n = len(closes)
    result = [float("nan")] * n
    if n < 60:
        return result

    # Pre-compute running sums for efficiency
    ma5 = [float("nan")] * n
    ma10 = [float("nan")] * n
    ma20 = [float("nan")] * n
    ma60 = [float("nan")] * n

    cumsum = [0.0] * (n + 1)
    for i in range(n):
        cumsum[i + 1] = cumsum[i] + closes[i]

    for period, arr in [(5, ma5), (10, ma10), (20, ma20), (60, ma60)]:
        for i in range(period - 1, n):
            arr[i] = (cumsum[i + 1] - cumsum[i - period + 1]) / period

    for i in range(59, n):
        m5, m10, m20, m60_v = ma5[i], ma10[i], ma20[i], ma60[i]
        if m5 > m10 > m20 > m60_v:
            result[i] = 1.0   # bullish alignment
        elif m5 < m10 < m20 < m60_v:
            result[i] = -1.0  # bearish alignment
        else:
            result[i] = 0.0

    return result


def compute_candle_patterns(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    idx: int,
) -> float:
    """Candle pattern detection at idx. Returns score in [-1, +1].

    Detects: hammer, inverted hammer, doji, engulfing, three soldiers/crows.
    Positive = bullish, negative = bearish.
    """
    if idx < 2 or idx >= len(closes):
        return 0.0

    o, h, lo, c = opens[idx], highs[idx], lows[idx], closes[idx]
    body = abs(c - o)
    full_range = h - lo
    if full_range <= 0:
        return 0.0

    body_ratio = body / full_range
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - lo

    score = 0.0

    # Hammer (bullish): small body at top, long lower shadow
    if lower_shadow > body * 2 and upper_shadow < body * 0.5 and c > o:
        score += 0.3

    # Inverted hammer (potential reversal)
    if upper_shadow > body * 2 and lower_shadow < body * 0.5 and c > o:
        score += 0.15

    # Doji at bottom (indecision after decline)
    if body_ratio < 0.1 and idx >= 3:
        # Check if we were declining
        recent_decline = closes[idx - 3] > closes[idx - 1] * 1.02
        if recent_decline:
            score += 0.2

    # Bullish engulfing
    prev_o, prev_c = opens[idx - 1], closes[idx - 1]
    if prev_c < prev_o and c > o:  # prev bearish, current bullish
        if c > prev_o and o < prev_c:  # current body engulfs prev
            score += 0.35

    # Bearish engulfing
    if prev_c > prev_o and c < o:  # prev bullish, current bearish
        if c < prev_o and o > prev_c:
            score -= 0.35

    # Three white soldiers
    if idx >= 3:
        all_bullish = all(closes[idx - j] > opens[idx - j] for j in range(3))
        ascending = closes[idx] > closes[idx - 1] > closes[idx - 2]
        if all_bullish and ascending:
            score += 0.3

    # Three black crows
    if idx >= 3:
        all_bearish = all(closes[idx - j] < opens[idx - j] for j in range(3))
        descending = closes[idx] < closes[idx - 1] < closes[idx - 2]
        if all_bearish and descending:
            score -= 0.3

    return max(-1.0, min(1.0, score))


def compute_volume_profile(
    volumes: List[float], idx: int, window: int = 20
) -> float:
    """Volume profile at idx. Returns: 1=surge, -1=shrink, 0=normal."""
    if idx < window or idx >= len(volumes):
        return 0.0

    avg_vol = sum(volumes[idx - window: idx]) / window
    if avg_vol <= 0:
        return 0.0

    ratio = volumes[idx] / avg_vol
    if ratio > 2.0:
        return 1.0   # volume surge
    elif ratio < 0.5:
        return -1.0  # volume shrink
    elif ratio > 1.3:
        return 0.5
    elif ratio < 0.7:
        return -0.5
    return 0.0


def compute_support_resistance(
    closes: List[float],
    highs: List[float],
    lows: List[float],
    idx: int,
    window: int = 20,
) -> float:
    """Distance from support level as a percentage (0-1 score).

    Closer to support = higher score (more upside potential).
    """
    if idx < window or idx >= len(closes):
        return 0.5

    lookback_lows = lows[idx - window: idx]
    lookback_highs = highs[idx - window: idx]

    support = min(lookback_lows)
    resistance = max(lookback_highs)

    price = closes[idx]
    price_range = resistance - support
    if price_range <= 0:
        return 0.5

    # Position in range: 0 = at support (bullish), 1 = at resistance (bearish)
    position = (price - support) / price_range
    # Invert: closer to support = higher score
    return max(0.0, min(1.0, 1.0 - position))


# ────────────────── Scoring ──────────────────


def score_stock(
    idx: int,
    indicators: Dict[str, Any],
    dna: StrategyDNA,
) -> float:
    """Score a stock at a given index using 12-dimensional DNA weights.

    Args:
        idx: Day index to score
        indicators: Dict with pre-computed indicator arrays
        dna: Strategy parameters

    Returns score in [0, 10] range.
    """
    rsi = indicators["rsi"]
    r2 = indicators["r2"]
    slope = indicators["slope"]
    volume_ratio = indicators["volume_ratio"]
    closes = indicators["close"]

    if idx >= len(rsi) or idx >= len(r2) or idx >= len(slope) or idx >= len(volume_ratio):
        return 0.0
    if any(
        math.isnan(x)
        for x in [rsi[idx], r2[idx], slope[idx], volume_ratio[idx]]
    ):
        return 0.0

    # 1. Momentum: higher slope = better
    momentum_raw = min(slope[idx] / max(dna.slope_min, 0.01), 2.0) / 2.0

    # 2. Mean reversion: RSI near buy threshold is good
    rsi_val = rsi[idx]
    if rsi_val <= dna.rsi_buy_threshold:
        mr_raw = 1.0
    elif rsi_val >= dna.rsi_sell_threshold:
        mr_raw = 0.0
    else:
        rng = dna.rsi_sell_threshold - dna.rsi_buy_threshold
        mr_raw = 1.0 - (rsi_val - dna.rsi_buy_threshold) / rng if rng > 0 else 0.5

    # 3. Volume: higher ratio = better
    vol_raw = min(volume_ratio[idx] / max(dna.volume_ratio_min, 0.01), 2.0) / 2.0

    # 4. Trend: R² + positive slope + MA alignment
    ma_align = indicators.get("ma_alignment", [0.0] * (idx + 1))
    ma_val = ma_align[idx] if idx < len(ma_align) and not math.isnan(ma_align[idx]) else 0.0
    base_trend = r2[idx] if slope[idx] > 0 else r2[idx] * 0.3
    trend_raw = base_trend * (1.0 + 0.3 * ma_val)  # MA alignment boosts trend
    trend_raw = max(0.0, min(1.0, trend_raw))

    # 5. Pattern: golden dip + candle patterns
    lookback = min(20, idx)
    if lookback > 0:
        recent_high = max(closes[idx - lookback: idx])
        pullback = (recent_high - closes[idx]) / recent_high * 100 if recent_high > 0 else 0
        if pullback >= dna.dip_threshold_pct * 0.5 and r2[idx] >= dna.r2_trend_min:
            dip_score = min(pullback / dna.dip_threshold_pct, 1.0)
        else:
            dip_score = 0.0
    else:
        dip_score = 0.0
    candle = compute_candle_patterns(
        indicators["open"], indicators["high"], indicators["low"], closes, idx
    )
    pattern_raw = max(0.0, min(1.0, dip_score * 0.5 + (candle + 1) / 2 * 0.5))

    # 6. MACD
    macd_hist = indicators.get("macd_hist", [float("nan")] * (idx + 1))
    macd_line = indicators.get("macd_line", [float("nan")] * (idx + 1))
    macd_signal = indicators.get("macd_signal", [float("nan")] * (idx + 1))
    if idx < len(macd_hist) and not math.isnan(macd_hist[idx]) and idx >= 1 and not math.isnan(macd_hist[idx - 1]):
        # Golden cross: histogram turns positive
        if macd_hist[idx] > 0 and macd_hist[idx - 1] <= 0:
            macd_raw = 1.0
        elif macd_hist[idx] > 0:
            macd_raw = 0.7
        elif macd_hist[idx] > macd_hist[idx - 1]:  # improving
            macd_raw = 0.4
        else:
            macd_raw = 0.1
    else:
        macd_raw = 0.5

    # 7. Bollinger Bands
    bb_upper = indicators.get("bb_upper", [float("nan")] * (idx + 1))
    bb_lower = indicators.get("bb_lower", [float("nan")] * (idx + 1))
    bb_middle = indicators.get("bb_middle", [float("nan")] * (idx + 1))
    if idx < len(bb_upper) and not math.isnan(bb_upper[idx]) and not math.isnan(bb_lower[idx]):
        bb_range = bb_upper[idx] - bb_lower[idx]
        if bb_range > 0:
            bb_pos = (closes[idx] - bb_lower[idx]) / bb_range
            # Near lower band is bullish (oversold), near upper is bearish
            bb_raw = max(0.0, min(1.0, 1.0 - bb_pos))
        else:
            bb_raw = 0.5
    else:
        bb_raw = 0.5

    # 8. KDJ
    k_val_list = indicators.get("kdj_k", [float("nan")] * (idx + 1))
    d_val_list = indicators.get("kdj_d", [float("nan")] * (idx + 1))
    j_val_list = indicators.get("kdj_j", [float("nan")] * (idx + 1))
    if (idx < len(k_val_list) and idx >= 1
            and not math.isnan(k_val_list[idx]) and not math.isnan(k_val_list[idx - 1])):
        k_val = k_val_list[idx]
        d_val = d_val_list[idx]
        # KDJ golden cross: K crosses above D
        if k_val > d_val and k_val_list[idx - 1] <= d_val_list[idx - 1]:
            kdj_raw = 1.0
        elif k_val > d_val:
            kdj_raw = 0.6
        elif k_val < 20:  # oversold zone
            kdj_raw = 0.7
        else:
            kdj_raw = 0.2
    else:
        kdj_raw = 0.5

    # 9. OBV trend
    obv = indicators.get("obv_trend", [float("nan")] * (idx + 1))
    if idx < len(obv) and not math.isnan(obv[idx]):
        # Positive OBV trend = accumulation
        obv_val = obv[idx]
        if obv_val > 0.5:
            obv_raw = 1.0
        elif obv_val > 0:
            obv_raw = 0.5 + obv_val
        elif obv_val > -0.5:
            obv_raw = 0.5 + obv_val
        else:
            obv_raw = 0.0
        obv_raw = max(0.0, min(1.0, obv_raw))
    else:
        obv_raw = 0.5

    # 10. Support/Resistance
    support_raw = compute_support_resistance(
        closes, indicators["high"], indicators["low"], idx
    )

    # 11. Volume Profile
    vprofile_val = compute_volume_profile(indicators["volume"], idx)
    # Map from [-1, 1] to [0, 1]: surge is bullish when price also rising
    if vprofile_val > 0 and slope[idx] > 0:
        vprofile_raw = 0.5 + vprofile_val * 0.5  # volume surge + uptrend = bullish
    elif vprofile_val < 0 and slope[idx] > 0:
        vprofile_raw = 0.3  # low volume pullback in uptrend can be okay
    else:
        vprofile_raw = 0.5 + vprofile_val * 0.25

    vprofile_raw = max(0.0, min(1.0, vprofile_raw))

    # Weighted sum with all 11 dimensions
    raw = (
        dna.w_momentum * momentum_raw
        + dna.w_mean_reversion * mr_raw
        + dna.w_volume * vol_raw
        + dna.w_trend * trend_raw
        + dna.w_pattern * pattern_raw
        + dna.w_macd * macd_raw
        + dna.w_bollinger * bb_raw
        + dna.w_kdj * kdj_raw
        + dna.w_obv * obv_raw
        + dna.w_support * support_raw
        + dna.w_volume_profile * vprofile_raw
    )

    total_weight = sum(getattr(dna, k) for k in _WEIGHT_KEYS)
    if total_weight > 0:
        raw /= total_weight

    return raw * 10.0


def compute_fitness(
    annual_return: float,
    max_drawdown: float,
    win_rate: float,
    sharpe: float,
    total_trades: int = 200,
) -> float:
    """Compute composite fitness score.

    fitness = annual_return * sqrt(win_rate) / max(max_drawdown, 5.0) * sharpe_bonus * trade_penalty

    Rewards: high return, high win rate, low drawdown, good Sharpe, enough trades.
    Penalizes: fewer than 100 trades (statistically unreliable).
    """
    dd_denom = max(max_drawdown, 5.0)
    win_factor = math.sqrt(max(win_rate, 0.0))
    sharpe_bonus = 1.0 + max(sharpe, 0.0) * 0.2
    
    # Penalize very low trade count — results with <10 trades are pure luck
    if total_trades < 10:
        trade_penalty = 0.1  # almost worthless
    elif total_trades < 30:
        trade_penalty = total_trades / 30.0  # linear penalty
    else:
        trade_penalty = 1.0  # no penalty, 30+ trades is enough
    
    return annual_return * win_factor / dd_denom * sharpe_bonus * trade_penalty


def filter_stock_pool(
    data: Dict[str, Dict[str, list]],
    min_daily_amount: float = 20_000_000.0,
    min_price: float = 5.0,
    max_stocks: int = 500,
) -> Dict[str, Dict[str, list]]:
    """Filter stock pool by quality metrics.

    Criteria:
    - Average daily turnover (volume * close proxy) > min_daily_amount
    - Last close > min_price
    - Stocks with recent limit-up (涨停) in last 60 days get priority
    - Returns at most max_stocks best-quality stocks

    Args:
        data: Raw stock data dict
        min_daily_amount: Minimum average daily turnover in CNY
        min_price: Minimum stock price
        max_stocks: Maximum number of stocks to keep

    Returns:
        Filtered data dict
    """
    scored_codes: List[Tuple[str, float]] = []

    for code, sd in data.items():
        closes = sd["close"]
        volumes = sd["volume"]

        if not closes:
            continue

        # Last close must be > min_price
        last_close = closes[-1]
        if last_close < min_price:
            continue

        # Average daily turnover (volume * close as proxy for amount)
        recent_n = min(60, len(closes))
        avg_amount = sum(
            closes[-recent_n + i] * volumes[-recent_n + i]
            for i in range(recent_n)
        ) / recent_n

        if avg_amount < min_daily_amount:
            continue

        # Bonus: check for limit-up in last 60 days (shows market attention)
        limit_up_bonus = 0.0
        for i in range(max(1, len(closes) - 60), len(closes)):
            if closes[i - 1] > 0:
                daily_ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                # Approximate limit-up: ≥9.5% for main board, ≥19% for ChiNext/STAR
                if daily_ret >= 0.095:
                    limit_up_bonus += 1.0

        # Quality score: turnover + limit-up bonus
        quality = avg_amount / 1e8 + limit_up_bonus * 0.5
        scored_codes.append((code, quality))

    # Sort by quality, keep top max_stocks
    scored_codes.sort(key=lambda x: x[1], reverse=True)
    keep_codes = {code for code, _ in scored_codes[:max_stocks]}

    return {code: sd for code, sd in data.items() if code in keep_codes}


class AutoEvolver:
    """Automatic strategy parameter evolution engine.

    Pure genetic-algorithm approach: mutate numerical parameters,
    backtest on local CSV data, keep the fittest.
    """

    def __init__(
        self,
        data_dir: str,
        population_size: int = 30,
        elite_count: int = 5,
        mutation_rate: float = 0.3,
        results_dir: str = "evolution_results",
        seed: Optional[int] = None,
    ):
        self.data_dir = data_dir
        self.population_size = population_size
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.results_dir = results_dir
        self.rng = random.Random(seed)
        os.makedirs(results_dir, exist_ok=True)

    def load_data(
        self, quality_filter: bool = True, max_stocks: int = 500
    ) -> Dict[str, Dict[str, list]]:
        """Load stock CSV data into memory.

        Returns dict: code -> {date, open, high, low, close, volume}
        Only loads stocks with enough data (>= 60 trading days).

        When quality_filter=True, applies:
        - Average daily turnover > 20M CNY (or volume*close proxy)
        - Last close > 5 CNY
        - Stocks with recent limit-up (涨停) get priority
        - Max ``max_stocks`` best-quality stocks retained
        """
        data: Dict[str, Dict[str, list]] = {}
        data_path = Path(self.data_dir)

        if not data_path.exists():
            return data

        csv_files = list(data_path.glob("*.csv"))
        for fp in csv_files:
            try:
                lines = fp.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) < 2:
                    continue

                header = lines[0].strip().split(",")
                col_map = {h.strip(): i for i, h in enumerate(header)}

                # Required columns
                required = {"date", "open", "high", "low", "close", "volume"}
                if not required.issubset(col_map.keys()):
                    continue

                dates = []
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []

                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if len(parts) > max(col_map.values()):
                        try:
                            dates.append(parts[col_map["date"]])
                            opens.append(float(parts[col_map["open"]]))
                            highs.append(float(parts[col_map["high"]]))
                            lows.append(float(parts[col_map["low"]]))
                            closes.append(float(parts[col_map["close"]]))
                            volumes.append(float(parts[col_map["volume"]]))
                        except (ValueError, IndexError):
                            continue

                if len(closes) >= 60:
                    code = fp.stem
                    data[code] = {
                        "date": dates,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                    }
            except Exception:
                continue

        if quality_filter and len(data) > max_stocks:
            data = filter_stock_pool(data, max_stocks=max_stocks)

        return data

    def mutate(self, dna: StrategyDNA) -> StrategyDNA:
        """Create a mutated copy of a strategy DNA.

        Each parameter has ``mutation_rate`` chance of being modified.
        Mutation amount: ±10-30% of current value, clamped to valid ranges.
        """
        d = dna.to_dict()
        for param, (lo, hi, is_int) in _PARAM_RANGES.items():
            if self.rng.random() < self.mutation_rate:
                val = d[param]
                # ±10-30%
                pct = self.rng.uniform(0.10, 0.30)
                direction = self.rng.choice([-1, 1])
                delta = val * pct * direction
                # Minimum absolute delta so small values still move
                if abs(delta) < 0.01:
                    delta = 0.01 * direction
                new_val = val + delta
                new_val = max(lo, min(hi, new_val))
                if is_int:
                    new_val = int(round(new_val))
                d[param] = new_val

        # Normalize scoring weights so they sum ≈ 1.0
        w_sum = sum(d[k] for k in _WEIGHT_KEYS)
        if w_sum > 0:
            for k in _WEIGHT_KEYS:
                d[k] = round(d[k] / w_sum, 4)

        return StrategyDNA.from_dict(d)

    def crossover(self, dna1: StrategyDNA, dna2: StrategyDNA) -> StrategyDNA:
        """Combine two strategies by randomly picking parameters from each parent."""
        d1 = dna1.to_dict()
        d2 = dna2.to_dict()
        child = {}
        for key in d1:
            child[key] = d1[key] if self.rng.random() < 0.5 else d2[key]

        # Normalize weights
        w_sum = sum(child[k] for k in _WEIGHT_KEYS)
        if w_sum > 0:
            for k in _WEIGHT_KEYS:
                child[k] = round(child[k] / w_sum, 4)

        return StrategyDNA.from_dict(child)

    def evaluate(
        self,
        dna: StrategyDNA,
        data: Dict[str, Dict[str, list]],
        sample_size: int = 200,
    ) -> EvolutionResult:
        """Backtest a strategy on loaded data.

        For speed, evaluates on a random sample of ``sample_size`` stocks.
        Simplified but correct backtesting:
        - Every hold_days: score all stocks → pick top max_positions
        - T+1 open price entry
        - Check stop-loss / take-profit during holding period
        - Exit at end of hold period
        - Compute annual return, drawdown, win rate, Sharpe, Calmar

        Args:
            dna: Strategy parameters
            data: Stock data dict from load_data()
            sample_size: Max stocks to evaluate (for speed)

        Returns:
            EvolutionResult with all metrics
        """
        if not data:
            return EvolutionResult(
                dna=dna,
                annual_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                sharpe=0.0,
                calmar=0.0,
                total_trades=0,
                profit_factor=0.0,
                fitness=0.0,
            )

        # Sample stocks for speed
        codes = list(data.keys())
        if len(codes) > sample_size:
            codes = self.rng.sample(codes, sample_size)

        # Pre-compute indicators per stock (all 12 dimensions)
        indicators: Dict[str, Dict[str, Any]] = {}
        for code in codes:
            sd = data[code]
            closes = sd["close"]
            vols = sd["volume"]
            opens = sd["open"]
            highs_list = sd["high"]
            lows_list = sd["low"]

            rsi = compute_rsi(closes)
            r2, slope = compute_linear_regression(closes)
            vol_ratio = compute_volume_ratio(vols)

            # New v2 indicators
            macd_line, macd_signal, macd_hist = compute_macd(closes)
            bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(closes)
            kdj_k, kdj_d, kdj_j = compute_kdj(highs_list, lows_list, closes)
            obv = compute_obv_trend(closes, vols)
            ma_align = compute_ma_alignment(closes)

            indicators[code] = {
                "rsi": rsi,
                "r2": r2,
                "slope": slope,
                "volume_ratio": vol_ratio,
                "close": closes,
                "open": opens,
                "high": highs_list,
                "low": lows_list,
                "volume": vols,
                # v2 indicators
                "macd_line": macd_line,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "kdj_k": kdj_k,
                "kdj_d": kdj_d,
                "kdj_j": kdj_j,
                "obv_trend": obv,
                "ma_alignment": ma_align,
            }

        # Find common date range — use the first stock to determine day count
        first_code = codes[0]
        total_days = len(data[first_code]["close"])

        # Portfolio simulation
        initial_capital = 1_000_000.0
        capital = initial_capital
        portfolio_values = [capital]

        trades: List[float] = []  # list of trade returns (%)
        gross_profit = 0.0
        gross_loss = 0.0

        hold_days = max(2, dna.hold_days)  # A-share T+1: buy T+1, earliest sell T+2
        day = 30  # skip first 30 days for indicator warmup

        while day < total_days - hold_days - 1:
            # Score all stocks at this day
            scored: List[Tuple[str, float]] = []
            for code in codes:
                sd = data[code]
                if day >= len(sd["close"]):
                    continue
                ind = indicators[code]
                s = score_stock(
                    day,
                    ind,
                    dna,
                )
                if s >= dna.min_score:
                    scored.append((code, s))

            # Pick top max_positions
            scored.sort(key=lambda x: x[1], reverse=True)
            picks = scored[: dna.max_positions]

            if picks:
                # Allocate capital equally
                per_pos = capital / len(picks)

                for code, _score in picks:
                    sd = data[code]
                    entry_day = day + 1  # T+1

                    if entry_day >= len(sd["open"]):
                        continue

                    entry_price = sd["open"][entry_day]
                    if entry_price <= 0:
                        continue

                    # === A-SHARE LIMIT RULES ===
                    # Check if stock is at limit-up on entry day (can't buy)
                    if entry_day >= 1:
                        prev_close = sd["close"][entry_day - 1]
                        if prev_close > 0:
                            # Determine limit % based on board type
                            code_str = code.replace("_", ".")
                            if code_str.startswith("sh.688") or code_str.startswith("sz.3"):
                                limit_pct = 0.20  # 科创板/创业板 20%
                            else:
                                limit_pct = 0.10  # 主板 10%

                            # Skip if opening at limit-up (can't buy, sealed)
                            if entry_price >= prev_close * (1 + limit_pct - 0.005):
                                continue

                    shares = per_pos / entry_price
                    exit_price = entry_price  # default

                    # Hold period with SL/TP check
                    for d in range(entry_day, min(entry_day + hold_days, len(sd["close"]))):
                        low = sd["low"][d]
                        high = sd["high"][d]

                        # Check if at limit-down (can't sell)
                        if d >= 1:
                            pc = sd["close"][d - 1]
                            if pc > 0:
                                code_str = code.replace("_", ".")
                                if code_str.startswith("sh.688") or code_str.startswith("sz.3"):
                                    lim = 0.20
                                else:
                                    lim = 0.10
                                limit_down_price = pc * (1 - lim + 0.005)
                                # If close is at limit-down, can't sell
                                if sd["close"][d] <= limit_down_price and d < entry_day + hold_days - 1:
                                    continue  # skip this day, try to sell next day

                        # Stop loss
                        sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                        if low <= sl_price:
                            exit_price = sl_price
                            break

                        # Take profit
                        tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                        if high >= tp_price:
                            exit_price = tp_price
                            break

                        exit_price = sd["close"][d]

                    trade_return = (exit_price - entry_price) / entry_price * 100
                    trades.append(trade_return)

                    pnl = shares * (exit_price - entry_price)
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

                    capital += pnl

            portfolio_values.append(max(capital, 0.01))  # avoid zero

            day += hold_days

        # Compute metrics
        total_trades = len(trades)
        win_rate = 0.0
        if total_trades > 0:
            wins = sum(1 for t in trades if t > 0)
            win_rate = wins / total_trades * 100

        # Annual return
        if len(portfolio_values) > 1 and portfolio_values[0] > 0:
            total_return = portfolio_values[-1] / portfolio_values[0] - 1
            # Assume ~250 trading days per year
            trading_days_used = total_days - 30
            years = trading_days_used / 250 if trading_days_used > 0 else 1
            if total_return > -1:
                annual_return = ((1 + total_return) ** (1 / max(years, 0.01)) - 1) * 100
            else:
                annual_return = -100.0
        else:
            annual_return = 0.0

        # Max drawdown
        max_drawdown = 0.0
        peak = portfolio_values[0]
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, dd)

        # Sharpe ratio (daily returns → annualized)
        sharpe = 0.0
        if len(portfolio_values) > 2:
            daily_returns = [
                (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
                for i in range(1, len(portfolio_values))
                if portfolio_values[i - 1] > 0
            ]
            if daily_returns:
                mean_r = sum(daily_returns) / len(daily_returns)
                var_r = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
                std_r = math.sqrt(var_r) if var_r > 0 else 0.001
                # Annualize: each "period" is hold_days trading days
                periods_per_year = 250 / max(hold_days, 1)
                sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

        # Calmar ratio
        calmar = annual_return / max(max_drawdown, 1.0)

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

        fitness = compute_fitness(annual_return, max_drawdown, win_rate, sharpe, total_trades)

        return EvolutionResult(
            dna=dna,
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(win_rate, 4),
            sharpe=round(sharpe, 4),
            calmar=round(calmar, 4),
            total_trades=total_trades,
            profit_factor=round(profit_factor, 4),
            fitness=round(fitness, 4),
        )

    def run_generation(
        self,
        parents: List[StrategyDNA],
        data: Dict[str, Dict[str, list]],
    ) -> List[EvolutionResult]:
        """Run one generation of evolution.

        1. Generate mutations + crossovers from parents
        2. Evaluate all candidates
        3. Sort by fitness
        4. Return top ``elite_count`` results
        """
        candidates: List[StrategyDNA] = list(parents)

        while len(candidates) < self.population_size:
            parent = self.rng.choice(parents)
            if self.rng.random() < 0.7:
                # Mutation
                child = self.mutate(parent)
            else:
                # Crossover
                other = self.rng.choice(parents)
                child = self.crossover(parent, other)
                child = self.mutate(child)  # mutate after crossover
            candidates.append(child)

        results = [self.evaluate(dna, data) for dna in candidates]
        results.sort(key=lambda r: r.fitness, reverse=True)
        return results[: self.elite_count]

    def evolve(self, generations: int = 100, save_interval: int = 10) -> List[EvolutionResult]:
        """Main evolution loop.

        - Loads data once
        - Optionally resumes from saved results
        - Runs ``generations`` generations
        - Saves best results every ``save_interval`` gens
        - Prints progress each generation

        Returns:
            Final top results
        """
        print("=" * 60)
        print("🦀 FinClaw Auto Evolution Engine")
        print("=" * 60)

        t0 = time.time()
        print("Loading market data...", flush=True)
        data = self.load_data()
        elapsed = time.time() - t0
        print(f"Loaded {len(data)} stocks in {elapsed:.1f}s")

        if not data:
            print("ERROR: No data loaded. Check data_dir path.")
            return []

        # Try to resume from saved results
        parents = self._load_parents()
        start_gen = self._load_start_gen()
        if parents:
            print(f"Resuming from generation {start_gen} with {len(parents)} elite strategies")
        else:
            parents = [StrategyDNA()]  # default seed
            start_gen = 0
            print("Starting fresh with default strategy DNA")

        print(f"Population: {self.population_size} | Elite: {self.elite_count} | "
              f"Mutation rate: {self.mutation_rate}")
        print("-" * 60)

        best_results: List[EvolutionResult] = []

        for gen in range(start_gen, start_gen + generations):
            gen_t0 = time.time()
            results = self.run_generation(parents, data)
            gen_time = time.time() - gen_t0

            best = results[0]
            best_results = results

            print(
                f"Gen {gen:4d} | "
                f"fitness={best.fitness:8.2f} | "
                f"return={best.annual_return:7.2f}% | "
                f"dd={best.max_drawdown:5.2f}% | "
                f"wr={best.win_rate:5.1f}% | "
                f"sharpe={best.sharpe:5.2f} | "
                f"trades={best.total_trades:4d} | "
                f"{gen_time:.1f}s"
            )

            # Update parents for next generation
            parents = [r.dna for r in results]

            # Periodic save
            if (gen + 1) % save_interval == 0 or gen == start_gen + generations - 1:
                self.save_results(gen, results)

        total_time = time.time() - t0
        print("-" * 60)
        print(f"Evolution complete! {generations} generations in {total_time:.1f}s")
        if best_results:
            print(f"Best fitness: {best_results[0].fitness:.4f}")
            print(f"Best DNA: {best_results[0].dna.to_dict()}")
        print("=" * 60)

        return best_results

    def save_results(self, gen: int, best: List[EvolutionResult]) -> None:
        """Save best strategies to JSON for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        payload = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "results": [r.to_dict() for r in best],
        }
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # Also save a versioned copy
        versioned = os.path.join(self.results_dir, f"gen_{gen:04d}.json")
        with open(versioned, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load_best(self) -> Optional[StrategyDNA]:
        """Load the best known strategy from saved results."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return None
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", [])
        if not results:
            return None
        return StrategyDNA.from_dict(results[0]["dna"])

    def _load_parents(self) -> List[StrategyDNA]:
        """Load elite parents from previous run for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return []
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [StrategyDNA.from_dict(r["dna"]) for r in data.get("results", [])]
        except Exception:
            return []

    def _load_start_gen(self) -> int:
        """Get last completed generation for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return 0
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("generation", 0) + 1
        except Exception:
            return 0
