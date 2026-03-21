"""
Unified Evolution System
=========================
Combines ALL existing components into one evolvable framework:
- cn_scanner signals (15 core signals, self-contained)
- Alpha158 factors (64 factors: 9 KBAR + 55 ROLLING)
- ML prediction (GBM probability via sklearn)
- Elite stock pool (500 quality stocks)
- Evolutionary parameter optimization

This is NOT a new system. It integrates everything we've built:
- cn_scanner.py signal functions → simplified, self-contained 0-10 scores
- scripts/alpha158_benchmark.py → compute_alpha158 factors
- auto_evolve.py → genetic algorithm + backtest engine
- Gen 349 best DNA → starting point for optimization

Architecture:
  UnifiedDNA      — all tunable parameters in one genome
  UnifiedEvolver  — master evolution engine that scores, backtests, evolves
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

import numpy as np


# ════════════════════════════════════════════════════════════════════
# UnifiedDNA — ALL tunable parameters in one place
# ════════════════════════════════════════════════════════════════════

# Weight keys for cn_scanner signals
_CN_SIGNAL_KEYS: List[str] = [
    "w_volume_breakout",
    "w_bottom_reversal",
    "w_macd_divergence",
    "w_ma_alignment",
    "w_low_volume_pullback",
    "w_nday_breakout",
    "w_momentum_confirmation",
    "w_three_soldiers",
    "w_long_lower_shadow",
    "w_doji_at_bottom",
    "w_volume_climax_reversal",
    "w_accumulation",
    "w_rsi_divergence",
    "w_squeeze_release",
    "w_adx_trend",
]

# Source blend weight keys
_SOURCE_WEIGHT_KEYS: List[str] = [
    "w_cn_scanner",
    "w_ml",
    "w_technical",
]


@dataclass
class UnifiedDNA:
    """All tunable parameters in one genome.

    Sections:
      1. Source blend weights (cn_scanner vs ML vs technical)
      2. cn_scanner signal weights (15)
      3. ML model hyperparameters
      4. Trading parameters
      5. Stock pool filters
    """

    # ── Source blend weights (normalized to sum=1) ──
    w_cn_scanner: float = 0.45
    w_ml: float = 0.30
    w_technical: float = 0.25

    # ── cn_scanner signal weights (15, normalized to sum=1) ──
    w_volume_breakout: float = 0.08
    w_bottom_reversal: float = 0.10
    w_macd_divergence: float = 0.08
    w_ma_alignment: float = 0.07
    w_low_volume_pullback: float = 0.07
    w_nday_breakout: float = 0.06
    w_momentum_confirmation: float = 0.05
    w_three_soldiers: float = 0.07
    w_long_lower_shadow: float = 0.07
    w_doji_at_bottom: float = 0.05
    w_volume_climax_reversal: float = 0.07
    w_accumulation: float = 0.05
    w_rsi_divergence: float = 0.08
    w_squeeze_release: float = 0.05
    w_adx_trend: float = 0.05

    # ── ML model hyperparameters ──
    ml_n_estimators: int = 100
    ml_max_depth: int = 5
    ml_learning_rate: float = 0.05
    ml_subsample: float = 0.8
    ml_train_ratio: float = 0.7

    # ── Trading parameters (from Gen 349 best) ──
    hold_days: int = 2        # A-share T+1 minimum
    stop_loss_pct: float = 5.9
    take_profit_pct: float = 25.0
    max_positions: int = 2
    min_score: float = 3.0    # minimum unified score to consider
    rsi_buy_threshold: float = 18.0  # from Gen 349

    # ── Stock pool filters ──
    min_daily_amount: float = 20_000_000.0  # 2000万
    min_price: float = 5.0
    max_stocks: int = 500

    # ── Alpha158 feature selection (bitmask-like: which factor groups to use) ──
    use_kbar: bool = True
    use_roc: bool = True
    use_ma: bool = True
    use_std: bool = True
    use_beta: bool = True
    use_maxmin: bool = True
    use_rsv: bool = True
    use_corr: bool = True
    use_cntp: bool = True
    use_vma: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "UnifiedDNA":
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def get_source_weights(self) -> Tuple[float, float, float]:
        """Return normalized (w_cn, w_ml, w_tech) weights."""
        total = self.w_cn_scanner + self.w_ml + self.w_technical
        if total <= 0:
            return (0.34, 0.33, 0.33)
        return (
            self.w_cn_scanner / total,
            self.w_ml / total,
            self.w_technical / total,
        )

    def get_signal_weights(self) -> Dict[str, float]:
        """Return normalized cn_scanner signal weights."""
        raw = {k: getattr(self, k) for k in _CN_SIGNAL_KEYS}
        total = sum(raw.values())
        if total <= 0:
            n = len(raw)
            return {k: 1.0 / n for k in raw}
        return {k: v / total for k, v in raw.items()}


# Valid ranges for mutation
_PARAM_RANGES: Dict[str, Tuple[float, float, bool]] = {
    # Source weights
    "w_cn_scanner": (0.0, 1.0, False),
    "w_ml": (0.0, 1.0, False),
    "w_technical": (0.0, 1.0, False),
    # Signal weights
    **{k: (0.0, 1.0, False) for k in _CN_SIGNAL_KEYS},
    # ML hyperparameters
    "ml_n_estimators": (50, 500, True),
    "ml_max_depth": (3, 10, True),
    "ml_learning_rate": (0.01, 0.2, False),
    "ml_subsample": (0.5, 1.0, False),
    "ml_train_ratio": (0.5, 0.8, False),
    # Trading
    "hold_days": (2, 15, True),
    "stop_loss_pct": (1.0, 15.0, False),
    "take_profit_pct": (5.0, 50.0, False),
    "max_positions": (1, 10, True),
    "min_score": (1.0, 8.0, False),
    "rsi_buy_threshold": (10.0, 50.0, False),
    # Stock pool
    "min_daily_amount": (5_000_000.0, 100_000_000.0, False),
    "min_price": (2.0, 20.0, False),
    "max_stocks": (100, 1000, True),
}


# ════════════════════════════════════════════════════════════════════
# cn_scanner signals — self-contained implementations (0-10 scores)
# Adapted from src/cn_scanner.py signal functions
# ════════════════════════════════════════════════════════════════════

def _ema_np(data: np.ndarray, period: int) -> np.ndarray:
    """Simple EMA helper for numpy arrays."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(data, dtype=np.float64)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


def _rsi_np(data: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI using numpy."""
    delta = np.diff(data)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = _ema_np(gain, period)
    avg_loss = _ema_np(loss, period)
    rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
    out = np.empty(len(data))
    out[0] = np.nan
    out[1:] = 100.0 - 100.0 / (1.0 + rs)
    return out


def _sma_np(data: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average."""
    out = np.full_like(data, np.nan)
    cs = np.cumsum(data)
    out[period - 1] = cs[period - 1] / period
    out[period:] = (cs[period:] - cs[:-period]) / period
    return out


def _macd_np(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD → (line, signal, histogram)."""
    line = _ema_np(data, 12) - _ema_np(data, 26)
    sig = _ema_np(line, 9)
    hist = line - sig
    return line, sig, hist


def _bb_bandwidth(data: np.ndarray, period: int = 20) -> np.ndarray:
    """Bollinger Band bandwidth."""
    mid = _sma_np(data, period)
    bw = np.full_like(data, np.nan)
    for i in range(period - 1, len(data)):
        std = np.std(data[i - period + 1: i + 1], ddof=0)
        if mid[i] > 0:
            bw[i] = (2 * 2 * std) / mid[i]
    return bw


def signal_volume_breakout(closes: np.ndarray, volumes: np.ndarray, idx: int) -> float:
    """Volume Breakout: price up >2% AND volume > 2x 20-day avg. Score 0-10."""
    if idx < 21 or idx >= len(closes):
        return 0.0
    change = (closes[idx] / closes[idx - 1] - 1) * 100
    avg_vol = np.mean(volumes[idx - 20:idx])
    if avg_vol <= 0:
        return 0.0
    vol_ratio = volumes[idx] / avg_vol
    if change > 2.0 and vol_ratio > 2.0:
        # Scale: change 2-5% → 5-8, vol_ratio 2-5 → bonus
        base = min(change / 5.0, 1.0) * 6.0 + 2.0
        vol_bonus = min((vol_ratio - 2.0) / 3.0, 1.0) * 2.0
        return min(base + vol_bonus, 10.0)
    return 0.0


def signal_bottom_reversal(closes: np.ndarray, rsi_arr: np.ndarray, idx: int) -> float:
    """Bottom Reversal: RSI < 25 AND price bouncing. Score 0-10."""
    if idx < 2 or idx >= len(closes):
        return 0.0
    rsi_val = rsi_arr[idx] if idx < len(rsi_arr) and not np.isnan(rsi_arr[idx]) else 50.0
    if rsi_val < 25.0 and closes[idx] > closes[idx - 1]:
        # Deeper oversold → higher score
        return min(10.0, 6.0 + (25.0 - rsi_val) * 0.2)
    return 0.0


def signal_macd_divergence(closes: np.ndarray, macd_hist: np.ndarray, idx: int) -> float:
    """MACD Bullish Divergence: price new low but MACD hist higher. Score 0-10."""
    if idx < 20 or idx >= len(closes) or idx >= len(macd_hist):
        return 0.0
    recent_10 = closes[idx - 9:idx + 1]
    if closes[idx] > np.min(recent_10) * 1.005:
        return 0.0
    prev_window = closes[idx - 20:idx - 10]
    if len(prev_window) == 0:
        return 0.0
    prev_low_off = int(np.argmin(prev_window))
    prev_low_idx = idx - 20 + prev_low_off
    curr_hist = macd_hist[idx]
    prev_hist = macd_hist[prev_low_idx] if prev_low_idx < len(macd_hist) else np.nan
    if np.isnan(curr_hist) or np.isnan(prev_hist):
        return 0.0
    if closes[idx] <= closes[prev_low_idx] and curr_hist > prev_hist:
        return 7.0
    return 0.0


def signal_ma_alignment(closes: np.ndarray, idx: int) -> float:
    """MA Alignment: Close > MA5 > MA10 > MA20. Score 0-10."""
    if idx < 20 or idx >= len(closes):
        return 0.0
    ma5 = np.mean(closes[idx - 4:idx + 1])
    ma10 = np.mean(closes[idx - 9:idx + 1])
    ma20 = np.mean(closes[idx - 19:idx + 1])
    if closes[idx] > ma5 > ma10 > ma20:
        return 6.0
    return 0.0


def signal_low_volume_pullback(closes: np.ndarray, volumes: np.ndarray, idx: int) -> float:
    """Low-Volume Pullback in uptrend. Score 0-10."""
    if idx < 25 or idx >= len(closes):
        return 0.0
    ma20_now = np.mean(closes[idx - 19:idx + 1])
    ma20_5ago = np.mean(closes[idx - 24:idx - 4])
    if ma20_now <= ma20_5ago:
        return 0.0
    down_count = sum(1 for i in range(idx - 2, idx + 1) if closes[i] < closes[i - 1])
    if down_count < 2:
        return 0.0
    if not (volumes[idx] < volumes[idx - 1] and volumes[idx - 1] < volumes[idx - 2]):
        return 0.0
    if closes[idx] < ma20_now:
        return 0.0
    return 7.0


def signal_nday_breakout(closes: np.ndarray, idx: int, n: int = 20) -> float:
    """N-Day Breakout: price at N-day high. Score 0-10."""
    if idx < n or idx >= len(closes):
        return 0.0
    n_day_max = np.max(closes[idx - n:idx + 1])
    if closes[idx] >= n_day_max:
        return 5.0
    return 0.0


def signal_momentum_confirmation(closes: np.ndarray, idx: int) -> float:
    """Momentum: 10d and 20d returns both positive. Score 0-10."""
    if idx < 21 or idx >= len(closes):
        return 0.0
    ret_10d = (closes[idx] / closes[idx - 10] - 1) * 100
    ret_20d = (closes[idx] / closes[idx - 20] - 1) * 100
    if ret_10d > 0 and ret_20d > 0:
        return min(3.0 + ret_10d * 0.5, 7.0)
    return 0.0


def signal_three_soldiers(
    opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
    closes: np.ndarray, idx: int,
) -> float:
    """Three Soldiers: 3 consecutive bullish candles closing near high. Score 0-10."""
    if idx < 3 or idx >= len(closes):
        return 0.0
    for offset in range(3):
        i = idx - 2 + offset
        if closes[i] <= opens[i]:
            return 0.0
        body = closes[i] - opens[i]
        if body <= 0:
            return 0.0
        upper_wick = highs[i] - closes[i]
        if upper_wick > 0.3 * body:
            return 0.0
    return 7.0


def signal_long_lower_shadow(
    opens: np.ndarray, highs: np.ndarray, lows: np.ndarray,
    closes: np.ndarray, rsi_arr: np.ndarray, idx: int,
) -> float:
    """Long Lower Shadow at oversold. Score 0-10."""
    if idx < 1 or idx >= len(closes):
        return 0.0
    body = abs(closes[idx] - opens[idx])
    if body < 1e-10:
        body = 1e-10
    lower_shadow = min(closes[idx], opens[idx]) - lows[idx]
    rsi_val = rsi_arr[idx] if idx < len(rsi_arr) and not np.isnan(rsi_arr[idx]) else 50.0
    if lower_shadow > 2.0 * body and rsi_val < 35.0:
        return 7.0
    return 0.0


def signal_doji_at_bottom(
    opens: np.ndarray, closes: np.ndarray, volumes: np.ndarray,
    rsi_arr: np.ndarray, idx: int,
) -> float:
    """Doji at Bottom: open ≈ close, RSI<40, low volume. Score 0-10."""
    if idx < 21 or idx >= len(closes):
        return 0.0
    price = closes[idx]
    if price <= 0:
        return 0.0
    body_pct = abs(closes[idx] - opens[idx]) / price * 100
    if body_pct > 0.5:
        return 0.0
    rsi_val = rsi_arr[idx] if idx < len(rsi_arr) and not np.isnan(rsi_arr[idx]) else 50.0
    if rsi_val >= 40.0:
        return 0.0
    avg_vol = np.mean(volumes[idx - 20:idx])
    if avg_vol <= 0:
        return 0.0
    vol_ratio = volumes[idx] / avg_vol
    if vol_ratio < 0.7:
        return 5.0
    return 0.0


def signal_volume_climax_reversal(closes: np.ndarray, volumes: np.ndarray, idx: int) -> float:
    """Volume Climax Reversal: huge vol on down day, then up. Score 0-10."""
    if idx < 21 or idx >= len(closes):
        return 0.0
    avg_vol = np.mean(volumes[idx - 20:idx - 1])
    if avg_vol <= 0:
        return 0.0
    if closes[idx - 1] >= closes[idx - 2]:
        return 0.0
    vol_ratio_prev = volumes[idx - 1] / avg_vol
    if vol_ratio_prev <= 3.0:
        return 0.0
    if closes[idx] <= closes[idx - 1]:
        return 0.0
    return 7.0


def signal_accumulation(closes: np.ndarray, volumes: np.ndarray, idx: int) -> float:
    """Accumulation: price flat, volume increasing. Score 0-10."""
    if idx < 11 or idx >= len(closes):
        return 0.0
    price_range = (np.max(closes[idx - 4:idx + 1]) - np.min(closes[idx - 4:idx + 1]))
    if closes[idx - 4] > 0:
        price_range_pct = price_range / closes[idx - 4] * 100
    else:
        return 0.0
    if price_range_pct > 3.0:
        return 0.0
    avg_vol_recent = np.mean(volumes[idx - 4:idx + 1])
    avg_vol_prev = np.mean(volumes[idx - 9:idx - 4])
    if avg_vol_prev <= 0:
        return 0.0
    vol_increase = (avg_vol_recent / avg_vol_prev - 1) * 100
    if vol_increase > 50.0:
        return 5.0
    return 0.0


def signal_rsi_bullish_divergence(closes: np.ndarray, rsi_arr: np.ndarray, idx: int) -> float:
    """RSI Bullish Divergence: price new low but RSI higher. Score 0-10."""
    if idx < 20 or idx >= len(closes) or idx >= len(rsi_arr):
        return 0.0
    recent_low = np.min(closes[idx - 9:idx + 1])
    if closes[idx] > recent_low * 1.005:
        return 0.0
    prev_window = closes[idx - 20:idx - 10]
    if len(prev_window) == 0:
        return 0.0
    prev_low_off = int(np.argmin(prev_window))
    prev_low_idx = idx - 20 + prev_low_off
    if closes[idx] > closes[prev_low_idx]:
        return 0.0
    rsi_now = rsi_arr[idx]
    rsi_prev = rsi_arr[prev_low_idx] if prev_low_idx < len(rsi_arr) else np.nan
    if np.isnan(rsi_now) or np.isnan(rsi_prev):
        return 0.0
    if rsi_now > rsi_prev:
        return 7.0
    return 0.0


def signal_squeeze_release(closes: np.ndarray, idx: int) -> float:
    """Squeeze Release: BB bandwidth expanding after tight squeeze. Score 0-10."""
    if idx < 30 or idx >= len(closes):
        return 0.0
    bw = _bb_bandwidth(closes[:idx + 1])
    if len(bw) < 6:
        return 0.0
    squeeze_found = False
    for end_offset in range(1, 4):
        if len(bw) < end_offset + 5:
            continue
        window = bw[-(end_offset + 5):-end_offset]
        valid = window[~np.isnan(window)]
        if len(valid) >= 5 and np.all(valid < 0.05):
            squeeze_found = True
            break
    if not squeeze_found:
        return 0.0
    curr_bw = float(bw[-1])
    if np.isnan(curr_bw):
        return 0.0
    if curr_bw >= 0.05:
        return 7.0
    return 0.0


def signal_adx_trend_strength(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, idx: int,
) -> float:
    """ADX Trend Strength: ADX > 25 AND +DI > -DI. Score 0-10."""
    if idx < 30 or idx >= len(closes):
        return 0.0
    # Simplified ADX calculation for the window ending at idx
    period = 14
    n = min(idx + 1, 60)
    h = highs[idx - n + 1:idx + 1]
    l = lows[idx - n + 1:idx + 1]
    c = closes[idx - n + 1:idx + 1]
    if len(c) < period + 1:
        return 0.0
    plus_dm = np.zeros(len(c))
    minus_dm = np.zeros(len(c))
    tr = np.zeros(len(c))
    tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr_val = _ema_np(tr, period)
    plus_di = 100 * _ema_np(plus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    minus_di = 100 * _ema_np(minus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    dx = 100 * np.abs(plus_di - minus_di) / np.where(plus_di + minus_di == 0, 1e-10, plus_di + minus_di)
    adx_arr = _ema_np(dx, period)
    a = float(adx_arr[-1])
    p = float(plus_di[-1])
    m = float(minus_di[-1])
    if np.isnan(a) or np.isnan(p) or np.isnan(m):
        return 0.0
    if a > 25.0 and p > m:
        return min(5.0 + (a - 25.0) * 0.1, 8.0)
    return 0.0


# ════════════════════════════════════════════════════════════════════
# Alpha158 Factor Computation (from scripts/alpha158_benchmark.py)
# ════════════════════════════════════════════════════════════════════

def compute_alpha158(
    dates: np.ndarray,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    dna: Optional[UnifiedDNA] = None,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[str]]]:
    """Compute Alpha158 factors for all days.

    Returns (X, y, feature_names) where:
      X: (n_days, n_features) feature matrix
      y: (n_days,) forward 2-day return labels
      feature_names: list of feature name strings

    Feature groups can be toggled via dna.use_* flags.
    """
    n = len(closes)
    if n < 61:
        return None, None, None

    features = []
    feature_names = []

    # === KBAR features (9) ===
    if dna is None or dna.use_kbar:
        kmid = (closes - opens) / (opens + 1e-10)
        klen = (highs - lows) / (opens + 1e-10)
        kmid2 = np.where(highs != lows, (closes - opens) / (highs - lows + 1e-10), 0)
        kup = (highs - np.maximum(opens, closes)) / (opens + 1e-10)
        kup2 = np.where(highs != lows, (highs - np.maximum(opens, closes)) / (highs - lows + 1e-10), 0)
        klow = (np.minimum(opens, closes) - lows) / (opens + 1e-10)
        klow2 = np.where(highs != lows, (np.minimum(opens, closes) - lows) / (highs - lows + 1e-10), 0)
        ksft = (2 * closes - highs - lows) / (opens + 1e-10)
        ksft2 = np.where(highs != lows, (2 * closes - highs - lows) / (highs - lows + 1e-10), 0)

        for f, name in [
            (kmid, "KMID"), (klen, "KLEN"), (kmid2, "KMID2"),
            (kup, "KUP"), (kup2, "KUP2"), (klow, "KLOW"), (klow2, "KLOW2"),
            (ksft, "KSFT"), (ksft2, "KSFT2"),
        ]:
            features.append(f)
            feature_names.append(name)

    # === ROLLING features with windows [5, 10, 20, 30, 60] ===
    windows = [5, 10, 20, 30, 60]

    for w in windows:
        # ROC: Rate of Change
        if dna is None or dna.use_roc:
            roc = np.full(n, np.nan)
            for i in range(w, n):
                roc[i] = closes[i - w] / (closes[i] + 1e-10)
            features.append(roc)
            feature_names.append(f"ROC{w}")

        # MA: Moving Average ratio
        if dna is None or dna.use_ma:
            ma = np.full(n, np.nan)
            for i in range(w - 1, n):
                ma[i] = np.mean(closes[i - w + 1:i + 1]) / (closes[i] + 1e-10)
            features.append(ma)
            feature_names.append(f"MA{w}")

        # STD: Standard Deviation ratio
        if dna is None or dna.use_std:
            std = np.full(n, np.nan)
            for i in range(w - 1, n):
                std[i] = np.std(closes[i - w + 1:i + 1]) / (closes[i] + 1e-10)
            features.append(std)
            feature_names.append(f"STD{w}")

        # BETA: Linear regression slope
        if dna is None or dna.use_beta:
            beta = np.full(n, np.nan)
            for i in range(w - 1, n):
                seg = closes[i - w + 1:i + 1]
                x = np.arange(w)
                slope = np.polyfit(x, seg, 1)[0]
                beta[i] = slope / (closes[i] + 1e-10)
            features.append(beta)
            feature_names.append(f"BETA{w}")

        # MAX/MIN ratio
        if dna is None or dna.use_maxmin:
            mx = np.full(n, np.nan)
            mn = np.full(n, np.nan)
            for i in range(w - 1, n):
                mx[i] = np.max(highs[i - w + 1:i + 1]) / (closes[i] + 1e-10)
                mn[i] = np.min(lows[i - w + 1:i + 1]) / (closes[i] + 1e-10)
            features.append(mx)
            feature_names.append(f"MAX{w}")
            features.append(mn)
            feature_names.append(f"MIN{w}")

        # RSV
        if dna is None or dna.use_rsv:
            rsv = np.full(n, np.nan)
            for i in range(w - 1, n):
                h_n = np.max(highs[i - w + 1:i + 1])
                l_n = np.min(lows[i - w + 1:i + 1])
                rsv[i] = (closes[i] - l_n) / (h_n - l_n + 1e-10)
            features.append(rsv)
            feature_names.append(f"RSV{w}")

        # CORR
        if dna is None or dna.use_corr:
            corr = np.full(n, np.nan)
            for i in range(w - 1, n):
                c_seg = closes[i - w + 1:i + 1]
                v_seg = np.log(volumes[i - w + 1:i + 1] + 1)
                if np.std(c_seg) > 0 and np.std(v_seg) > 0:
                    corr[i] = np.corrcoef(c_seg, v_seg)[0, 1]
            features.append(corr)
            feature_names.append(f"CORR{w}")

        # CNTP/CNTN
        if dna is None or dna.use_cntp:
            cntp = np.full(n, np.nan)
            cntn = np.full(n, np.nan)
            for i in range(w, n):
                up = np.sum(closes[i - w + 1:i + 1] > closes[i - w:i])
                down = np.sum(closes[i - w + 1:i + 1] < closes[i - w:i])
                cntp[i] = up / w
                cntn[i] = down / w
            features.append(cntp)
            feature_names.append(f"CNTP{w}")
            features.append(cntn)
            feature_names.append(f"CNTN{w}")

        # VMA
        if dna is None or dna.use_vma:
            vma = np.full(n, np.nan)
            for i in range(w - 1, n):
                vma[i] = np.mean(volumes[i - w + 1:i + 1]) / (volumes[i] + 1e-10)
            features.append(vma)
            feature_names.append(f"VMA{w}")

    # Stack features
    X = np.column_stack(features)

    # Label: 2-day forward return (T+1 buy, T+2 sell)
    y = np.full(n, np.nan)
    for i in range(n - 2):
        y[i] = (closes[i + 2] / closes[i + 1] - 1)

    return X, y, feature_names


# ════════════════════════════════════════════════════════════════════
# UnifiedEvolver — the master evolution engine
# ════════════════════════════════════════════════════════════════════

class UnifiedEvolver:
    """Master evolution engine integrating cn_scanner + Alpha158 + ML + elite pool.

    Usage:
        evolver = UnifiedEvolver("data/a_shares")
        results = evolver.evolve(generations=100, population=30)
    """

    def __init__(
        self,
        data_dir: str,
        best_dna: Optional[UnifiedDNA] = None,
        population_size: int = 30,
        elite_count: int = 5,
        mutation_rate: float = 0.3,
        results_dir: str = "evolution_results_unified",
        seed: Optional[int] = None,
    ):
        self.data_dir = data_dir
        self.best_dna = best_dna or UnifiedDNA()
        self.population_size = population_size
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.results_dir = results_dir
        self.rng = random.Random(seed)
        os.makedirs(results_dir, exist_ok=True)

    # ── Data Loading ─────────────────────────────────────────────

    def load_elite_pool(self, dna: Optional[UnifiedDNA] = None) -> Dict[str, Dict[str, Any]]:
        """Load top quality stocks from CSV data.

        Applies filters: min_daily_amount, min_price, max_stocks.
        Returns dict: code -> {date, open, high, low, close, volume}
        """
        d = dna or self.best_dna
        data: Dict[str, Dict[str, Any]] = {}
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

                required = {"date", "open", "high", "low", "close", "volume"}
                if not required.issubset(col_map.keys()):
                    continue

                dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if len(parts) > max(col_map.values()):
                        try:
                            dates.append(parts[col_map["date"]])
                            o = float(parts[col_map["open"]])
                            h = float(parts[col_map["high"]])
                            l = float(parts[col_map["low"]])
                            c = float(parts[col_map["close"]])
                            v = float(parts[col_map["volume"]])
                            if c > 0:
                                opens.append(o)
                                highs.append(h)
                                lows.append(l)
                                closes.append(c)
                                volumes.append(v)
                            else:
                                dates.pop()
                        except (ValueError, IndexError):
                            if dates and len(dates) > len(closes):
                                dates.pop()
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

        # Apply quality filters
        if len(data) > d.max_stocks:
            data = self._filter_stock_pool(data, d)

        return data

    def _filter_stock_pool(
        self, data: Dict[str, Dict[str, Any]], dna: UnifiedDNA,
    ) -> Dict[str, Dict[str, Any]]:
        """Filter stock pool by quality metrics (from auto_evolve.py)."""
        scored: List[Tuple[str, float]] = []
        for code, sd in data.items():
            closes = sd["close"]
            volumes = sd["volume"]
            if not closes:
                continue
            if closes[-1] < dna.min_price:
                continue
            recent_n = min(60, len(closes))
            avg_amount = sum(
                closes[-recent_n + i] * volumes[-recent_n + i]
                for i in range(recent_n)
            ) / recent_n
            if avg_amount < dna.min_daily_amount:
                continue
            # Bonus for limit-up activity
            bonus = 0.0
            for i in range(max(1, len(closes) - 60), len(closes)):
                if closes[i - 1] > 0:
                    ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                    if ret >= 0.095:
                        bonus += 1.0
            quality = avg_amount / 1e8 + bonus * 0.5
            scored.append((code, quality))

        scored.sort(key=lambda x: x[1], reverse=True)
        keep = {code for code, _ in scored[:dna.max_stocks]}
        return {code: sd for code, sd in data.items() if code in keep}

    # ── cn_scanner Signal Computation ────────────────────────────

    def compute_cn_scanner_signals(
        self, sd: Dict[str, Any], idx: int,
    ) -> Dict[str, float]:
        """Compute all 15 cn_scanner signals at given index.

        Returns dict of signal_name -> score (0-10).
        """
        closes = np.array(sd["close"], dtype=np.float64)
        volumes = np.array(sd["volume"], dtype=np.float64)
        opens = np.array(sd["open"], dtype=np.float64)
        highs = np.array(sd["high"], dtype=np.float64)
        lows = np.array(sd["low"], dtype=np.float64)

        # Pre-compute shared indicators
        rsi_arr = _rsi_np(closes)
        _, _, macd_hist = _macd_np(closes)

        signals: Dict[str, float] = {}
        signals["volume_breakout"] = signal_volume_breakout(closes, volumes, idx)
        signals["bottom_reversal"] = signal_bottom_reversal(closes, rsi_arr, idx)
        signals["macd_divergence"] = signal_macd_divergence(closes, macd_hist, idx)
        signals["ma_alignment"] = signal_ma_alignment(closes, idx)
        signals["low_volume_pullback"] = signal_low_volume_pullback(closes, volumes, idx)
        signals["nday_breakout"] = signal_nday_breakout(closes, idx)
        signals["momentum_confirmation"] = signal_momentum_confirmation(closes, idx)
        signals["three_soldiers"] = signal_three_soldiers(opens, highs, lows, closes, idx)
        signals["long_lower_shadow"] = signal_long_lower_shadow(opens, highs, lows, closes, rsi_arr, idx)
        signals["doji_at_bottom"] = signal_doji_at_bottom(opens, closes, volumes, rsi_arr, idx)
        signals["volume_climax_reversal"] = signal_volume_climax_reversal(closes, volumes, idx)
        signals["accumulation"] = signal_accumulation(closes, volumes, idx)
        signals["rsi_divergence"] = signal_rsi_bullish_divergence(closes, rsi_arr, idx)
        signals["squeeze_release"] = signal_squeeze_release(closes, idx)
        signals["adx_trend"] = signal_adx_trend_strength(highs, lows, closes, idx)

        return signals

    # ── Alpha158 Feature Computation ─────────────────────────────

    def compute_alpha158_features(
        self, sd: Dict[str, Any], idx: int, dna: Optional[UnifiedDNA] = None,
    ) -> Optional[np.ndarray]:
        """Compute Alpha158 features at given index.

        Returns feature vector (1D) or None if insufficient data.
        """
        closes = np.array(sd["close"][:idx + 1], dtype=np.float64)
        opens = np.array(sd["open"][:idx + 1], dtype=np.float64)
        highs = np.array(sd["high"][:idx + 1], dtype=np.float64)
        lows = np.array(sd["low"][:idx + 1], dtype=np.float64)
        volumes = np.array(sd["volume"][:idx + 1], dtype=np.float64)
        dates = np.array(sd["date"][:idx + 1])

        result = compute_alpha158(dates, opens, highs, lows, closes, volumes, dna)
        if result[0] is None:
            return None

        X, _, _ = result
        # Return the last row (features at idx)
        row = X[-1]
        if np.any(np.isnan(row)):
            row = np.nan_to_num(row, nan=0.0, posinf=0.0, neginf=0.0)
        return row

    # ── ML Model Training ────────────────────────────────────────

    def train_ml_model(
        self, data: Dict[str, Dict[str, Any]], dna: UnifiedDNA,
    ) -> Optional[Any]:
        """Train a GBM model on Alpha158 features.

        Uses sklearn GradientBoostingRegressor (avoids LightGBM DLL issues).
        Returns trained model or None if insufficient data.
        """
        try:
            from sklearn.ensemble import GradientBoostingRegressor
        except ImportError:
            return None

        all_X = []
        all_y = []
        loaded = 0

        for code, sd in data.items():
            closes = np.array(sd["close"], dtype=np.float64)
            opens = np.array(sd["open"], dtype=np.float64)
            highs = np.array(sd["high"], dtype=np.float64)
            lows = np.array(sd["low"], dtype=np.float64)
            volumes = np.array(sd["volume"], dtype=np.float64)
            dates = np.array(sd["date"])

            if len(closes) < 120 or closes[-1] < dna.min_price:
                continue
            if np.mean(volumes[-20:]) * closes[-1] < dna.min_daily_amount * 0.5:
                continue

            result = compute_alpha158(dates, opens, highs, lows, closes, volumes, dna)
            if result[0] is None:
                continue
            X, y, _ = result

            valid = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            if valid.sum() < 60:
                continue

            all_X.append(X[valid])
            all_y.append(y[valid])
            loaded += 1
            if loaded >= 200:
                break

        if not all_X:
            return None

        X = np.vstack(all_X)
        y = np.concatenate(all_y)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        split = int(len(y) * dna.ml_train_ratio)
        if split < 50 or len(y) - split < 20:
            return None

        X_train, y_train = X[:split], y[:split]

        model = GradientBoostingRegressor(
            n_estimators=dna.ml_n_estimators,
            max_depth=dna.ml_max_depth,
            learning_rate=dna.ml_learning_rate,
            subsample=dna.ml_subsample,
            random_state=42,
        )
        model.fit(X_train, y_train)
        return model

    # ── Unified Scoring ──────────────────────────────────────────

    def score_stock(
        self,
        sd: Dict[str, Any],
        idx: int,
        dna: UnifiedDNA,
        ml_model: Optional[Any] = None,
        precomputed_signals: Optional[Dict[str, float]] = None,
    ) -> float:
        """Unified scoring combining all sources.

        1. cn_scanner signals (weighted sum) → normalized to 0-10
        2. Alpha158-based ML prediction → normalized to 0-10
        3. Technical pattern score (RSI, momentum) → 0-10

        final_score = w_cn * cn_score + w_ml * ml_score + w_tech * tech_score
        """
        w_cn, w_ml, w_tech = dna.get_source_weights()

        # 1. cn_scanner signals
        if precomputed_signals is not None:
            signals = precomputed_signals
        else:
            signals = self.compute_cn_scanner_signals(sd, idx)

        signal_weights = dna.get_signal_weights()
        cn_score = 0.0
        for sig_name, sig_val in signals.items():
            w_key = f"w_{sig_name}"
            w = signal_weights.get(w_key, 1.0 / 15)
            cn_score += w * sig_val
        # cn_score is already 0-10 range (weighted average of 0-10 scores)

        # 2. ML prediction
        ml_score = 5.0  # neutral default
        if ml_model is not None and w_ml > 0.01:
            features = self.compute_alpha158_features(sd, idx, dna)
            if features is not None:
                try:
                    pred = ml_model.predict(features.reshape(1, -1))[0]
                    # Predicted return → score: +2% = 10, -2% = 0, 0% = 5
                    ml_score = max(0.0, min(10.0, 5.0 + pred * 250.0))
                except Exception:
                    pass

        # 3. Technical pattern score
        closes = sd["close"]
        if idx < 21 or idx >= len(closes):
            tech_score = 5.0
        else:
            tech_score = 5.0
            c = closes[idx]
            # RSI component
            rsi_arr = _rsi_np(np.array(closes[:idx + 1], dtype=np.float64))
            rsi_val = rsi_arr[-1] if not np.isnan(rsi_arr[-1]) else 50.0
            if rsi_val < dna.rsi_buy_threshold:
                tech_score += 2.5
            elif rsi_val < 30:
                tech_score += 1.5
            elif rsi_val > 70:
                tech_score -= 2.0

            # 5-day momentum
            if idx >= 5 and closes[idx - 5] > 0:
                ret_5d = (c / closes[idx - 5] - 1) * 100
                if 0 < ret_5d <= 8:
                    tech_score += 1.0
                elif ret_5d < -5:
                    tech_score += 1.5  # mean reversion opportunity

            # Volume surge
            volumes = sd["volume"]
            if idx >= 21:
                avg_vol = sum(volumes[idx - 20:idx]) / 20
                if avg_vol > 0:
                    vr = volumes[idx] / avg_vol
                    if 1.2 <= vr <= 3.0:
                        tech_score += 0.5

            tech_score = max(0.0, min(10.0, tech_score))

        # Blend
        final = w_cn * cn_score + w_ml * ml_score + w_tech * tech_score
        return final

    # ── Backtest ─────────────────────────────────────────────────

    def backtest(
        self,
        dna: UnifiedDNA,
        data: Dict[str, Dict[str, Any]],
        ml_model: Optional[Any] = None,
        sample_size: int = 200,
    ) -> Dict[str, Any]:
        """Full backtest with A-share rules.

        Rules:
        - T+1: can't sell on buy day
        - Limit up (涨停): can't buy if open at limit
        - Limit down (跌停): can't sell if at limit down
        - 0.1% commission (round trip)
        """
        if not data:
            return self._empty_backtest(dna)

        codes = list(data.keys())
        if len(codes) > sample_size:
            codes = self.rng.sample(codes, sample_size)

        initial_capital = 1_000_000.0
        capital = initial_capital
        portfolio_values = [capital]
        trades: List[float] = []
        gross_profit = 0.0
        gross_loss = 0.0

        hold_days = max(2, dna.hold_days)
        commission = 0.001  # 0.1% round trip

        # Determine total days from first stock
        first_code = codes[0]
        total_days = len(data[first_code]["close"])

        day = 60  # warmup period for Alpha158 (needs 60 days)

        while day < total_days - hold_days - 1:
            scored: List[Tuple[str, float]] = []
            for code in codes:
                sd = data[code]
                if day >= len(sd["close"]):
                    continue
                s = self.score_stock(sd, day, dna, ml_model)
                if s >= dna.min_score:
                    scored.append((code, s))

            scored.sort(key=lambda x: x[1], reverse=True)
            picks = scored[:dna.max_positions]

            if picks:
                per_pos = capital / len(picks)
                for code, _score in picks:
                    sd = data[code]
                    entry_day = day + 1  # T+1

                    if entry_day >= len(sd["open"]):
                        continue

                    entry_price = sd["open"][entry_day]
                    if entry_price <= 0:
                        continue

                    # Check limit-up on entry (can't buy)
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

                    shares = per_pos / entry_price
                    exit_price = entry_price

                    for d in range(entry_day + 1, min(entry_day + hold_days, len(sd["close"]))):
                        lo = sd["low"][d]
                        hi = sd["high"][d]

                        # Check limit-down (can't sell)
                        if d >= 1:
                            pc = sd["close"][d - 1]
                            if pc > 0:
                                code_str = code.replace("_", ".")
                                if code_str.startswith("sh.688") or code_str.startswith("sz.3"):
                                    lim = 0.20
                                else:
                                    lim = 0.10
                                limit_down = pc * (1 - lim + 0.005)
                                if sd["close"][d] <= limit_down and d < entry_day + hold_days - 1:
                                    continue

                        # Stop loss
                        sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                        if lo <= sl_price:
                            exit_price = sl_price
                            break

                        # Take profit
                        tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                        if hi >= tp_price:
                            exit_price = tp_price
                            break

                        exit_price = sd["close"][d]

                    # Apply commission
                    trade_return = (exit_price - entry_price) / entry_price - commission
                    trades.append(trade_return * 100)

                    pnl = shares * exit_price - shares * entry_price - shares * entry_price * commission
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

                    capital += pnl

            portfolio_values.append(max(capital, 0.01))
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
            trading_days_used = total_days - 60
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

        # Sharpe ratio
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
                periods_per_year = 250 / max(hold_days, 1)
                sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

        calmar = annual_return / max(max_drawdown, 1.0)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
            10.0 if gross_profit > 0 else 0.0
        )
        fitness = self._compute_fitness(annual_return, max_drawdown, win_rate, sharpe, total_trades)

        return {
            "dna": dna.to_dict(),
            "annual_return": round(annual_return, 4),
            "max_drawdown": round(max_drawdown, 4),
            "win_rate": round(win_rate, 4),
            "sharpe": round(sharpe, 4),
            "calmar": round(calmar, 4),
            "total_trades": total_trades,
            "profit_factor": round(profit_factor, 4),
            "fitness": round(fitness, 4),
        }

    def _empty_backtest(self, dna: UnifiedDNA) -> Dict[str, Any]:
        return {
            "dna": dna.to_dict(),
            "annual_return": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "sharpe": 0.0,
            "calmar": 0.0,
            "total_trades": 0,
            "profit_factor": 0.0,
            "fitness": 0.0,
        }

    @staticmethod
    def _compute_fitness(
        annual_return: float, max_drawdown: float,
        win_rate: float, sharpe: float, total_trades: int,
    ) -> float:
        """Compute composite fitness (from auto_evolve.py)."""
        dd_denom = max(max_drawdown, 5.0)
        win_factor = math.sqrt(max(win_rate, 0.0))
        sharpe_bonus = 1.0 + max(sharpe, 0.0) * 0.2
        if total_trades < 10:
            trade_penalty = 0.1
        elif total_trades < 30:
            trade_penalty = total_trades / 30.0
        else:
            trade_penalty = 1.0
        return annual_return * win_factor / dd_denom * sharpe_bonus * trade_penalty

    # ── Mutation & Crossover ─────────────────────────────────────

    def mutate(self, dna: UnifiedDNA) -> UnifiedDNA:
        """Create a mutated copy of DNA."""
        d = dna.to_dict()
        for param, (lo, hi, is_int) in _PARAM_RANGES.items():
            if param not in d:
                continue
            if self.rng.random() < self.mutation_rate:
                val = d[param]
                pct = self.rng.uniform(0.10, 0.30)
                direction = self.rng.choice([-1, 1])
                delta = val * pct * direction
                if abs(delta) < 0.01:
                    delta = 0.01 * direction
                new_val = val + delta
                new_val = max(lo, min(hi, new_val))
                if is_int:
                    new_val = int(round(new_val))
                d[param] = new_val

        # Normalize source weights
        sw_sum = sum(d.get(k, 0) for k in _SOURCE_WEIGHT_KEYS)
        if sw_sum > 0:
            for k in _SOURCE_WEIGHT_KEYS:
                d[k] = round(d.get(k, 0) / sw_sum, 4)

        # Normalize signal weights
        sig_sum = sum(d.get(k, 0) for k in _CN_SIGNAL_KEYS)
        if sig_sum > 0:
            for k in _CN_SIGNAL_KEYS:
                d[k] = round(d.get(k, 0) / sig_sum, 4)

        return UnifiedDNA.from_dict(d)

    def crossover(self, dna1: UnifiedDNA, dna2: UnifiedDNA) -> UnifiedDNA:
        """Combine two DNAs by randomly picking params from each parent."""
        d1 = dna1.to_dict()
        d2 = dna2.to_dict()
        child = {}
        for key in d1:
            child[key] = d1[key] if self.rng.random() < 0.5 else d2[key]

        # Normalize weights
        sw_sum = sum(child.get(k, 0) for k in _SOURCE_WEIGHT_KEYS)
        if sw_sum > 0:
            for k in _SOURCE_WEIGHT_KEYS:
                child[k] = round(child.get(k, 0) / sw_sum, 4)

        sig_sum = sum(child.get(k, 0) for k in _CN_SIGNAL_KEYS)
        if sig_sum > 0:
            for k in _CN_SIGNAL_KEYS:
                child[k] = round(child.get(k, 0) / sig_sum, 4)

        return UnifiedDNA.from_dict(child)

    # ── Evolution Loop ───────────────────────────────────────────

    def evolve(
        self,
        generations: int = 100,
        population: int = 30,
        use_ml: bool = True,
        save_interval: int = 10,
    ) -> List[Dict[str, Any]]:
        """Main evolution loop.

        Starts from best_dna, mutates, evaluates, selects.

        Args:
            generations: number of generations to run
            population: population size per generation
            use_ml: whether to train and use ML model (slower but better)
            save_interval: save results every N generations
        """
        self.population_size = population

        print("=" * 60)
        print("🦀 Unified Evolution System")
        print("=" * 60)

        t0 = time.time()
        print("Loading elite stock pool...", flush=True)
        data = self.load_elite_pool()
        print(f"Loaded {len(data)} stocks in {time.time() - t0:.1f}s")

        if not data:
            print("ERROR: No data loaded.")
            return []

        # Train ML model (optional)
        ml_model = None
        if use_ml:
            print("Training ML model (GBM on Alpha158 features)...", flush=True)
            t1 = time.time()
            ml_model = self.train_ml_model(data, self.best_dna)
            if ml_model:
                print(f"ML model trained in {time.time() - t1:.1f}s")
            else:
                print("ML model training failed, proceeding without ML")

        # Load or create initial population
        parents = self._load_parents()
        start_gen = self._load_start_gen()
        if parents:
            print(f"Resuming from gen {start_gen} with {len(parents)} elites")
        else:
            parents = [self.best_dna]
            start_gen = 0
            print("Starting fresh with best DNA")

        print(f"Pop: {population} | Elite: {self.elite_count} | "
              f"Mutation: {self.mutation_rate}")
        print(f"Sources: cn_scanner={self.best_dna.w_cn_scanner:.0%} "
              f"ML={self.best_dna.w_ml:.0%} "
              f"Technical={self.best_dna.w_technical:.0%}")
        print("-" * 60)

        best_results: List[Dict[str, Any]] = []

        for gen in range(start_gen, start_gen + generations):
            gen_t0 = time.time()

            # Generate candidates
            candidates: List[UnifiedDNA] = list(parents)
            while len(candidates) < population:
                parent = self.rng.choice(parents)
                if self.rng.random() < 0.7:
                    child = self.mutate(parent)
                else:
                    other = self.rng.choice(parents)
                    child = self.crossover(parent, other)
                    child = self.mutate(child)
                candidates.append(child)

            # Evaluate
            results = [self.backtest(dna, data, ml_model) for dna in candidates]
            results.sort(key=lambda r: r["fitness"], reverse=True)
            best_results = results[:self.elite_count]

            best = best_results[0]
            gen_time = time.time() - gen_t0

            print(
                f"Gen {gen:4d} | "
                f"fitness={best['fitness']:8.2f} | "
                f"return={best['annual_return']:7.2f}% | "
                f"dd={best['max_drawdown']:5.2f}% | "
                f"wr={best['win_rate']:5.1f}% | "
                f"sharpe={best['sharpe']:5.2f} | "
                f"trades={best['total_trades']:4d} | "
                f"{gen_time:.1f}s"
            )

            parents = [UnifiedDNA.from_dict(r["dna"]) for r in best_results]

            if (gen + 1) % save_interval == 0 or gen == start_gen + generations - 1:
                self._save_results(gen, best_results)

        total_time = time.time() - t0
        print("-" * 60)
        print(f"Evolution complete! {generations} gens in {total_time:.1f}s")
        if best_results:
            print(f"Best fitness: {best_results[0]['fitness']:.4f}")
        print("=" * 60)

        return best_results

    # ── Persistence ──────────────────────────────────────────────

    def _save_results(self, gen: int, results: List[Dict[str, Any]]) -> None:
        payload = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "system": "unified_evolution",
            "results": results,
        }
        latest = os.path.join(self.results_dir, "latest.json")
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        versioned = os.path.join(self.results_dir, f"gen_{gen:04d}.json")
        with open(versioned, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _load_parents(self) -> List[UnifiedDNA]:
        latest = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(latest):
            return []
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("system") != "unified_evolution":
                return []
            return [UnifiedDNA.from_dict(r["dna"]) for r in data.get("results", [])]
        except Exception:
            return []

    def _load_start_gen(self) -> int:
        latest = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(latest):
            return 0
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("system") != "unified_evolution":
                return 0
            return data.get("generation", 0) + 1
        except Exception:
            return 0
