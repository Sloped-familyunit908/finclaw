"""
ML-Based A-Share Stock Scorer
==============================
Uses scikit-learn's HistGradientBoostingClassifier (sklearn's native LightGBM)
for walk-forward trained stock selection.

Based on Microsoft Qlib research: gradient boosting is the best model
for A-share alpha.

Version history:
  v1 — 20 features, single HistGBM, binary label (return > 2%)
  v2 — 40+ features, ensemble of 3 models, risk-adjusted labels,
       expanding window, feature importance analysis
"""

from __future__ import annotations

import numpy as np
from typing import Optional

# Default ML version — v2 is enhanced, v1 is legacy
DEFAULT_ML_VERSION = "v2"


# ── Feature Engineering ──────────────────────────────────────────────

def compute_features(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    version: str = DEFAULT_ML_VERSION,
) -> np.ndarray | None:
    """Compute technical features for a single stock at the last bar.

    Returns a 1-D feature vector or ``None`` if insufficient data.
    """
    if len(close) < 30:
        return None

    features = compute_features_series(close, volume, open_, high, low, version=version)
    if features is None:
        return None

    # Return last row (most recent date)
    last = features[-1]
    if np.any(np.isnan(last)):
        return None
    return last


def compute_features_series(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    version: str = DEFAULT_ML_VERSION,
) -> np.ndarray | None:
    """Compute feature matrix for all bars.  Shape: (n_bars, n_features).

    Returns ``None`` if data is too short.

    Parameters
    ----------
    version : str
        ``"v1"`` for original 20 features, ``"v2"`` for enhanced 40+ features.
    """
    if version == "v1":
        return _compute_features_v1(close, volume, open_, high, low)
    return _compute_features_v2(close, volume, open_, high, low)


def _compute_features_v1(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
) -> np.ndarray | None:
    """Original v1 features — 20 technical indicators."""
    from src.ta import rsi as calc_rsi, macd as calc_macd, bollinger_bands, sma, ema, atr, adx, obv

    n = len(close)
    if n < 30:
        return None

    close = np.asarray(close, dtype=np.float64)

    # Synthesize OHLCV if missing
    if open_ is None:
        open_ = np.copy(close)
        open_[1:] = close[:-1]
    else:
        open_ = np.asarray(open_, dtype=np.float64)

    if high is None:
        high = np.copy(close)
    else:
        high = np.asarray(high, dtype=np.float64)

    if low is None:
        low = np.copy(close)
    else:
        low = np.asarray(low, dtype=np.float64)

    if volume is not None:
        volume = np.asarray(volume, dtype=np.float64)

    # ── Compute raw indicators ───────────────────────────────────
    rsi14 = calc_rsi(close, 14)
    rsi7 = calc_rsi(close, 7)
    macd_line, macd_signal, macd_hist = calc_macd(close)
    macd_dist = macd_line - macd_signal
    bb = bollinger_bands(close)
    pct_b = bb['pct_b']
    bandwidth = bb['bandwidth']

    # Returns
    ret1 = np.full(n, np.nan)
    ret3 = np.full(n, np.nan)
    ret5 = np.full(n, np.nan)
    ret10 = np.full(n, np.nan)
    ret20 = np.full(n, np.nan)
    for i in range(1, n):
        ret1[i] = close[i] / close[i - 1] - 1
    for i in range(3, n):
        ret3[i] = close[i] / close[i - 3] - 1
    for i in range(5, n):
        ret5[i] = close[i] / close[i - 5] - 1
    for i in range(10, n):
        ret10[i] = close[i] / close[i - 10] - 1
    for i in range(20, n):
        ret20[i] = close[i] / close[i - 20] - 1

    # Volume ratio
    vol_ratio = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        vol_avg20 = sma(volume, 20)
        vol_ratio = np.where(
            (vol_avg20 > 0) & ~np.isnan(vol_avg20),
            volume / vol_avg20,
            np.nan,
        )

    # ATR
    atr_val = atr(high, low, close, 14)
    atr_pct = np.where(close > 0, atr_val / close, np.nan)

    # MA distances from price
    ma5 = sma(close, 5)
    ma10 = sma(close, 10)
    ma20 = sma(close, 20)
    ma5_dist = np.where(ma5 > 0, (close - ma5) / ma5, np.nan)
    ma10_dist = np.where(ma10 > 0, (close - ma10) / ma10, np.nan)
    ma20_dist = np.where(ma20 > 0, (close - ma20) / ma20, np.nan)

    # ADX
    adx_val = adx(high, low, close, 14)

    # OBV trend: slope of OBV over last 10 bars (normalized)
    obv_trend = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        obv_val = obv(close, volume)
        for i in range(10, n):
            segment = obv_val[i - 9: i + 1]
            if not np.any(np.isnan(segment)):
                x = np.arange(10, dtype=np.float64)
                # linear regression slope
                x_mean = 4.5
                y_mean = np.mean(segment)
                denom = np.sum((x - x_mean) ** 2)
                if denom > 0:
                    slope = np.sum((x - x_mean) * (segment - y_mean)) / denom
                    # Normalize by mean volume
                    avg_v = np.mean(volume[i - 9: i + 1])
                    obv_trend[i] = slope / avg_v if avg_v > 0 else 0.0

    # Upper/lower shadow ratios
    body = np.abs(close - open_)
    body_safe = np.where(body < 1e-10, 1e-10, body)
    upper_shadow = high - np.maximum(close, open_)
    lower_shadow = np.minimum(close, open_) - low
    upper_ratio = upper_shadow / body_safe
    lower_ratio = lower_shadow / body_safe
    # Clip extreme values
    upper_ratio = np.clip(upper_ratio, 0, 10)
    lower_ratio = np.clip(lower_ratio, 0, 10)

    # ── Stack features ───────────────────────────────────────────
    features = np.column_stack([
        rsi14,          # 0: RSI(14)
        rsi7,           # 1: RSI(7)
        macd_hist,      # 2: MACD histogram
        macd_dist,      # 3: MACD signal distance
        pct_b,          # 4: Bollinger %B
        bandwidth,      # 5: Bollinger bandwidth
        ret1,           # 6: 1-day return
        ret3,           # 7: 3-day return
        ret5,           # 8: 5-day return
        ret10,          # 9: 10-day return
        ret20,          # 10: 20-day return
        vol_ratio,      # 11: volume ratio
        atr_pct,        # 12: ATR % of price
        ma5_dist,       # 13: MA5 distance
        ma10_dist,      # 14: MA10 distance
        ma20_dist,      # 15: MA20 distance
        adx_val,        # 16: ADX
        obv_trend,      # 17: OBV trend
        upper_ratio,    # 18: upper shadow ratio
        lower_ratio,    # 19: lower shadow ratio
    ])

    return features


def _compute_features_v2(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
) -> np.ndarray | None:
    """Enhanced v2 features — 40+ technical indicators.

    Includes all v1 features plus:
    - Momentum: ROC 5/10/20, momentum acceleration
    - Volume: volume trend, volume-price correlation, OBV momentum, A/D line
    - Volatility: realized vol 5/10/20d, vol ratio, Garman-Klass
    - Price pattern: dist from 20d high/low, range position, consecutive days, candle body
    - Cross-indicator: RSI momentum, MACD hist change, BB squeeze
    """
    from src.ta import rsi as calc_rsi, macd as calc_macd, bollinger_bands, sma, ema, atr, adx, obv

    n = len(close)
    if n < 30:
        return None

    close = np.asarray(close, dtype=np.float64)

    # Synthesize OHLCV if missing
    if open_ is None:
        open_ = np.copy(close)
        open_[1:] = close[:-1]
    else:
        open_ = np.asarray(open_, dtype=np.float64)

    if high is None:
        high = np.copy(close)
    else:
        high = np.asarray(high, dtype=np.float64)

    if low is None:
        low = np.copy(close)
    else:
        low = np.asarray(low, dtype=np.float64)

    if volume is not None:
        volume = np.asarray(volume, dtype=np.float64)

    # ════════════════════════════════════════════════════════════════
    # V1 BASE FEATURES (0-19)
    # ════════════════════════════════════════════════════════════════
    rsi14 = calc_rsi(close, 14)
    rsi7 = calc_rsi(close, 7)
    macd_line, macd_signal, macd_hist = calc_macd(close)
    macd_dist = macd_line - macd_signal
    bb = bollinger_bands(close)
    pct_b = bb['pct_b']
    bandwidth = bb['bandwidth']

    # Returns
    ret1 = np.full(n, np.nan)
    ret3 = np.full(n, np.nan)
    ret5 = np.full(n, np.nan)
    ret10 = np.full(n, np.nan)
    ret20 = np.full(n, np.nan)
    for i in range(1, n):
        ret1[i] = close[i] / close[i - 1] - 1
    for i in range(3, n):
        ret3[i] = close[i] / close[i - 3] - 1
    for i in range(5, n):
        ret5[i] = close[i] / close[i - 5] - 1
    for i in range(10, n):
        ret10[i] = close[i] / close[i - 10] - 1
    for i in range(20, n):
        ret20[i] = close[i] / close[i - 20] - 1

    # Volume ratio (current vol / 20d avg vol)
    vol_ratio = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        vol_avg20 = sma(volume, 20)
        vol_ratio = np.where(
            (vol_avg20 > 0) & ~np.isnan(vol_avg20),
            volume / vol_avg20,
            np.nan,
        )

    # ATR
    atr_val = atr(high, low, close, 14)
    atr_pct = np.where(close > 0, atr_val / close, np.nan)

    # MA distances from price
    ma5 = sma(close, 5)
    ma10 = sma(close, 10)
    ma20 = sma(close, 20)
    ma5_dist = np.where(ma5 > 0, (close - ma5) / ma5, np.nan)
    ma10_dist = np.where(ma10 > 0, (close - ma10) / ma10, np.nan)
    ma20_dist = np.where(ma20 > 0, (close - ma20) / ma20, np.nan)

    # ADX
    adx_val = adx(high, low, close, 14)

    # OBV trend: slope of OBV over last 10 bars (normalized)
    obv_trend = np.full(n, np.nan)
    obv_val = None
    if volume is not None and len(volume) == n:
        obv_val = obv(close, volume)
        for i in range(10, n):
            segment = obv_val[i - 9: i + 1]
            if not np.any(np.isnan(segment)):
                x = np.arange(10, dtype=np.float64)
                x_mean = 4.5
                y_mean = np.mean(segment)
                denom = np.sum((x - x_mean) ** 2)
                if denom > 0:
                    slope = np.sum((x - x_mean) * (segment - y_mean)) / denom
                    avg_v = np.mean(volume[i - 9: i + 1])
                    obv_trend[i] = slope / avg_v if avg_v > 0 else 0.0

    # Upper/lower shadow ratios
    body = np.abs(close - open_)
    body_safe = np.where(body < 1e-10, 1e-10, body)
    upper_shadow = high - np.maximum(close, open_)
    lower_shadow = np.minimum(close, open_) - low
    upper_ratio = upper_shadow / body_safe
    lower_ratio = lower_shadow / body_safe
    upper_ratio = np.clip(upper_ratio, 0, 10)
    lower_ratio = np.clip(lower_ratio, 0, 10)

    # ════════════════════════════════════════════════════════════════
    # V2 NEW FEATURES (20+)
    # ════════════════════════════════════════════════════════════════

    # ── Momentum features ────────────────────────────────────────
    # Rate of change (ROC) — percentage change over N bars
    roc5 = np.full(n, np.nan)
    roc10 = np.full(n, np.nan)
    roc20 = np.full(n, np.nan)
    for i in range(5, n):
        roc5[i] = (close[i] / close[i - 5] - 1) * 100 if close[i - 5] > 0 else np.nan
    for i in range(10, n):
        roc10[i] = (close[i] / close[i - 10] - 1) * 100 if close[i - 10] > 0 else np.nan
    for i in range(20, n):
        roc20[i] = (close[i] / close[i - 20] - 1) * 100 if close[i - 20] > 0 else np.nan

    # Momentum acceleration: ret5 - ret10
    momentum_accel = ret5 - ret10  # NaN propagates naturally

    # ── Volume features ──────────────────────────────────────────
    # Volume trend: 5-day avg vol / 20-day avg vol
    vol_trend = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        vol_avg5 = sma(volume, 5)
        vol_avg20_v2 = sma(volume, 20)
        vol_trend = np.where(
            (vol_avg20_v2 > 0) & ~np.isnan(vol_avg5) & ~np.isnan(vol_avg20_v2),
            vol_avg5 / vol_avg20_v2,
            np.nan,
        )

    # Volume-price correlation: 5-day rolling correlation of price change and volume
    vol_price_corr = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        for i in range(5, n):
            price_changes = np.diff(close[i - 5: i + 1])  # 5 price changes
            vol_window = volume[i - 4: i + 1]  # 5 volume values (aligned)
            if len(price_changes) == 5 and len(vol_window) == 5:
                if np.std(price_changes) > 1e-10 and np.std(vol_window) > 1e-10:
                    corr = np.corrcoef(price_changes, vol_window)[0, 1]
                    vol_price_corr[i] = corr if not np.isnan(corr) else 0.0
                else:
                    vol_price_corr[i] = 0.0

    # OBV momentum: OBV_5ma - OBV_20ma
    obv_momentum = np.full(n, np.nan)
    if obv_val is not None:
        obv_5ma = sma(obv_val, 5)
        obv_20ma = sma(obv_val, 20)
        for i in range(n):
            if not np.isnan(obv_5ma[i]) and not np.isnan(obv_20ma[i]):
                # Normalize by 20ma magnitude to keep values reasonable
                denom = abs(obv_20ma[i]) if abs(obv_20ma[i]) > 1e-10 else 1e-10
                obv_momentum[i] = (obv_5ma[i] - obv_20ma[i]) / denom

    # Accumulation/Distribution line
    ad_line = np.full(n, np.nan)
    if volume is not None and len(volume) == n:
        hl_range = high - low
        mfm = np.where(hl_range > 1e-10,
                        ((close - low) - (high - close)) / hl_range,
                        0.0)
        mfv = mfm * volume
        ad_line[0] = mfv[0]
        for i in range(1, n):
            ad_line[i] = ad_line[i - 1] + mfv[i]
        # Normalize A/D line by rolling std to keep bounded
        ad_std = np.nanstd(ad_line[:min(n, 20)])
        if ad_std > 1e-10:
            ad_line = ad_line / ad_std

    # ── Volatility features ──────────────────────────────────────
    # Realized volatility: rolling std of daily returns
    daily_ret = np.full(n, np.nan)
    for i in range(1, n):
        daily_ret[i] = close[i] / close[i - 1] - 1

    rvol_5 = np.full(n, np.nan)
    rvol_10 = np.full(n, np.nan)
    rvol_20 = np.full(n, np.nan)
    for i in range(5, n):
        window = daily_ret[i - 4: i + 1]
        if not np.any(np.isnan(window)):
            rvol_5[i] = np.std(window, ddof=1)
    for i in range(10, n):
        window = daily_ret[i - 9: i + 1]
        if not np.any(np.isnan(window)):
            rvol_10[i] = np.std(window, ddof=1)
    for i in range(20, n):
        window = daily_ret[i - 19: i + 1]
        if not np.any(np.isnan(window)):
            rvol_20[i] = np.std(window, ddof=1)

    # Volatility ratio: vol_5d / vol_20d (expansion/contraction)
    vol_ratio_5_20 = np.where(
        (~np.isnan(rvol_5)) & (~np.isnan(rvol_20)) & (rvol_20 > 1e-10),
        rvol_5 / rvol_20,
        np.nan,
    )

    # Garman-Klass volatility (using OHLC)
    gk_vol = np.full(n, np.nan)
    for i in range(20, n):
        gk_sum = 0.0
        valid = 0
        for j in range(i - 19, i + 1):
            hl = high[j] / low[j] if low[j] > 0 else 1.0
            co = close[j] / open_[j] if open_[j] > 0 else 1.0
            if hl > 0 and co > 0:
                gk_sum += 0.5 * np.log(hl) ** 2 - (2 * np.log(2) - 1) * np.log(co) ** 2
                valid += 1
        if valid > 0:
            val = gk_sum / valid
            gk_vol[i] = np.sqrt(max(val, 0.0))  # guard against negative from float precision

    # ── Price pattern features ───────────────────────────────────
    # Distance from 20d high (0-1)
    dist_20d_high = np.full(n, np.nan)
    dist_20d_low = np.full(n, np.nan)
    range_position = np.full(n, np.nan)
    for i in range(20, n):
        h20 = np.max(high[i - 19: i + 1])
        l20 = np.min(low[i - 19: i + 1])
        if h20 > 0:
            dist_20d_high[i] = (h20 - close[i]) / h20
        if l20 > 0:
            dist_20d_low[i] = (close[i] - l20) / l20 if l20 > 0 else np.nan
        hl_range = h20 - l20
        if hl_range > 1e-10:
            range_position[i] = (close[i] - l20) / hl_range
        else:
            range_position[i] = 0.5

    # Consecutive up/down days count (positive = up days, negative = down days)
    consec_days = np.full(n, np.nan)
    if n > 1:
        consec_days[0] = 0.0
        for i in range(1, n):
            if close[i] > close[i - 1]:
                prev = consec_days[i - 1] if not np.isnan(consec_days[i - 1]) else 0.0
                consec_days[i] = max(prev, 0) + 1
            elif close[i] < close[i - 1]:
                prev = consec_days[i - 1] if not np.isnan(consec_days[i - 1]) else 0.0
                consec_days[i] = min(prev, 0) - 1
            else:
                consec_days[i] = 0.0

    # Average candle body size (5d) — normalized by price
    avg_body_5d = np.full(n, np.nan)
    for i in range(5, n):
        bodies = np.abs(close[i - 4: i + 1] - open_[i - 4: i + 1])
        avg_price = np.mean(close[i - 4: i + 1])
        if avg_price > 0:
            avg_body_5d[i] = np.mean(bodies) / avg_price

    # ── Cross-indicator features ─────────────────────────────────
    # RSI momentum: RSI(7) - RSI(14)
    rsi_momentum = rsi7 - rsi14  # NaN propagates naturally

    # MACD histogram change: hist[i] - hist[i-1]
    macd_hist_change = np.full(n, np.nan)
    for i in range(1, n):
        if not np.isnan(macd_hist[i]) and not np.isnan(macd_hist[i - 1]):
            macd_hist_change[i] = macd_hist[i] - macd_hist[i - 1]

    # BB squeeze indicator: bandwidth / avg_bandwidth_20
    bb_squeeze = np.full(n, np.nan)
    for i in range(39, n):  # need 20 valid bandwidth values (bandwidth starts at idx 19)
        bw_window = bandwidth[i - 19: i + 1]
        valid_bw = bw_window[~np.isnan(bw_window)]
        if len(valid_bw) >= 10:
            avg_bw_val = np.mean(valid_bw)
            if avg_bw_val > 1e-10 and not np.isnan(bandwidth[i]):
                bb_squeeze[i] = bandwidth[i] / avg_bw_val

    # ── Stack ALL features ───────────────────────────────────────
    features = np.column_stack([
        # V1 features (0-19)
        rsi14,              # 0
        rsi7,               # 1
        macd_hist,          # 2
        macd_dist,          # 3
        pct_b,              # 4
        bandwidth,          # 5
        ret1,               # 6
        ret3,               # 7
        ret5,               # 8
        ret10,              # 9
        ret20,              # 10
        vol_ratio,          # 11
        atr_pct,            # 12
        ma5_dist,           # 13
        ma10_dist,          # 14
        ma20_dist,          # 15
        adx_val,            # 16
        obv_trend,          # 17
        upper_ratio,        # 18
        lower_ratio,        # 19
        # V2 momentum features (20-23)
        roc5,               # 20
        roc10,              # 21
        roc20,              # 22
        momentum_accel,     # 23
        # V2 volume features (24-27)
        vol_trend,          # 24
        vol_price_corr,     # 25
        obv_momentum,       # 26
        ad_line,            # 27
        # V2 volatility features (28-32)
        rvol_5,             # 28
        rvol_10,            # 29
        rvol_20,            # 30
        vol_ratio_5_20,     # 31
        gk_vol,             # 32
        # V2 price pattern features (33-37)
        dist_20d_high,      # 33
        dist_20d_low,       # 34
        range_position,     # 35
        consec_days,        # 36
        avg_body_5d,        # 37
        # V2 cross-indicator features (38-40)
        rsi_momentum,       # 38
        macd_hist_change,   # 39
        bb_squeeze,         # 40
    ])

    return features


# ── Feature Name Lists ───────────────────────────────────────────────

FEATURE_NAMES_V1 = [
    "rsi14", "rsi7", "macd_hist", "macd_dist", "pct_b", "bandwidth",
    "ret1", "ret3", "ret5", "ret10", "ret20", "vol_ratio",
    "atr_pct", "ma5_dist", "ma10_dist", "ma20_dist", "adx",
    "obv_trend", "upper_shadow_ratio", "lower_shadow_ratio",
]

FEATURE_NAMES_V2 = FEATURE_NAMES_V1 + [
    # Momentum
    "roc5", "roc10", "roc20", "momentum_accel",
    # Volume
    "vol_trend", "vol_price_corr", "obv_momentum", "ad_line",
    # Volatility
    "rvol_5d", "rvol_10d", "rvol_20d", "vol_ratio_5_20", "gk_vol",
    # Price pattern
    "dist_20d_high", "dist_20d_low", "range_position", "consec_days", "avg_body_5d",
    # Cross-indicator
    "rsi_momentum", "macd_hist_change", "bb_squeeze",
]

# Legacy aliases for backward compatibility
FEATURE_NAMES = FEATURE_NAMES_V2
NUM_FEATURES = len(FEATURE_NAMES_V2)

NUM_FEATURES_V2 = len(FEATURE_NAMES_V2)


def get_feature_names(version: str = DEFAULT_ML_VERSION) -> list[str]:
    """Get feature names for the given version."""
    if version == "v1":
        return FEATURE_NAMES_V1
    return FEATURE_NAMES_V2


def get_num_features(version: str = DEFAULT_ML_VERSION) -> int:
    """Get feature count for the given version."""
    if version == "v1":
        return NUM_FEATURES
    return NUM_FEATURES_V2


# ── Label Generation ─────────────────────────────────────────────────

def compute_labels(close: np.ndarray, forward_days: int = 5, threshold: float = 0.02) -> np.ndarray:
    """Compute binary labels: 1 if N-day forward return > threshold, else 0.

    The last *forward_days* bars will have NaN labels.
    """
    n = len(close)
    labels = np.full(n, np.nan)
    for i in range(n - forward_days):
        fwd_ret = close[i + forward_days] / close[i] - 1
        labels[i] = 1.0 if fwd_ret > threshold else 0.0
    return labels


def compute_labels_v2(
    close: np.ndarray,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    forward_days: int = 5,
    threshold: float = 0.02,
    max_drawdown_pct: float = 0.03,
) -> np.ndarray:
    """Enhanced label generation with risk-adjusted returns and drawdown filtering.

    A bar is labeled positive (1.0) only if:
    1. Forward return > threshold
    2. Max intra-period drawdown < max_drawdown_pct

    The last *forward_days* bars will have NaN labels.
    """
    n = len(close)
    labels = np.full(n, np.nan)

    # If no high/low, fall back to close-only
    use_intraday = (high is not None and low is not None
                    and len(high) == n and len(low) == n)

    for i in range(n - forward_days):
        fwd_ret = close[i + forward_days] / close[i] - 1

        if fwd_ret <= threshold:
            labels[i] = 0.0
            continue

        # Check max drawdown during holding period
        entry_price = close[i]
        max_dd = 0.0
        if use_intraday:
            for j in range(i + 1, i + forward_days + 1):
                low_dd = (low[j] / entry_price) - 1
                max_dd = min(max_dd, low_dd)
        else:
            for j in range(i + 1, i + forward_days + 1):
                dd = (close[j] / entry_price) - 1
                max_dd = min(max_dd, dd)

        # If drawdown exceeds limit, label as negative despite positive return
        if max_dd < -max_drawdown_pct:
            labels[i] = 0.0
        else:
            labels[i] = 1.0

    return labels


# ── Walk-Forward Trainer ─────────────────────────────────────────────

class MLStockScorer:
    """Walk-forward ML scorer using HistGradientBoostingClassifier.

    Training: past *train_bars* bars → predict next *predict_bars* window,
    then roll forward.
    """

    def __init__(
        self,
        train_bars: int = 120,  # ~6 months
        predict_bars: int = 20,  # ~1 month
        forward_days: int = 5,
        threshold: float = 0.02,
        version: str = DEFAULT_ML_VERSION,
        expanding_window: bool = False,
    ):
        self.train_bars = train_bars
        self.predict_bars = predict_bars
        self.forward_days = forward_days
        self.threshold = threshold
        self.version = version
        self.expanding_window = expanding_window
        self._model = None
        self._feature_importances: np.ndarray | None = None
        self._ensemble_models: list | None = None

    def train_and_predict(
        self,
        features: np.ndarray,
        close: np.ndarray,
        high: np.ndarray | None = None,
        low: np.ndarray | None = None,
        verbose: bool = False,
    ) -> np.ndarray:
        """Walk-forward train/predict.

        Parameters
        ----------
        features : np.ndarray
            Shape (n_bars, n_features).
        close : np.ndarray
            Shape (n_bars,).
        high : np.ndarray, optional
            High prices for v2 label generation.
        low : np.ndarray, optional
            Low prices for v2 label generation.
        verbose : bool
            Print training progress.

        Returns
        -------
        np.ndarray
            Probability of positive forward return for each bar.
            Bars without a prediction are ``np.nan``.
        """
        if self.version == "v2":
            return self._train_and_predict_v2(features, close, high, low, verbose)
        return self._train_and_predict_v1(features, close, verbose)

    def _train_and_predict_v1(
        self, features: np.ndarray, close: np.ndarray, verbose: bool = False,
    ) -> np.ndarray:
        """Original v1 walk-forward training with single HistGBM."""
        from sklearn.ensemble import HistGradientBoostingClassifier

        n = len(features)
        labels = compute_labels(close, self.forward_days, self.threshold)
        probs = np.full(n, np.nan)

        start = self.train_bars
        step = 0
        while start + self.predict_bars <= n:
            train_end = start
            pred_end = min(start + self.predict_bars, n)

            # Build training set
            X_train = features[start - self.train_bars: train_end]
            y_train = labels[start - self.train_bars: train_end]

            # Remove NaN rows
            valid_mask = ~(np.any(np.isnan(X_train), axis=1) | np.isnan(y_train))
            X_train_clean = X_train[valid_mask]
            y_train_clean = y_train[valid_mask]

            if len(X_train_clean) < 20 or len(np.unique(y_train_clean)) < 2:
                start += self.predict_bars
                continue

            model = HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=5,
                learning_rate=0.1,
                min_samples_leaf=10,
                random_state=42,
            )
            model.fit(X_train_clean, y_train_clean)

            X_pred = features[train_end: pred_end]
            valid_pred = ~np.any(np.isnan(X_pred), axis=1)
            if np.any(valid_pred):
                this_probs = np.full(pred_end - train_end, np.nan)
                this_probs[valid_pred] = model.predict_proba(X_pred[valid_pred])[:, 1]
                probs[train_end: pred_end] = this_probs

            self._model = model
            step += 1
            if verbose:
                print(f"  [v1] Step {step}: trained on [{start - self.train_bars}:{train_end}], "
                      f"predict [{train_end}:{pred_end}]")
            start += self.predict_bars

        return probs

    def _train_and_predict_v2(
        self,
        features: np.ndarray,
        close: np.ndarray,
        high: np.ndarray | None = None,
        low: np.ndarray | None = None,
        verbose: bool = False,
    ) -> np.ndarray:
        """Enhanced v2 walk-forward training with ensemble and risk-adjusted labels."""
        from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

        n = len(features)
        # Use enhanced labels if high/low available
        if high is not None and low is not None:
            labels = compute_labels_v2(close, high, low,
                                       self.forward_days, self.threshold)
        else:
            labels = compute_labels_v2(close, forward_days=self.forward_days,
                                       threshold=self.threshold)

        probs = np.full(n, np.nan)
        all_importances = []

        start = self.train_bars
        step = 0
        while start + self.predict_bars <= n:
            train_end = start
            pred_end = min(start + self.predict_bars, n)

            # Build training set — expanding window or fixed
            if self.expanding_window:
                train_start = 0
            else:
                train_start = start - self.train_bars

            X_train = features[train_start: train_end]
            y_train = labels[train_start: train_end]

            # Remove NaN rows
            valid_mask = ~(np.any(np.isnan(X_train), axis=1) | np.isnan(y_train))
            X_train_clean = X_train[valid_mask]
            y_train_clean = y_train[valid_mask]

            if len(X_train_clean) < 20 or len(np.unique(y_train_clean)) < 2:
                start += self.predict_bars
                continue

            # ── Ensemble of 3 models ─────────────────────────────
            model_a = HistGradientBoostingClassifier(
                max_iter=200,
                max_depth=3,
                learning_rate=0.05,
                min_samples_leaf=10,
                l2_regularization=0.1,
                max_leaf_nodes=31,
                random_state=42,
            )
            model_b = HistGradientBoostingClassifier(
                max_iter=200,
                max_depth=7,
                learning_rate=0.05,
                min_samples_leaf=10,
                l2_regularization=0.1,
                max_leaf_nodes=31,
                random_state=42,
            )
            model_c = RandomForestClassifier(
                n_estimators=100,
                max_depth=7,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=1,
            )

            model_a.fit(X_train_clean, y_train_clean)
            model_b.fit(X_train_clean, y_train_clean)
            model_c.fit(X_train_clean, y_train_clean)

            ensemble = [model_a, model_b, model_c]

            # Predict next window — average probabilities
            X_pred = features[train_end: pred_end]
            valid_pred = ~np.any(np.isnan(X_pred), axis=1)
            if np.any(valid_pred):
                this_probs = np.full(pred_end - train_end, np.nan)
                X_valid = X_pred[valid_pred]
                # Average predictions from all 3 models
                ensemble_probs = np.zeros(X_valid.shape[0])
                for m in ensemble:
                    ensemble_probs += m.predict_proba(X_valid)[:, 1]
                ensemble_probs /= len(ensemble)
                this_probs[valid_pred] = ensemble_probs
                probs[train_end: pred_end] = this_probs

            # Track feature importances from HistGBM model A
            # (HistGBM doesn't have feature_importances_ by default in all versions)
            try:
                # Use permutation importance proxy: use model_a's splitting stats
                # HistGBM stores n_iter_ but not always feature_importances_
                # RandomForest always has feature_importances_
                imp_c = model_c.feature_importances_
                all_importances.append(imp_c)
            except AttributeError:
                pass

            self._model = model_a  # keep model A for live prediction
            self._ensemble_models = ensemble
            step += 1
            if verbose:
                n_train = len(X_train_clean)
                pos = int(np.sum(y_train_clean == 1))
                neg = n_train - pos
                print(f"  [v2] Step {step}: train[{train_start}:{train_end}] "
                      f"({n_train} samples, {pos}+/{neg}-), "
                      f"predict [{train_end}:{pred_end}]")
            start += self.predict_bars

        # Aggregate feature importances
        if all_importances:
            self._feature_importances = np.mean(all_importances, axis=0)

        if verbose:
            print(f"  [v2] Walk-forward complete: {step} steps")

        return probs

    def predict_latest(self, features: np.ndarray) -> float | None:
        """Predict using the last trained model(s).

        For v2, uses ensemble averaging. For v1, uses single model.
        """
        if self.version == "v2" and self._ensemble_models:
            if np.any(np.isnan(features)):
                return None
            X = features.reshape(1, -1)
            avg_prob = 0.0
            for m in self._ensemble_models:
                avg_prob += m.predict_proba(X)[0, 1]
            avg_prob /= len(self._ensemble_models)
            return float(avg_prob)

        if self._model is None:
            return None
        if np.any(np.isnan(features)):
            return None
        prob = self._model.predict_proba(features.reshape(1, -1))[0, 1]
        return float(prob)

    def get_feature_importances(self) -> dict[str, float] | None:
        """Get feature importance dict (feature_name → importance).

        Returns None if no importances are available.
        """
        if self._feature_importances is None:
            return None
        names = get_feature_names(self.version)
        n_feat = len(self._feature_importances)
        if n_feat != len(names):
            # Fallback: use generic names
            names = [f"feature_{i}" for i in range(n_feat)]
        return {name: float(imp) for name, imp in zip(names, self._feature_importances)}


# ── Blending with Rule-Based Scores ──────────────────────────────────

def blend_scores(
    rule_score: float,
    ml_probability: float,
    rule_weight: float = 0.5,
    max_rule_score: float = 20.0,
) -> float:
    """Blend rule-based score with ML probability.

    ``final = rule_weight * (rule_score / max_rule_score) * 20
              + (1 - rule_weight) * ml_probability * 20``
    """
    rule_normalized = min(rule_score / max_rule_score, 1.0)
    final = rule_weight * rule_normalized * 20 + (1 - rule_weight) * ml_probability * 20
    return round(final, 2)


# ── ML Scoring for Scanner Integration ───────────────────────────────

def compute_score_ml(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    scorer: MLStockScorer | None = None,
    version: str = DEFAULT_ML_VERSION,
) -> dict:
    """Compute ML-blended score for a single stock.

    Uses V3 rule-based score as the base, then blends with ML probability.
    If no scorer is provided, creates a new one (slower, no walk-forward context).
    """
    from src.cn_scanner import compute_score_v3, _empty_result

    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        result = _empty_result(close)
        result["strategy"] = "ml"
        return result

    # Get V3 base score
    base = compute_score_v3(close, volume, open_, high, low)

    # Compute features (use scorer's version if available)
    feat_version = scorer.version if scorer is not None else version
    features = compute_features_series(close, volume, open_, high, low, version=feat_version)
    if features is None or len(features) < 30:
        base["strategy"] = "ml"
        return base

    # ML probability
    ml_prob = None
    if scorer is not None:
        last_feat = features[-1]
        if not np.any(np.isnan(last_feat)):
            ml_prob = scorer.predict_latest(last_feat)

    if ml_prob is None:
        # Fall back to rule-based only
        base["strategy"] = "ml"
        return base

    blended = blend_scores(base["score"], ml_prob)
    base["score"] = int(round(blended))
    base["ml_probability"] = ml_prob
    base["strategy"] = "ml"
    base["reasons"].append(f"ML prob={ml_prob:.2f}")

    # Re-classify signal using v3 thresholds
    from src.cn_scanner import classify_signal_v3
    base["signal"] = classify_signal_v3(base["score"])

    return base
