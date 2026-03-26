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

v3: Walk-Forward validation (70/30 split), deterministic stock sampling
    per generation, enhanced fitness with Sortino, consecutive loss penalty,
    and consistency bonus.
"""

from __future__ import annotations

print("Evolution Engine v4 -- Walk-Forward + Smart Evolution + 57-dim Factors")

import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, field, fields
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
    # Technical extended
    "w_atr",
    "w_adx",
    "w_roc",
    "w_williams_r",
    "w_cci",
    "w_mfi",
    "w_vwap",
    "w_donchian",
    "w_ichimoku",
    "w_elder_ray",
    # Rolling statistics
    "w_beta",
    "w_r_squared",
    "w_residual",
    "w_quantile_upper",
    "w_quantile_lower",
    "w_aroon",
    "w_price_volume_corr",
    # Fundamental factors (original)
    "w_pe",
    "w_pb",
    "w_roe",
    "w_revenue_growth",
    # Fundamental growth
    "w_revenue_yoy",
    "w_revenue_qoq",
    "w_profit_yoy",
    "w_profit_qoq",
    # Fundamental valuation
    "w_ps",
    "w_peg",
    # Fundamental quality
    "w_gross_margin",
    "w_debt_ratio",
    "w_cashflow",
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
    # Fundamental factors (default 0 = disabled until evolved)
    w_pe: float = 0.0             # PE valuation score
    w_pb: float = 0.0             # PB value score
    w_roe: float = 0.0            # Return on equity
    w_revenue_growth: float = 0.0 # Revenue growth rate

    # === Technical Extended ===
    w_atr: float = 0.0              # Average True Range (volatility)
    w_adx: float = 0.0              # Average Directional Index (trend strength)
    w_roc: float = 0.0              # Rate of Change
    w_williams_r: float = 0.0       # Williams %R
    w_cci: float = 0.0              # Commodity Channel Index
    w_mfi: float = 0.0              # Money Flow Index
    w_vwap: float = 0.0             # Volume Weighted Avg Price distance
    w_donchian: float = 0.0         # Donchian Channel breakout
    w_ichimoku: float = 0.0         # Ichimoku cloud position
    w_elder_ray: float = 0.0        # Elder Ray (bull/bear power)

    # === Rolling Statistics ===
    w_beta: float = 0.0             # Price regression slope
    w_r_squared: float = 0.0        # Trend linearity
    w_residual: float = 0.0         # Regression residual (mean reversion)
    w_quantile_upper: float = 0.0   # 80% quantile distance
    w_quantile_lower: float = 0.0   # 20% quantile distance
    w_aroon: float = 0.0            # Days since high/low
    w_price_volume_corr: float = 0.0 # Price-volume correlation

    # === Fundamental Growth ===
    w_revenue_yoy: float = 0.0      # Revenue YoY growth
    w_revenue_qoq: float = 0.0      # Revenue QoQ growth
    w_profit_yoy: float = 0.0       # Net profit YoY growth
    w_profit_qoq: float = 0.0       # Net profit QoQ growth

    # === Fundamental Valuation ===
    w_ps: float = 0.0               # Price-to-Sales
    w_peg: float = 0.0              # PEG ratio

    # === Fundamental Quality ===
    w_gross_margin: float = 0.0     # Gross margin
    w_debt_ratio: float = 0.0       # Debt-to-asset ratio
    w_cashflow: float = 0.0         # Operating cashflow quality

    # === Dynamic factor weights (from factor discovery) ===
    custom_weights: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Flatten custom_weights into top-level for serialization
        cw = d.pop("custom_weights", {})
        d.update(cw)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyDNA":
        valid = {f.name for f in fields(cls)}
        known = {k: v for k, v in d.items() if k in valid and k != "custom_weights"}
        # Any keys not in standard fields go into custom_weights
        extra = {k: v for k, v in d.items() if k not in valid}
        # Merge explicit custom_weights from dict if present
        if "custom_weights" in d and isinstance(d["custom_weights"], dict):
            extra.update(d["custom_weights"])
        known["custom_weights"] = extra
        return cls(**known)


# Valid ranges for each parameter — (min, max, is_int)
_PARAM_RANGES: Dict[str, Tuple[float, float, bool]] = {
    "min_score": (4, 8, True),  # min=4 prevents overfitting via loose threshold
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
    # Fundamental factor weights
    "w_pe": (0.0, 1.0, False),
    "w_pb": (0.0, 1.0, False),
    "w_roe": (0.0, 1.0, False),
    "w_revenue_growth": (0.0, 1.0, False),
    # Technical extended
    "w_atr": (0.0, 1.0, False),
    "w_adx": (0.0, 1.0, False),
    "w_roc": (0.0, 1.0, False),
    "w_williams_r": (0.0, 1.0, False),
    "w_cci": (0.0, 1.0, False),
    "w_mfi": (0.0, 1.0, False),
    "w_vwap": (0.0, 1.0, False),
    "w_donchian": (0.0, 1.0, False),
    "w_ichimoku": (0.0, 1.0, False),
    "w_elder_ray": (0.0, 1.0, False),
    # Rolling statistics
    "w_beta": (0.0, 1.0, False),
    "w_r_squared": (0.0, 1.0, False),
    "w_residual": (0.0, 1.0, False),
    "w_quantile_upper": (0.0, 1.0, False),
    "w_quantile_lower": (0.0, 1.0, False),
    "w_aroon": (0.0, 1.0, False),
    "w_price_volume_corr": (0.0, 1.0, False),
    # Fundamental growth
    "w_revenue_yoy": (0.0, 1.0, False),
    "w_revenue_qoq": (0.0, 1.0, False),
    "w_profit_yoy": (0.0, 1.0, False),
    "w_profit_qoq": (0.0, 1.0, False),
    # Fundamental valuation
    "w_ps": (0.0, 1.0, False),
    "w_peg": (0.0, 1.0, False),
    # Fundamental quality
    "w_gross_margin": (0.0, 1.0, False),
    "w_debt_ratio": (0.0, 1.0, False),
    "w_cashflow": (0.0, 1.0, False),
}


def get_all_weight_keys(dna: StrategyDNA) -> List[str]:
    """Return builtin weight keys + dynamic custom weight keys."""
    return _WEIGHT_KEYS + list(dna.custom_weights.keys())


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
    n = min(len(closes), len(volumes))
    trend = [float("nan")] * len(closes)
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

# ────────────────── Extended Technical Indicators ──────────────────


def compute_atr(
    highs: List[float], lows: List[float], closes: List[float], period: int = 14
) -> List[float]:
    """Average True Range. Returns ATR as % of close. NaN-padded."""
    n = len(closes)
    atr = [float("nan")] * n
    if n < period + 1:
        return atr
    trs: List[float] = [0.0]
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    # Seed ATR with SMA
    avg_tr = sum(trs[1:period + 1]) / period
    atr[period] = avg_tr / closes[period] * 100 if closes[period] > 0 else 0.0
    for i in range(period + 1, n):
        avg_tr = (avg_tr * (period - 1) + trs[i]) / period
        atr[i] = avg_tr / closes[i] * 100 if closes[i] > 0 else 0.0
    return atr


def compute_roc(closes: List[float], period: int = 10) -> List[float]:
    """Rate of Change: (close - close[n]) / close[n] * 100. NaN-padded."""
    n = len(closes)
    roc = [float("nan")] * n
    for i in range(period, n):
        if closes[i - period] > 0:
            roc[i] = (closes[i] - closes[i - period]) / closes[i - period] * 100
    return roc


def compute_williams_r(
    highs: List[float], lows: List[float], closes: List[float], period: int = 14
) -> List[float]:
    """Williams %R. Returns values in [-100, 0]. NaN-padded."""
    n = len(closes)
    wr = [float("nan")] * n
    if n < period:
        return wr
    for i in range(period - 1, n):
        hh = max(highs[i - period + 1:i + 1])
        ll = min(lows[i - period + 1:i + 1])
        if hh - ll > 0:
            wr[i] = (hh - closes[i]) / (hh - ll) * -100
        else:
            wr[i] = -50.0
    return wr


def compute_cci(closes: List[float], highs: List[float], lows: List[float], period: int = 20) -> List[float]:
    """Commodity Channel Index. NaN-padded."""
    n = len(closes)
    cci = [float("nan")] * n
    if n < period:
        return cci
    for i in range(period - 1, n):
        tp_list = [(highs[j] + lows[j] + closes[j]) / 3 for j in range(i - period + 1, i + 1)]
        tp_mean = sum(tp_list) / period
        md = sum(abs(tp - tp_mean) for tp in tp_list) / period
        if md > 0:
            cci[i] = (tp_list[-1] - tp_mean) / (0.015 * md)
        else:
            cci[i] = 0.0
    return cci


def compute_mfi(
    highs: List[float], lows: List[float], closes: List[float],
    volumes: List[float], period: int = 14,
) -> List[float]:
    """Money Flow Index (volume-weighted RSI). Returns [0, 100]. NaN-padded."""
    n = min(len(closes), len(volumes))
    mfi = [float("nan")] * len(closes)
    if n < period + 1:
        return mfi
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(n)]
    for i in range(period, n):
        pos_flow = 0.0
        neg_flow = 0.0
        for j in range(i - period + 1, i + 1):
            mf = tp[j] * volumes[j]
            if tp[j] > tp[j - 1]:
                pos_flow += mf
            elif tp[j] < tp[j - 1]:
                neg_flow += mf
        if neg_flow > 0:
            mr = pos_flow / neg_flow
            mfi[i] = 100 - 100 / (1 + mr)
        else:
            mfi[i] = 100.0
    return mfi


def compute_donchian_position(
    highs: List[float], lows: List[float], closes: List[float], period: int = 20
) -> List[float]:
    """Price position within Donchian channel [0=at low, 1=at high]. NaN-padded."""
    n = len(closes)
    pos = [float("nan")] * n
    if n < period:
        return pos
    for i in range(period - 1, n):
        hh = max(highs[i - period + 1:i + 1])
        ll = min(lows[i - period + 1:i + 1])
        rng = hh - ll
        if rng > 0:
            pos[i] = (closes[i] - ll) / rng
        else:
            pos[i] = 0.5
    return pos


def compute_aroon(closes: List[float], period: int = 25) -> List[float]:
    """Aroon oscillator: (days_since_high - days_since_low) / period. Returns [-1, 1]. NaN-padded."""
    n = len(closes)
    aroon = [float("nan")] * n
    if n < period:
        return aroon
    for i in range(period - 1, n):
        seg = closes[i - period + 1:i + 1]
        hi_idx = seg.index(max(seg))
        lo_idx = seg.index(min(seg))
        aroon_up = hi_idx / (period - 1) if period > 1 else 0.5
        aroon_down = lo_idx / (period - 1) if period > 1 else 0.5
        aroon[i] = aroon_up - aroon_down  # [-1, 1]
    return aroon


def compute_price_volume_corr(
    closes: List[float], volumes: List[float], window: int = 20
) -> List[float]:
    """Rolling Pearson correlation between price and volume. Returns [-1, 1]. NaN-padded."""
    n = min(len(closes), len(volumes))
    corr = [float("nan")] * len(closes)
    if n < window:
        return corr
    for i in range(window - 1, n):
        p = closes[i - window + 1:i + 1]
        v = volumes[i - window + 1:i + 1]
        mp = sum(p) / window
        mv = sum(v) / window
        cov = sum((p[j] - mp) * (v[j] - mv) for j in range(window)) / window
        sp = math.sqrt(sum((p[j] - mp) ** 2 for j in range(window)) / window)
        sv = math.sqrt(sum((v[j] - mv) ** 2 for j in range(window)) / window)
        if sp > 0 and sv > 0:
            corr[i] = max(-1.0, min(1.0, cov / (sp * sv)))
        else:
            corr[i] = 0.0
    return corr


# Import fundamental scoring functions
from src.evolution.fundamentals import (
    compute_pe_score as _compute_pe_score,
    compute_pb_score as _compute_pb_score,
    compute_roe_score as _compute_roe_score,
    compute_growth_score as _compute_growth_score,
    compute_revenue_yoy_score as _compute_revenue_yoy_score,
    compute_revenue_qoq_score as _compute_revenue_qoq_score,
    compute_profit_yoy_score as _compute_profit_yoy_score,
    compute_profit_qoq_score as _compute_profit_qoq_score,
    compute_ps_score as _compute_ps_score,
    compute_peg_score as _compute_peg_score,
    compute_gross_margin_score as _compute_gross_margin_score,
    compute_debt_ratio_score as _compute_debt_ratio_score,
    compute_cashflow_score as _compute_cashflow_score,
)

# Import market state filter (hard rule, not part of evolution)
from src.evolution.market_filter import MarketStateFilter


def score_stock(
    idx: int,
    indicators: Dict[str, Any],
    dna: StrategyDNA,
) -> float:
    """Score a stock at a given index using multi-dimensional DNA weights.

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

    # ──── Extended Technical Indicators (12-21) ────

    # Helper to safely read a pre-computed indicator at idx
    def _safe_read(key: str, default: float = 0.5) -> float:
        arr = indicators.get(key, None)
        if arr is None or idx >= len(arr):
            return default
        val = arr[idx]
        if isinstance(val, float) and math.isnan(val):
            return default
        return val

    # 12. ATR — lower volatility = safer, score inversely
    atr_val = _safe_read("atr_pct", 0.5)
    if atr_val != 0.5:
        # ATR as % of price: <1% very calm, >5% very volatile
        if atr_val < 1.0:
            atr_raw = 1.0
        elif atr_val < 2.0:
            atr_raw = 0.8
        elif atr_val < 3.0:
            atr_raw = 0.6
        elif atr_val < 5.0:
            atr_raw = 0.4
        else:
            atr_raw = 0.2
    else:
        atr_raw = 0.5

    # 13. ADX — stub (not computed, default neutral)
    adx_raw = 0.5

    # 14. ROC — positive momentum = good
    roc_val = _safe_read("roc", 0.5)
    if roc_val != 0.5:
        if roc_val > 10:
            roc_raw = 1.0
        elif roc_val > 5:
            roc_raw = 0.8
        elif roc_val > 0:
            roc_raw = 0.6
        elif roc_val > -5:
            roc_raw = 0.3
        else:
            roc_raw = 0.1
    else:
        roc_raw = 0.5

    # 15. Williams %R — oversold (<-80) = bullish, overbought (>-20) = bearish
    wr_val = _safe_read("williams_r", 0.5)
    if wr_val != 0.5:
        # %R ranges from -100 to 0
        if wr_val < -80:
            williams_raw = 1.0  # oversold = bullish
        elif wr_val < -50:
            williams_raw = 0.6
        elif wr_val < -20:
            williams_raw = 0.3
        else:
            williams_raw = 0.1  # overbought = bearish
    else:
        williams_raw = 0.5

    # 16. CCI — score based on position
    cci_val = _safe_read("cci", 0.5)
    if cci_val != 0.5:
        if cci_val < -200:
            cci_raw = 1.0   # deeply oversold
        elif cci_val < -100:
            cci_raw = 0.8
        elif cci_val < 0:
            cci_raw = 0.5
        elif cci_val < 100:
            cci_raw = 0.4
        elif cci_val < 200:
            cci_raw = 0.2
        else:
            cci_raw = 0.1
    else:
        cci_raw = 0.5

    # 17. MFI — similar to RSI but volume-weighted
    mfi_val = _safe_read("mfi", 0.5)
    if mfi_val != 0.5:
        if mfi_val < 20:
            mfi_raw = 1.0   # oversold
        elif mfi_val < 40:
            mfi_raw = 0.7
        elif mfi_val < 60:
            mfi_raw = 0.5
        elif mfi_val < 80:
            mfi_raw = 0.3
        else:
            mfi_raw = 0.1   # overbought
    else:
        mfi_raw = 0.5

    # 18. VWAP — stub (needs intraday data), neutral
    vwap_raw = 0.5

    # 19. Donchian — position within channel
    donchian_val = _safe_read("donchian_pos", 0.5)
    if donchian_val != 0.5:
        # Near bottom of channel = bullish (buy low)
        donchian_raw = max(0.0, min(1.0, 1.0 - donchian_val))
    else:
        donchian_raw = 0.5

    # 20. Ichimoku — stub (complex, skip for now), neutral
    ichimoku_raw = 0.5

    # 21. Elder Ray — stub, neutral
    elder_ray_raw = 0.5

    # ──── Rolling Statistics (22-28) ────

    # 22. Beta (slope magnitude as trend strength)
    beta_raw = max(0.0, min(1.0, abs(slope[idx]) / 3.0))

    # 23. R² (trend linearity, already available)
    r2_raw = r2[idx]

    # 24. Residual (mean reversion: if price below regression line = buy signal)
    # Use regression slope to estimate expected vs actual
    residual_raw = 0.5  # default neutral
    if lookback >= 20 and closes[idx] > 0:
        seg = closes[idx - 19:idx + 1]
        if len(seg) == 20:
            mean_y = sum(seg) / 20
            mean_x = 9.5
            ss_xy = sum((j - mean_x) * (seg[j] - mean_y) for j in range(20))
            ss_xx = sum((j - mean_x) ** 2 for j in range(20))
            if ss_xx > 0:
                s = ss_xy / ss_xx
                intercept = mean_y - s * mean_x
                expected = s * 19 + intercept
                residual = (closes[idx] - expected) / closes[idx] * 100
                # Below expected = undervalued (bullish)
                if residual < -3:
                    residual_raw = 1.0
                elif residual < -1:
                    residual_raw = 0.7
                elif residual < 1:
                    residual_raw = 0.5
                elif residual < 3:
                    residual_raw = 0.3
                else:
                    residual_raw = 0.1

    # 25-26. Quantile distance
    quantile_upper_raw = 0.5
    quantile_lower_raw = 0.5
    if lookback >= 20:
        seg = sorted(closes[idx - 19:idx + 1])
        if len(seg) == 20:
            q80 = seg[int(20 * 0.8)]
            q20 = seg[int(20 * 0.2)]
            price = closes[idx]
            if q80 > 0:
                # Distance above 80th quantile: higher = overbought
                quantile_upper_raw = max(0.0, min(1.0, 1.0 - (price - q20) / (q80 - q20))) if q80 != q20 else 0.5
            if q20 > 0:
                quantile_lower_raw = max(0.0, min(1.0, (price - q20) / (q80 - q20))) if q80 != q20 else 0.5

    # 27. Aroon oscillator
    aroon_val = _safe_read("aroon", 0.5)
    if aroon_val != 0.5:
        # aroon range [-1, 1]: positive = recent high-dominant, negative = recent low-dominant
        aroon_raw = max(0.0, min(1.0, (aroon_val + 1.0) / 2.0))
    else:
        aroon_raw = 0.5

    # 28. Price-volume correlation
    pv_corr_val = _safe_read("pv_corr", 0.5)
    if pv_corr_val != 0.5:
        # Positive correlation + uptrend = healthy; negative = divergence
        if slope[idx] > 0:
            pv_corr_raw = max(0.0, min(1.0, (pv_corr_val + 1.0) / 2.0))
        else:
            pv_corr_raw = max(0.0, min(1.0, (1.0 - pv_corr_val) / 2.0))
    else:
        pv_corr_raw = 0.5

    # ──── Fundamental Scores (29-42) ────

    fund = indicators.get("fundamentals", {})

    # Original 4 fundamental factors
    pe_val = fund.get("pe", 0)
    pe_raw = _compute_pe_score(pe_val) if pe_val > 0 else 0.5

    pb_val = fund.get("pb", 0)
    pb_raw = _compute_pb_score(pb_val) if pb_val > 0 else 0.5

    roe_val = fund.get("roe", 0)
    roe_raw = _compute_roe_score(roe_val) if roe_val > 0 else 0.5

    rev_growth = fund.get("revenue_growth", 0)
    growth_raw = _compute_growth_score(rev_growth) if rev_growth != 0 else 0.5

    # New fundamental growth factors
    revenue_yoy_val = fund.get("revenue_yoy", 0)
    revenue_yoy_raw = _compute_revenue_yoy_score(revenue_yoy_val) if revenue_yoy_val != 0 else 0.5

    revenue_qoq_val = fund.get("revenue_qoq", 0)
    revenue_qoq_raw = _compute_revenue_qoq_score(revenue_qoq_val) if revenue_qoq_val != 0 else 0.5

    profit_yoy_val = fund.get("profit_yoy", 0)
    profit_yoy_raw = _compute_profit_yoy_score(profit_yoy_val) if profit_yoy_val != 0 else 0.5

    profit_qoq_val = fund.get("profit_qoq", 0)
    profit_qoq_raw = _compute_profit_qoq_score(profit_qoq_val) if profit_qoq_val != 0 else 0.5

    # Valuation factors
    ps_val = fund.get("ps", 0)
    ps_raw = _compute_ps_score(ps_val) if ps_val > 0 else 0.5

    peg_pe = fund.get("pe", 0)
    peg_growth = fund.get("revenue_growth", 0)
    peg_raw = _compute_peg_score(peg_pe, peg_growth) if peg_pe > 0 and peg_growth > 0 else 0.5

    # Quality factors
    gm_val = fund.get("gross_margin", 0)
    gross_margin_raw = _compute_gross_margin_score(gm_val) if gm_val > 0 else 0.5

    dr_val = fund.get("debt_ratio", 0)
    debt_ratio_raw = _compute_debt_ratio_score(dr_val) if dr_val > 0 else 0.5

    cf_val = fund.get("ocf_to_profit", 0)
    cashflow_raw = _compute_cashflow_score(cf_val) if cf_val != 0 else 0.5

    # ──── Weighted sum with all dimensions ────
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
        # Technical extended
        + dna.w_atr * atr_raw
        + dna.w_adx * adx_raw
        + dna.w_roc * roc_raw
        + dna.w_williams_r * williams_raw
        + dna.w_cci * cci_raw
        + dna.w_mfi * mfi_raw
        + dna.w_vwap * vwap_raw
        + dna.w_donchian * donchian_raw
        + dna.w_ichimoku * ichimoku_raw
        + dna.w_elder_ray * elder_ray_raw
        # Rolling statistics
        + dna.w_beta * beta_raw
        + dna.w_r_squared * r2_raw
        + dna.w_residual * residual_raw
        + dna.w_quantile_upper * quantile_upper_raw
        + dna.w_quantile_lower * quantile_lower_raw
        + dna.w_aroon * aroon_raw
        + dna.w_price_volume_corr * pv_corr_raw
        # Fundamental (original)
        + dna.w_pe * pe_raw
        + dna.w_pb * pb_raw
        + dna.w_roe * roe_raw
        + dna.w_revenue_growth * growth_raw
        # Fundamental growth
        + dna.w_revenue_yoy * revenue_yoy_raw
        + dna.w_revenue_qoq * revenue_qoq_raw
        + dna.w_profit_yoy * profit_yoy_raw
        + dna.w_profit_qoq * profit_qoq_raw
        # Fundamental valuation
        + dna.w_ps * ps_raw
        + dna.w_peg * peg_raw
        # Fundamental quality
        + dna.w_gross_margin * gross_margin_raw
        + dna.w_debt_ratio * debt_ratio_raw
        + dna.w_cashflow * cashflow_raw
    )

    total_weight = sum(getattr(dna, k) for k in _WEIGHT_KEYS)

    # ──── Dynamic factors (from custom_weights via factor discovery) ────
    if hasattr(dna, 'custom_weights') and dna.custom_weights:
        factor_fns = indicators.get("_factor_fns", {})
        closes_raw = indicators.get("close", [])
        highs_raw = indicators.get("high", [])
        lows_raw = indicators.get("low", [])
        vols_raw = indicators.get("volume", [])

        for fname, w in dna.custom_weights.items():
            if w < 0.0001 or fname not in factor_fns:
                continue
            try:
                factor_raw = factor_fns[fname](closes_raw, highs_raw, lows_raw, vols_raw, idx)
                factor_raw = max(0.0, min(1.0, float(factor_raw)))
            except Exception:
                factor_raw = 0.5  # neutral on error
            raw += w * factor_raw
            total_weight += w

    if total_weight > 0:
        raw /= total_weight

    return raw * 10.0


def compute_fitness(
    annual_return: float,
    max_drawdown: float,
    win_rate: float,
    sharpe: float,
    total_trades: int = 200,
    sortino: Optional[float] = None,
    max_consec_losses: int = 0,
    monthly_returns: Optional[List[float]] = None,
    positions_used: int = 1,
    max_positions: int = 1,
    avg_turnover: float = 0.0,
) -> float:
    """Compute composite fitness score.

    fitness = annual_return * sqrt(win_rate) / max(max_drawdown, 5.0) * sharpe_bonus * trade_penalty
              * sortino_bonus * consec_loss_penalty * consistency_bonus * diversification_bonus
              * turnover_penalty

    Rewards: high return, high win rate, low drawdown, good Sharpe, enough trades,
             Sortino > Sharpe, consistent monthly returns, diversified holdings.
    Penalizes: fewer than 30 trades, long consecutive loss streaks, very high turnover.
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

    base_fitness = annual_return * win_factor / dd_denom * sharpe_bonus * trade_penalty

    # Sortino-like bonus: if sortino > sharpe, extra 10%
    sortino_bonus = 1.0
    if sortino is not None and sortino > sharpe:
        sortino_bonus = 1.1

    # Max consecutive losses penalty
    consec_loss_penalty = 1.0
    if max_consec_losses > 15:
        consec_loss_penalty = 0.4
    elif max_consec_losses > 10:
        consec_loss_penalty = 0.7

    # Consistency bonus: coefficient of variation of monthly returns
    consistency_bonus = 1.0
    if monthly_returns is not None and len(monthly_returns) >= 3:
        mean_mr = sum(monthly_returns) / len(monthly_returns)
        if mean_mr != 0:
            var_mr = sum((r - mean_mr) ** 2 for r in monthly_returns) / len(monthly_returns)
            std_mr = math.sqrt(var_mr)
            cv = abs(std_mr / mean_mr)
            if cv < 1.0:
                consistency_bonus = 1.2  # consistent returns

    # Diversification bonus: reward strategies that actually hold multiple
    # positions simultaneously (not just max_positions parameter, but real usage)
    diversification_bonus = 1.0
    if positions_used >= 2:
        if max_positions >= 5 and positions_used >= 3:
            diversification_bonus = 1.25  # 25% bonus for wide diversification
        elif max_positions >= 3 and positions_used >= 2:
            diversification_bonus = 1.15  # 15% bonus for moderate diversification

    # Turnover penalty: penalize strategies that churn their portfolio
    turnover_penalty = 1.0
    if avg_turnover > 0.8:
        turnover_penalty = 0.85  # very high turnover
    elif avg_turnover > 0.5:
        turnover_penalty = 0.95  # moderately high turnover

    return (base_fitness * sortino_bonus * consec_loss_penalty
            * consistency_bonus * diversification_bonus * turnover_penalty)


def filter_stock_pool(
    data: Dict[str, Dict[str, list]],
    min_daily_amount: float = 20_000_000.0,
    min_price: float = 5.0,
    max_stocks: int = 500,
) -> Dict[str, Dict[str, list]]:
    """Filter stock pool by quality metrics.

    Criteria:
    - Exclude ST / *ST stocks (delisting risk)
    - Exclude bank stocks (low volatility, drag on evolution)
    - Exclude stocks with price < min_price
    - Average daily turnover > min_daily_amount
    - Stocks with recent limit-up get priority bonus
    - Returns at most max_stocks best-quality stocks

    Args:
        data: Raw stock data dict (code -> {date, open, high, low, close, volume})
        min_daily_amount: Minimum average daily turnover in CNY
        min_price: Minimum stock price
        max_stocks: Maximum number of stocks to keep

    Returns:
        Filtered data dict
    """
    # Bank stock codes (major A-share banks — low volatility, not useful for evolution)
    _BANK_CODES = {
        "sh_601398",  # 工商银行
        "sh_601288",  # 农业银行
        "sh_601988",  # 中国银行
        "sh_601939",  # 建设银行
        "sh_601328",  # 交通银行
        "sh_600036",  # 招商银行
        "sh_601166",  # 兴业银行
        "sh_600016",  # 民生银行
        "sh_600000",  # 浦发银行
        "sh_601818",  # 光大银行
        "sh_600015",  # 华夏银行
        "sh_601998",  # 中信银行
        "sh_600919",  # 江苏银行
        "sh_601009",  # 南京银行
        "sh_601169",  # 北京银行
        "sz_000001",  # 平安银行
        "sz_002142",  # 宁波银行
        "sh_601838",  # 成都银行
        "sh_600926",  # 杭州银行
        "sh_601077",  # 渝农商行
        "sh_600908",  # 无锡银行
        "sz_002839",  # 张家港行
        "sz_002936",  # 郑州银行
        "sz_002948",  # 青岛银行
        "sh_601528",  # 瑞丰银行
        "sh_601860",  # 紫金银行
        "sz_002807",  # 江阴银行
        "sz_002966",  # 苏州银行
    }

    scored_codes: List[Tuple[str, float]] = []

    for code, sd in data.items():
        closes = sd["close"]
        volumes = sd["volume"]

        if not closes:
            continue

        # --- Exclusion filters ---

        # Skip bank stocks
        if code in _BANK_CODES:
            continue

        # Skip ST stocks — they have "ST" in the data or erratic price patterns
        # ST stocks typically have 5% daily limit instead of 10%
        # Heuristic: if max daily change in last 60 days never exceeds 5.5%, likely ST
        recent_n = min(60, len(closes))
        if recent_n > 5:
            max_daily_change = 0.0
            for i in range(len(closes) - recent_n + 1, len(closes)):
                if closes[i - 1] > 0:
                    change = abs(closes[i] - closes[i - 1]) / closes[i - 1]
                    max_daily_change = max(max_daily_change, change)
            # ST stocks have 5% limit; normal stocks have 10%+
            # If max change in 60 days is under 5.5%, very likely ST
            if max_daily_change < 0.055 and max_daily_change > 0:
                continue

        # Last close must be > min_price
        last_close = closes[-1]
        if last_close < min_price:
            continue

        # --- Quality scoring ---

        # Average daily turnover (volume * close as proxy for amount)
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
                # Approximate limit-up: >=9.5% for main board, >=19% for ChiNext/STAR
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
        market: str = "cn",
        walk_forward: bool = True,
        wf_config: Optional[Any] = None,
    ):
        self.data_dir = data_dir
        self.population_size = population_size
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.results_dir = results_dir
        self.market = market
        self.rng = random.Random(seed)
        os.makedirs(results_dir, exist_ok=True)

        # Walk-forward validation (default ON)
        self.walk_forward = walk_forward
        self._wf_validator = None
        if walk_forward:
            from src.evolution.walk_forward import WalkForwardValidator
            self._wf_validator = WalkForwardValidator(wf_config)

        # Initialize crypto backtest engine if needed
        self._crypto_engine = None
        if market == "crypto":
            from src.evolution.crypto_backtest import CryptoBacktestEngine
            self._crypto_engine = CryptoBacktestEngine()

    def load_data(
        self, quality_filter: bool = True, max_stocks: int = 500
    ) -> Dict[str, Dict[str, list]]:
        """Load stock CSV data into memory.

        Returns dict: code -> {date, open, high, low, close, volume}
        Only loads stocks with enough data (>= 60 trading days).

        Uses UnifiedDataLoader for CSV loading with built-in data validation
        and cleaning (NaN removal, negative price removal, date sorting).

        When quality_filter=True, applies:
        - Average daily turnover > 20M CNY (or volume*close proxy)
        - Last close > 5 CNY
        - Stocks with recent limit-up (涨停) get priority
        - Max ``max_stocks`` best-quality stocks retained
        """
        from src.evolution.data_loader import UnifiedDataLoader, validate_data

        loader = UnifiedDataLoader()
        load_market = "crypto" if self.market == "crypto" else "cn"
        data = loader.load_csv_dir(self.data_dir, market=load_market, min_days=60, clean=True)

        # Run data quality validation and print summary
        if data:
            report = validate_data(data)
            print(f"  [data quality] {report.valid_stocks}/{report.total_stocks} stocks valid, "
                  f"avg {report.avg_trading_days:.0f} trading days")
            if report.stocks_with_gaps > 0:
                print(f"  [data quality] {report.stocks_with_gaps} stocks have date gaps")
            if report.stocks_with_bad_data > 0:
                print(f"  [data quality] {report.stocks_with_bad_data} stocks have data issues")
            for w in report.warnings[:5]:
                print(f"  [data quality] [{w.level}] {w.stock}: {w.message}")
            if len(report.warnings) > 5:
                print(f"  [data quality] ... and {len(report.warnings) - 5} more warnings")

        if quality_filter and self.market != "crypto" and len(data) > max_stocks:
            data = filter_stock_pool(data, max_stocks=max_stocks)
            # NOTE: Sector-based and fundamental quality filtering (e.g., min ROE,
            # max PE, sector rotation) can be configured via finclaw-pro config.
            # The public framework supports weight-based scoring only.

        return data

    def mutate(self, dna: StrategyDNA) -> StrategyDNA:
        """Create a mutated copy of a strategy DNA.

        Each parameter has ``mutation_rate`` chance of being modified.
        Mutation amount: ±10-30% of current value, clamped to valid ranges.
        """
        d = dna.to_dict()

        # Extract custom weight keys (they were flattened into d by to_dict)
        custom_keys = list(dna.custom_weights.keys())
        # Remove them from d so they don't interfere with _PARAM_RANGES loop
        custom_vals = {k: d.pop(k, 0.0) for k in custom_keys}

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

        # Mutate custom weights with the same mutation rate
        for k in custom_keys:
            if self.rng.random() < self.mutation_rate:
                val = custom_vals[k]
                pct = self.rng.uniform(0.10, 0.30)
                direction = self.rng.choice([-1, 1])
                delta = val * pct * direction
                if abs(delta) < 0.01:
                    delta = 0.01 * direction
                custom_vals[k] = max(0.0, min(1.0, val + delta))

        # Normalize ALL weights together (builtin + custom) to sum ≈ 1.0
        w_sum = sum(d[k] for k in _WEIGHT_KEYS) + sum(custom_vals.values())
        if w_sum > 0:
            for k in _WEIGHT_KEYS:
                d[k] = round(d[k] / w_sum, 4)
            for k in custom_keys:
                custom_vals[k] = round(custom_vals[k] / w_sum, 4)

        # Put custom weights back into the dict for from_dict
        d.update(custom_vals)
        return StrategyDNA.from_dict(d)

    def crossover(self, dna1: StrategyDNA, dna2: StrategyDNA, bias: float = 0.5) -> StrategyDNA:
        """Combine two strategies by randomly picking parameters from each parent.

        Args:
            dna1: First parent DNA.
            dna2: Second parent DNA.
            bias: Probability of choosing dna1's gene (0.0-1.0, default 0.5).
                  When bias > 0.5, dna1's parameters are preferred.
        """
        d1 = dna1.to_dict()
        d2 = dna2.to_dict()

        # Get union of custom weight keys from both parents
        custom_keys_1 = set(dna1.custom_weights.keys())
        custom_keys_2 = set(dna2.custom_weights.keys())
        all_custom_keys = custom_keys_1 | custom_keys_2

        # Remove custom keys from d1/d2 (they were flattened by to_dict)
        cw1 = {k: d1.pop(k, 0.0) for k in all_custom_keys}
        cw2 = {k: d2.pop(k, 0.0) for k in all_custom_keys}

        child = {}
        for key in d1:
            child[key] = d1[key] if self.rng.random() < bias else d2.get(key, d1[key])

        # Merge custom weights from both parents (union of keys)
        child_custom = {}
        for k in all_custom_keys:
            child_custom[k] = cw1[k] if self.rng.random() < bias else cw2[k]

        # Normalize ALL weights together (builtin + custom)
        w_sum = sum(child[k] for k in _WEIGHT_KEYS) + sum(child_custom.values())
        if w_sum > 0:
            for k in _WEIGHT_KEYS:
                child[k] = round(child[k] / w_sum, 4)
            for k in all_custom_keys:
                child_custom[k] = round(child_custom[k] / w_sum, 4)

        # Put custom weights back into child dict for from_dict
        child.update(child_custom)
        return StrategyDNA.from_dict(child)

    def evaluate(
        self,
        dna: StrategyDNA,
        data: Dict[str, Dict[str, list]],
        sample_size: int = 200,
        gen_seed: int = 0,
    ) -> EvolutionResult:
        """Backtest a strategy on loaded data with walk-forward validation.

        For speed, evaluates on a deterministic sample of ``sample_size`` stocks
        (seeded by ``gen_seed`` so same generation always picks same stocks).

        Walk-forward: splits each stock's data into train (first 70%) and
        validation (last 30%).  Final fitness weights validation 60%, train 40%.

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
            gen_seed: Deterministic seed for stock sampling (generation number)

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

        # Load dynamic factor registry (cached on self)
        if not hasattr(self, '_factor_registry'):
            try:
                from src.evolution.factor_discovery import FactorRegistry, create_seed_factors
                create_seed_factors("factors")
                self._factor_registry = FactorRegistry("factors")
                self._factor_registry.load_all()
                factor_names = self._factor_registry.list_factors()
                if factor_names:
                    print(f"  [factors] loaded {len(factor_names)} dynamic factors: {factor_names}")
            except Exception as e:
                print(f"  [factors] skipped: {e}")
                self._factor_registry = None

        # Pre-compute active factor count for logging (once per evaluate call)
        _active_factor_count = None
        _total_factor_count = None
        if self._factor_registry and self._factor_registry.factors:
            _total_factor_count = len(self._factor_registry.list_factors())
            if hasattr(dna, 'custom_weights') and dna.custom_weights:
                _active_factor_count = sum(
                    1 for fname, w in dna.custom_weights.items()
                    if w >= 0.001 and fname in self._factor_registry.factors
                )
                if _active_factor_count < _total_factor_count:
                    print(f"  [factors] speedup: {_active_factor_count}/{_total_factor_count} factors active (skipping {_total_factor_count - _active_factor_count} near-zero)")

        # Deterministic sampling: use gen_seed so same generation always
        # picks the same stocks, eliminating sampling noise.
        codes = list(data.keys())
        if len(codes) > sample_size:
            sample_rng = random.Random(gen_seed)
            codes = sample_rng.sample(codes, sample_size)

        # Pre-compute indicators per stock (all 12 dimensions)
        indicators: Dict[str, Dict[str, Any]] = {}
        for code in codes:
            sd = data[code]
            closes = sd["close"]
            vols = sd["volume"]
            opens = sd["open"]
            highs_list = sd["high"]
            lows_list = sd["low"]
            
            # Ensure all lists have same length
            min_len = min(len(closes), len(vols), len(opens), len(highs_list), len(lows_list))
            closes = closes[:min_len]
            vols = vols[:min_len]
            opens = opens[:min_len]
            highs_list = highs_list[:min_len]
            lows_list = lows_list[:min_len]

            rsi = compute_rsi(closes)
            r2, slope = compute_linear_regression(closes)
            vol_ratio = compute_volume_ratio(vols)

            # New v2 indicators
            macd_line, macd_signal, macd_hist = compute_macd(closes)
            bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(closes)
            kdj_k, kdj_d, kdj_j = compute_kdj(highs_list, lows_list, closes)
            obv = compute_obv_trend(closes, vols)
            ma_align = compute_ma_alignment(closes)

            # Extended technical indicators (v3)
            atr_pct = compute_atr(highs_list, lows_list, closes)
            roc = compute_roc(closes)
            williams_r = compute_williams_r(highs_list, lows_list, closes)
            cci = compute_cci(closes, highs_list, lows_list)
            mfi = compute_mfi(highs_list, lows_list, closes, vols)
            donchian_pos = compute_donchian_position(highs_list, lows_list, closes)
            aroon = compute_aroon(closes)
            pv_corr = compute_price_volume_corr(closes, vols)

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
                # v3 extended indicators
                "atr_pct": atr_pct,
                "roc": roc,
                "williams_r": williams_r,
                "cci": cci,
                "mfi": mfi,
                "donchian_pos": donchian_pos,
                "aroon": aroon,
                "pv_corr": pv_corr,
            }

            # Store dynamic factor compute functions for on-the-fly scoring
            # Optimization: only include factors with non-trivial weights in DNA
            # If DNA has 196 custom weights but only 30 are >= 0.001, we skip 166
            if self._factor_registry and self._factor_registry.factors:
                if hasattr(dna, 'custom_weights') and dna.custom_weights:
                    # Pre-filter: only compute factors that the DNA actually uses
                    active_factors = {}
                    for fname, w in dna.custom_weights.items():
                        if w >= 0.001 and fname in self._factor_registry.factors:
                            active_factors[fname] = self._factor_registry.factors[fname].compute_fn
                    indicators[code]["_factor_fns"] = active_factors
                else:
                    # No custom weights in DNA, store all (fallback)
                    indicators[code]["_factor_fns"] = {
                        fname: self._factor_registry.factors[fname].compute_fn
                        for fname in self._factor_registry.list_factors()
                    }

        # Load fundamental data (once per session, cached)
        if not hasattr(self, '_fund_data_cache'):
            self._fund_data_cache = {}
            if not os.environ.get("FINCLAW_SKIP_FUNDAMENTALS"):
                try:
                    from src.evolution.fundamentals import fetch_fundamentals_baostock
                    self._fund_data_cache = fetch_fundamentals_baostock(codes)
                except Exception as e:
                    print(f"  [fundamentals] skipped: {e}")
            else:
                print("  [fundamentals] skipped (FINCLAW_SKIP_FUNDAMENTALS=1)")
        fund_data = self._fund_data_cache

        # Add fundamentals to indicators dict for each stock
        for code in codes:
            indicators[code]["fundamentals"] = fund_data.get(code, {})

        # Find common date range — use the first stock to determine day count
        first_code = codes[0]
        total_days = len(data[first_code]["close"])

        # ── Walk-Forward Split ──
        # Train on first 70%, validate on last 30%
        warmup = 30  # indicator warmup days
        train_end = warmup + int((total_days - warmup) * 0.7)
        val_start = train_end
        val_end = total_days

        hold_days = max(2, dna.hold_days)  # A-share T+1: buy T+1, earliest sell T+2

        # ── Choose backtest engine ──
        if self.market == "crypto" and self._crypto_engine is not None:
            # Use crypto backtest engine — no T+1, supports shorts/leverage
            def _run_backtest_dispatch(day_start: int, day_end: int):
                return self._crypto_engine.run_backtest(
                    dna, data, indicators, codes, day_start, day_end
                )
        else:
            _run_backtest_dispatch = None  # use inline A-share backtest below

        def _run_backtest(day_start: int, day_end: int) -> Tuple[
            float, float, float, float, float, int, float, float, int, List[float], int, float
        ]:
            """Run backtest on a date range. Returns (annual_return, max_drawdown,
            win_rate, sharpe, calmar, total_trades, profit_factor, sortino,
            max_consec_losses, monthly_returns, max_concurrent_positions, avg_turnover)."""
            initial_capital = 1_000_000.0
            bt_capital = initial_capital
            bt_portfolio_values = [bt_capital]

            bt_trades: List[float] = []
            bt_gross_profit = 0.0
            bt_gross_loss = 0.0

            # Track monthly returns for consistency bonus
            bt_monthly_returns: List[float] = []
            month_start_capital = bt_capital
            last_month_day = day_start
            approx_month_days = 21  # ~21 trading days per month

            # Track max concurrent positions for diversification scoring
            bt_max_concurrent = 0

            # Track turnover: how much the portfolio changes each rebalancing
            bt_turnover_ratios: List[float] = []
            bt_prev_picks: set = set()

            # Market state filter (hard rule, always applied, not evolved)
            bt_market_filter = MarketStateFilter()

            day = day_start

            while day < day_end - hold_days - 1:
                # Monthly return tracking
                if day - last_month_day >= approx_month_days:
                    if month_start_capital > 0:
                        mr = (bt_capital - month_start_capital) / month_start_capital * 100
                        bt_monthly_returns.append(mr)
                    month_start_capital = bt_capital
                    last_month_day = day

                # Score all stocks at this day
                scored: List[Tuple[str, float]] = []
                for code in codes:
                    sd = data[code]
                    if day >= len(sd["close"]):
                        continue
                    ind = indicators[code]
                    s = score_stock(day, ind, dna)
                    if s >= dna.min_score:
                        scored.append((code, s))

                # Apply market state filter (hard rule, not evolved)
                if bt_market_filter is not None and scored:
                    mkt_state = bt_market_filter.compute_market_state(
                        data, indicators, codes, day,
                    )
                    adjusted_scored = []
                    for code, s in scored:
                        ind = indicators[code]
                        sd = data[code]
                        has_bottom = MarketStateFilter.check_bottom_signals(
                            ind,
                            sd["close"], sd["high"], sd["low"], sd["volume"],
                            day,
                        )
                        adj_s = bt_market_filter.adjust_score(s, mkt_state, has_bottom)
                        if adj_s >= dna.min_score:
                            adjusted_scored.append((code, adj_s))
                    scored = adjusted_scored

                # ── Hard Filter: Reject Chronic Underperformers ──
                # This is a permanent safety rule, NOT subject to evolution.
                # Prevents buying stocks in structural decline (dying industries).
                if scored:
                    filtered_scored = []
                    for code, s in scored:
                        closes_arr = data[code]["close"]
                        if day >= 60:
                            peak_60d = max(closes_arr[day - 59:day + 1])
                            current = closes_arr[day]
                            if peak_60d > 0:
                                drawdown_from_peak = (peak_60d - current) / peak_60d
                                # Hard reject: >30% below 60-day high
                                if drawdown_from_peak > 0.30:
                                    continue
                                # Soft penalty: 15-30% below 60-day high, reduce score by 30%
                                if drawdown_from_peak > 0.15:
                                    s = s * 0.70
                                    if s < dna.min_score:
                                        continue
                        filtered_scored.append((code, s))
                    scored = filtered_scored

                # Pick top max_positions
                scored.sort(key=lambda x: x[1], reverse=True)
                picks = scored[: dna.max_positions]

                # Track turnover: how many positions changed from previous period
                current_pick_codes = {code for code, _ in picks}
                if bt_prev_picks:  # Skip first period (no previous positions)
                    # Count codes that are new or removed
                    changes = len(bt_prev_picks.symmetric_difference(current_pick_codes))
                    max_pos = max(dna.max_positions, 1)
                    period_turnover = changes / max_pos
                    bt_turnover_ratios.append(period_turnover)
                bt_prev_picks = current_pick_codes

                if picks:
                    per_pos = bt_capital / len(picks)
                    positions_this_period = 0

                    for code, _score in picks:
                        sd = data[code]
                        entry_day = day + 1  # T+1

                        if entry_day >= len(sd["open"]):
                            continue

                        entry_price = sd["open"][entry_day]
                        if entry_price <= 0:
                            continue

                        # === A-SHARE LIMIT RULES ===
                        if entry_day >= 1:
                            prev_close = sd["close"][entry_day - 1]
                            if prev_close > 0:
                                code_str = code.replace("_", ".")
                                if code_str.startswith("sh.688") or code_str.startswith("sz.3"):
                                    limit_pct = 0.20
                                else:
                                    limit_pct = 0.10
                                if entry_price >= prev_close * (1 + limit_pct - 0.005):
                                    continue

                        # === DYNAMIC SLIPPAGE based on volume ===
                        # Compute avg daily volume over recent 20 days
                        vols = sd["volume"]
                        vol_lookback = min(20, entry_day)
                        if vol_lookback > 0:
                            avg_vol = sum(vols[entry_day - vol_lookback:entry_day]) / vol_lookback
                        else:
                            avg_vol = vols[entry_day] if entry_day < len(vols) else 0
                        # Volume-based slippage tiers (shares/day)
                        if avg_vol < 5_000_000:
                            slippage_pct = 0.0015  # 0.15% for low volume
                        elif avg_vol < 50_000_000:
                            slippage_pct = 0.0005  # 0.05% for medium volume
                        else:
                            slippage_pct = 0.0002  # 0.02% for high volume

                        # Apply slippage to entry: buy at slightly higher price
                        entry_price = entry_price * (1 + slippage_pct)

                        shares = per_pos / entry_price
                        exit_price = entry_price
                        positions_this_period += 1

                        for d in range(entry_day, min(entry_day + hold_days, len(sd["close"]))):
                            low = sd["low"][d]
                            high = sd["high"][d]

                            if d >= 1:
                                pc = sd["close"][d - 1]
                                if pc > 0:
                                    code_str = code.replace("_", ".")
                                    if code_str.startswith("sh.688") or code_str.startswith("sz.3"):
                                        lim = 0.20
                                    else:
                                        lim = 0.10
                                    limit_down_price = pc * (1 - lim + 0.005)
                                    if sd["close"][d] <= limit_down_price:
                                        # Can't sell a limit-down stock on any day,
                                        # including the last hold day. The exit_price
                                        # stays at the previous day's close (or entry
                                        # if day 0). The position effectively carries
                                        # over until the limit is lifted.
                                        continue

                            sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                            if low <= sl_price:
                                exit_price = sl_price
                                break

                            tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                            if high >= tp_price:
                                exit_price = tp_price
                                break

                            exit_price = sd["close"][d]

                        # Apply slippage to exit: sell at slightly lower price
                        exit_price = exit_price * (1 - slippage_pct)

                        buy_cost = entry_price * (0.0003 + 0.0005)
                        sell_cost = exit_price * (0.0003 + 0.0005 + 0.001)
                        trade_return = (exit_price - entry_price - buy_cost - sell_cost) / entry_price * 100
                        bt_trades.append(trade_return)

                        pnl = shares * entry_price * trade_return / 100
                        if pnl > 0:
                            bt_gross_profit += pnl
                        else:
                            bt_gross_loss += abs(pnl)

                        bt_capital += pnl

                    # Update max concurrent positions
                    if positions_this_period > bt_max_concurrent:
                        bt_max_concurrent = positions_this_period

                bt_portfolio_values.append(max(bt_capital, 0.01))
                day += hold_days

            # Final partial month
            if month_start_capital > 0 and bt_capital != month_start_capital:
                mr = (bt_capital - month_start_capital) / month_start_capital * 100
                bt_monthly_returns.append(mr)

            # ── Compute metrics ──
            bt_total_trades = len(bt_trades)
            bt_win_rate = 0.0
            if bt_total_trades > 0:
                wins = sum(1 for t in bt_trades if t > 0)
                bt_win_rate = wins / bt_total_trades * 100

            # Max consecutive losses
            bt_max_consec_losses = 0
            current_streak = 0
            for t in bt_trades:
                if t <= 0:
                    current_streak += 1
                    bt_max_consec_losses = max(bt_max_consec_losses, current_streak)
                else:
                    current_streak = 0

            # Annual return
            bt_annual_return = 0.0
            if len(bt_portfolio_values) > 1 and bt_portfolio_values[0] > 0:
                total_return = bt_portfolio_values[-1] / bt_portfolio_values[0] - 1
                trading_days_used = day_end - day_start
                years = trading_days_used / 250 if trading_days_used > 0 else 1
                if total_return > -1:
                    bt_annual_return = ((1 + total_return) ** (1 / max(years, 0.01)) - 1) * 100
                else:
                    bt_annual_return = -100.0

            # Max drawdown
            bt_max_drawdown = 0.0
            peak = bt_portfolio_values[0]
            for v in bt_portfolio_values:
                if v > peak:
                    peak = v
                dd = (peak - v) / peak * 100 if peak > 0 else 0
                bt_max_drawdown = max(bt_max_drawdown, dd)

            # Sharpe ratio
            bt_sharpe = 0.0
            bt_sortino = 0.0
            if len(bt_portfolio_values) > 2:
                period_returns = [
                    (bt_portfolio_values[i] - bt_portfolio_values[i - 1]) / bt_portfolio_values[i - 1]
                    for i in range(1, len(bt_portfolio_values))
                    if bt_portfolio_values[i - 1] > 0
                ]
                if period_returns:
                    mean_r = sum(period_returns) / len(period_returns)
                    var_r = sum((r - mean_r) ** 2 for r in period_returns) / len(period_returns)
                    std_r = math.sqrt(var_r) if var_r > 0 else 0.001
                    periods_per_year = 250 / max(hold_days, 1)
                    bt_sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

                    # Sortino: downside deviation only
                    downside_returns = [r for r in period_returns if r < 0]
                    if downside_returns:
                        downside_var = sum(r ** 2 for r in downside_returns) / len(period_returns)
                        downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.001
                        bt_sortino = (mean_r / downside_std) * math.sqrt(periods_per_year)
                    else:
                        bt_sortino = bt_sharpe * 1.5  # no down periods = great

            bt_calmar = bt_annual_return / max(bt_max_drawdown, 1.0)
            bt_profit_factor = bt_gross_profit / bt_gross_loss if bt_gross_loss > 0 else (10.0 if bt_gross_profit > 0 else 0.0)

            # Compute average turnover
            bt_avg_turnover = 0.0
            if bt_turnover_ratios:
                bt_avg_turnover = sum(bt_turnover_ratios) / len(bt_turnover_ratios)

            return (bt_annual_return, bt_max_drawdown, bt_win_rate, bt_sharpe,
                    bt_calmar, bt_total_trades, bt_profit_factor, bt_sortino,
                    bt_max_consec_losses, bt_monthly_returns, bt_max_concurrent,
                    bt_avg_turnover)

        # ── Run backtests on train and validation periods ──
        # Choose the backtest dispatch callable
        if _run_backtest_dispatch is not None:
            _bt_fn = _run_backtest_dispatch
        else:
            _bt_fn = _run_backtest

        if self.walk_forward and self._wf_validator is not None:
            # ── NEW: Multi-window walk-forward validation ──
            wf_result = self._wf_validator.validate(
                _bt_fn, total_bars=total_days, warmup=warmup,
            )
            fitness = wf_result.final_fitness

            if wf_result.window_results:
                last_w = wf_result.window_results[-1]
                annual_return = last_w.oos_annual_return
                max_drawdown = last_w.oos_max_drawdown
                sharpe = last_w.oos_sharpe
                win_rate = last_w.oos_win_rate
                total_trades = sum(w.oos_trades for w in wf_result.window_results)
                # Use last window OOS metrics for remaining fields
                calmar = annual_return / max(max_drawdown, 1.0)
                profit_factor = 0.0  # not directly available from WindowResult
                sortino = 0.0
            else:
                annual_return = 0.0
                max_drawdown = 0.0
                sharpe = 0.0
                win_rate = 0.0
                total_trades = 0
                calmar = 0.0
                profit_factor = 0.0
                sortino = 0.0
        else:
            # ── LEGACY: Single 70/30 split (backward compatible) ──
            (train_ret, train_dd, train_wr, train_sharpe, train_calmar,
             train_trades, train_pf, train_sortino,
             train_consec_losses, train_monthly, train_max_concurrent,
             train_avg_turnover) = _bt_fn(warmup, train_end)

            (val_ret, val_dd, val_wr, val_sharpe, val_calmar,
             val_trades, val_pf, val_sortino,
             val_consec_losses, val_monthly, val_max_concurrent,
             val_avg_turnover) = _bt_fn(val_start, val_end)

            # Combine metrics (report validation-period numbers as primary)
            total_trades = train_trades + val_trades
            annual_return = val_ret
            max_drawdown = max(train_dd, val_dd)
            win_rate = val_wr
            sharpe = val_sharpe
            calmar = val_calmar
            profit_factor = val_pf
            sortino = val_sortino
            max_consec_losses = max(train_consec_losses, val_consec_losses)
            monthly_returns = (train_monthly or []) + (val_monthly or [])
            max_concurrent = max(train_max_concurrent, val_max_concurrent)

            train_fitness = compute_fitness(
                train_ret, train_dd, train_wr, train_sharpe, train_trades,
                sortino=train_sortino,
                max_consec_losses=train_consec_losses,
                monthly_returns=train_monthly,
                positions_used=train_max_concurrent,
                max_positions=dna.max_positions,
                avg_turnover=train_avg_turnover,
            )
            val_fitness = compute_fitness(
                val_ret, val_dd, val_wr, val_sharpe, val_trades,
                sortino=val_sortino,
                max_consec_losses=val_consec_losses,
                monthly_returns=val_monthly,
                positions_used=val_max_concurrent,
                max_positions=dna.max_positions,
                avg_turnover=val_avg_turnover,
            )

            fitness = 0.4 * train_fitness + 0.6 * val_fitness

            if train_fitness > 0 and val_fitness < 0.3 * train_fitness:
                fitness *= 0.3

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

    def _random_dna(self) -> StrategyDNA:
        """Generate a completely random StrategyDNA."""
        d = {}
        for param, (lo, hi, is_int) in _PARAM_RANGES.items():
            val = self.rng.uniform(lo, hi)
            if is_int:
                val = int(round(val))
            d[param] = val
        # Normalize weights
        w_sum = sum(d[k] for k in _WEIGHT_KEYS)
        if w_sum > 0:
            for k in _WEIGHT_KEYS:
                d[k] = round(d[k] / w_sum, 4)
        dna = StrategyDNA.from_dict(d)
        # Also randomize custom weights if factor registry exists
        if hasattr(self, '_factor_registry') and self._factor_registry and self._factor_registry.factors:
            cw = {}
            for name in self._factor_registry.list_factors():
                cw[name] = self.rng.uniform(0, 0.1)  # small random values
            dna.custom_weights = cw
        return dna

    def _strategy_distance(self, dna1: StrategyDNA, dna2: StrategyDNA) -> float:
        """Measure how different two strategies are (0=identical, 1=very different)."""
        d1 = dna1.to_dict()
        d2 = dna2.to_dict()
        diffs = []
        for param, (lo, hi, _) in _PARAM_RANGES.items():
            range_size = hi - lo
            if range_size > 0:
                diff = abs(d1.get(param, 0) - d2.get(param, 0)) / range_size
                diffs.append(diff)
        return sum(diffs) / len(diffs) if diffs else 0.0

    def _tournament_select(
        self, results: List[EvolutionResult]
    ) -> List[EvolutionResult]:
        """Select elite parents using tournament selection with elitism.

        - Always keeps the #1 best (elitism).
        - For remaining slots, picks 3 random candidates and takes the best.
        - Preserves diversity by giving weaker-but-different strategies a chance.
        """
        if len(results) <= self.elite_count:
            return list(results)

        # Elitism: always keep #1
        selected = [results[0]]

        # Tournament selection for remaining slots
        for _ in range(self.elite_count - 1):
            tournament = self.rng.sample(results, min(3, len(results)))
            winner = max(tournament, key=lambda r: r.fitness)
            if winner not in selected:
                selected.append(winner)
            else:
                # If winner already selected, take the next best from tournament
                found = False
                for t in sorted(tournament, key=lambda r: r.fitness, reverse=True):
                    if t not in selected:
                        selected.append(t)
                        found = True
                        break
                if not found:
                    # Fallback: pick next unselected result by rank
                    for r in results:
                        if r not in selected:
                            selected.append(r)
                            break

        return selected[:self.elite_count]

    def run_generation(
        self,
        parents: List[StrategyDNA],
        data: Dict[str, Dict[str, list]],
        gen: int = 0,
    ) -> List[EvolutionResult]:
        """Run one generation of evolution.

        1. Generate mutations + crossovers from parents
        2. Evaluate all candidates (with deterministic sampling via gen seed)
        3. Apply diversity bonus (niche preservation)
        4. Select elite via tournament selection
        5. Return top ``elite_count`` results
        """
        candidates: List[StrategyDNA] = list(parents)

        while len(candidates) < self.population_size:
            parent = self.rng.choice(parents)
            if self.rng.random() < 0.7:
                # Mutation
                child = self.mutate(parent)
            else:
                # Crossover with fitness-weighted bias toward better parent
                other = self.rng.choice(parents)
                child = self.crossover(parent, other, bias=0.6)
                child = self.mutate(child)  # mutate after crossover
            candidates.append(child)

        results = [self.evaluate(dna, data, gen_seed=gen) for dna in candidates]
        results.sort(key=lambda r: r.fitness, reverse=True)

        # Diversity bonus: strategies different from the champion get a small boost
        if len(results) > 1:
            champion_dna = results[0].dna
            for r in results[1:]:
                dist = self._strategy_distance(r.dna, champion_dna)
                # Up to 10% bonus for being very different
                diversity_bonus = 1.0 + dist * 0.1
                r.fitness *= diversity_bonus
            # Re-sort after applying diversity bonus
            results.sort(key=lambda r: r.fitness, reverse=True)

        # Tournament selection with elitism (replaces simple top-N)
        return self._tournament_select(results)

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
        print(" FinClaw Auto Evolution Engine")
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

        # Load factor registry and initialize custom_weights for all parents
        if not hasattr(self, '_factor_registry'):
            try:
                from src.evolution.factor_discovery import FactorRegistry, create_seed_factors
                create_seed_factors("factors")
                self._factor_registry = FactorRegistry("factors")
                self._factor_registry.load_all()
                factor_names = self._factor_registry.list_factors()
                if factor_names:
                    print(f"  [factors] loaded {len(factor_names)} dynamic factors: {factor_names}")
            except Exception as e:
                print(f"  [factors] skipped: {e}")
                self._factor_registry = None

        # Ensure all parents have custom_weights populated with discovered factor names
        if self._factor_registry and self._factor_registry.factors:
            discovered = self._factor_registry.list_factors()
            updated_parents = []
            for p in parents:
                cw = dict(p.custom_weights)  # copy
                for fname in discovered:
                    if fname not in cw:
                        cw[fname] = 0.0
                updated_parents.append(StrategyDNA(
                    **{f.name: getattr(p, f.name) for f in fields(p) if f.name != 'custom_weights'},
                    custom_weights=cw,
                ))
            parents = updated_parents

        print(f"Population: {self.population_size} | Elite: {self.elite_count} | "
              f"Mutation rate: {self.mutation_rate}")
        print("-" * 60)

        best_results: List[EvolutionResult] = []

        # Smart evolution: stagnation detection + adaptive mutation rate
        stagnation_counter = 0
        best_ever_fitness = 0.0
        base_mutation_rate = self.mutation_rate
        boost_gens = 0

        for gen in range(start_gen, start_gen + generations):
            gen_t0 = time.time()

            # Adaptive mutation rate
            if gen < start_gen + 30:
                self.mutation_rate = min(base_mutation_rate * 1.5, 0.8)
            elif stagnation_counter == 0 and boost_gens > 0:
                self.mutation_rate = min(base_mutation_rate * 2.0, 0.9)
                boost_gens -= 1
            else:
                self.mutation_rate = base_mutation_rate

            results = self.run_generation(parents, data, gen=gen)
            gen_time = time.time() - gen_t0

            best = results[0]
            best_results = results

            # Stagnation detection
            if best.fitness > best_ever_fitness:
                best_ever_fitness = best.fitness
                stagnation_counter = 0
            else:
                stagnation_counter += 1

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

            # Stagnation injection: replace worst 2 parents with random DNA
            if stagnation_counter >= 15:
                random_dna1 = self._random_dna()
                random_dna2 = self._random_dna()
                parents[-1] = random_dna1
                parents[-2] = random_dna2
                stagnation_counter = 0
                boost_gens = 5
                print("  [stagnation] No improvement for 15 gens -- injecting random DNA")

            # Periodic save
            if (gen + 1) % save_interval == 0 or gen == start_gen + generations - 1:
                self.save_results(gen, results)

        total_time = time.time() - t0
        self.mutation_rate = base_mutation_rate  # restore original rate
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

        # ═══════════════════════════════════════════════════════════
        # best_ever.json — GLOBAL all-time best, NEVER overwritten
        # unless a new record is set. Survives cycle restarts.
        # ═══════════════════════════════════════════════════════════
        current_best_fitness = best[0].fitness if best else 0.0
        best_ever_file = os.path.join(self.results_dir, "best_ever.json")
        prev_ever_fitness = 0.0
        if os.path.exists(best_ever_file):
            try:
                with open(best_ever_file, "r", encoding="utf-8") as f:
                    prev_ever = json.load(f)
                prev_ever_fitness = prev_ever.get("fitness", 0.0)
            except Exception:
                prev_ever_fitness = 0.0

        if current_best_fitness > prev_ever_fitness:
            best_ever_payload = {
                "fitness": current_best_fitness,
                "generation": gen,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "annual_return": best[0].annual_return,
                "max_drawdown": best[0].max_drawdown,
                "win_rate": best[0].win_rate,
                "sharpe": best[0].sharpe,
                "calmar": best[0].calmar,
                "total_trades": best[0].total_trades,
                "profit_factor": best[0].profit_factor,
                "dna": best[0].dna.to_dict(),
            }
            with open(best_ever_file, "w", encoding="utf-8") as f:
                json.dump(best_ever_payload, f, indent=2, ensure_ascii=False)
            print(f"  [best_ever] NEW ALL-TIME RECORD! fitness={current_best_fitness:.2f} "
                  f"(prev={prev_ever_fitness:.2f}) gen={gen} "
                  f"annual={best[0].annual_return:.1f}% sharpe={best[0].sharpe:.2f}")

            # Also save a timestamped copy so we never lose any record-breaking DNA
            hall_dir = os.path.join(self.results_dir, "hall_of_fame")
            os.makedirs(hall_dir, exist_ok=True)
            hof_name = f"record_gen{gen}_fit{int(current_best_fitness)}_" \
                       f"{time.strftime('%Y%m%d_%H%M%S')}.json"
            hof_path = os.path.join(hall_dir, hof_name)
            with open(hof_path, "w", encoding="utf-8") as f:
                json.dump(best_ever_payload, f, indent=2, ensure_ascii=False)

        # Auto-backup best DNA (per-cycle best, kept for reference)
        best_dir = os.path.join(self.results_dir, "best_dna")
        os.makedirs(best_dir, exist_ok=True)
        best_fitness_file = os.path.join(best_dir, "_best_fitness.txt")
        prev_best = 0.0
        if os.path.exists(best_fitness_file):
            try:
                prev_best = float(open(best_fitness_file).read().strip())
            except Exception:
                pass
        if current_best_fitness > prev_best:
            annual = int(best[0].annual_return)
            sharpe_val = round(best[0].sharpe, 1)
            backup_name = f"best_gen{gen}_annual{annual}_sharpe{sharpe_val}.json"
            backup_path = os.path.join(best_dir, backup_name)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            with open(best_fitness_file, "w") as f:
                f.write(str(current_best_fitness))
            print(f"  [backup] New cycle best! fitness={current_best_fitness:.1f} -> {backup_name}")

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
