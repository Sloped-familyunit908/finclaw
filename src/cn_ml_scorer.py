"""
ML-Based A-Share Stock Scorer
==============================
Uses scikit-learn's HistGradientBoostingClassifier (sklearn's native LightGBM)
for walk-forward trained stock selection.

Based on Microsoft Qlib research: gradient boosting is the best model
for A-share alpha.
"""

from __future__ import annotations

import numpy as np
from typing import Optional


# ── Feature Engineering ──────────────────────────────────────────────

def compute_features(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
) -> np.ndarray | None:
    """Compute ~20 technical features for a single stock at the last bar.

    Returns a 1-D feature vector or ``None`` if insufficient data.
    """
    if len(close) < 30:
        return None

    features = compute_features_series(close, volume, open_, high, low)
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
) -> np.ndarray | None:
    """Compute feature matrix for all bars.  Shape: (n_bars, n_features).

    Returns ``None`` if data is too short.
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


FEATURE_NAMES = [
    "rsi14", "rsi7", "macd_hist", "macd_dist", "pct_b", "bandwidth",
    "ret1", "ret3", "ret5", "ret10", "ret20", "vol_ratio",
    "atr_pct", "ma5_dist", "ma10_dist", "ma20_dist", "adx",
    "obv_trend", "upper_shadow_ratio", "lower_shadow_ratio",
]

NUM_FEATURES = len(FEATURE_NAMES)


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
    ):
        self.train_bars = train_bars
        self.predict_bars = predict_bars
        self.forward_days = forward_days
        self.threshold = threshold
        self._model = None

    def train_and_predict(
        self,
        features: np.ndarray,
        close: np.ndarray,
    ) -> np.ndarray:
        """Walk-forward train/predict.

        Parameters
        ----------
        features : np.ndarray
            Shape (n_bars, n_features).
        close : np.ndarray
            Shape (n_bars,).

        Returns
        -------
        np.ndarray
            Probability of positive forward return for each bar.
            Bars without a prediction are ``np.nan``.
        """
        from sklearn.ensemble import HistGradientBoostingClassifier

        n = len(features)
        labels = compute_labels(close, self.forward_days, self.threshold)
        probs = np.full(n, np.nan)

        start = self.train_bars
        while start + self.predict_bars <= n:
            train_end = start
            pred_end = min(start + self.predict_bars, n)

            # Build training set: [start - train_bars, start)
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

            # Predict next window
            X_pred = features[train_end: pred_end]
            valid_pred = ~np.any(np.isnan(X_pred), axis=1)
            if np.any(valid_pred):
                this_probs = np.full(pred_end - train_end, np.nan)
                this_probs[valid_pred] = model.predict_proba(X_pred[valid_pred])[:, 1]
                probs[train_end: pred_end] = this_probs

            self._model = model  # keep last model for live prediction
            start += self.predict_bars

        return probs

    def predict_latest(self, features: np.ndarray) -> float | None:
        """Predict using the last trained model.

        Parameters
        ----------
        features : np.ndarray
            A single feature vector of shape ``(n_features,)``.

        Returns
        -------
        float or None
            Probability of positive forward return, or ``None`` if no model
            is available.
        """
        if self._model is None:
            return None
        if np.any(np.isnan(features)):
            return None
        prob = self._model.predict_proba(features.reshape(1, -1))[0, 1]
        return float(prob)


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

    # Compute features
    features = compute_features_series(close, volume, open_, high, low)
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
