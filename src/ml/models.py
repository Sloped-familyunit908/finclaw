"""
Simple ML models for financial prediction.

Provides numpy-only implementations with optional sklearn/xgboost enhancements.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


class LinearRegression:
    """Simple OLS linear regression using numpy.

    Used for factor scoring / return prediction.
    """

    def __init__(self):
        self.coefficients: Optional[np.ndarray] = None
        self.intercept: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LinearRegression":
        """Fit using normal equation: beta = (X'X)^-1 X'y."""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        # Remove rows with NaN
        mask = ~(np.any(np.isnan(X), axis=1) | np.isnan(y))
        X_clean = X[mask]
        y_clean = y[mask]
        if len(y_clean) < X_clean.shape[1] + 1:
            self.coefficients = np.zeros(X.shape[1])
            self.intercept = np.nanmean(y) if len(y) > 0 else 0.0
            return self
        # Add intercept column
        ones = np.ones((len(X_clean), 1))
        X_aug = np.hstack([ones, X_clean])
        try:
            beta = np.linalg.lstsq(X_aug, y_clean, rcond=None)[0]
            self.intercept = beta[0]
            self.coefficients = beta[1:]
        except np.linalg.LinAlgError:
            self.coefficients = np.zeros(X.shape[1])
            self.intercept = np.nanmean(y_clean)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict y values."""
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if self.coefficients is None:
            return np.zeros(len(X))
        return self.intercept + X @ self.coefficients

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """R-squared score."""
        y_pred = self.predict(X)
        y = np.asarray(y, dtype=float)
        mask = ~(np.isnan(y_pred) | np.isnan(y))
        if mask.sum() < 2:
            return 0.0
        ss_res = np.sum((y[mask] - y_pred[mask]) ** 2)
        ss_tot = np.sum((y[mask] - np.mean(y[mask])) ** 2)
        return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


class MAPredictor:
    """Moving average crossover predictor.

    Predicts +1 (bullish) when short MA > long MA, -1 otherwise.
    """

    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window

    def predict(self, prices: np.ndarray) -> np.ndarray:
        """Generate signals from price series."""
        prices = np.asarray(prices, dtype=float)
        n = len(prices)
        signals = np.zeros(n)
        for i in range(self.long_window - 1, n):
            short_ma = np.mean(prices[i - self.short_window + 1 : i + 1])
            long_ma = np.mean(prices[i - self.long_window + 1 : i + 1])
            signals[i] = 1.0 if short_ma > long_ma else -1.0
        return signals


class RegimeClassifier:
    """Naive Bayes-like regime classifier.

    Classifies market regime as bull / bear / sideways based on
    return distribution statistics.
    """

    def __init__(self, lookback: int = 63):
        self.lookback = lookback
        # Prior means and stds for each regime (rough calibration)
        self.regimes = {
            "bull": {"mean": 0.0008, "std": 0.01},
            "bear": {"mean": -0.0006, "std": 0.018},
            "sideways": {"mean": 0.0001, "std": 0.008},
        }

    def classify(self, returns: np.ndarray) -> List[str]:
        """Classify each point into a regime based on rolling stats."""
        returns = np.asarray(returns, dtype=float)
        n = len(returns)
        result = ["unknown"] * n
        for i in range(self.lookback, n):
            window = returns[i - self.lookback : i]
            valid = window[~np.isnan(window)]
            if len(valid) < 10:
                continue
            obs_mean = np.mean(valid)
            obs_std = np.std(valid, ddof=1)
            best_regime = "sideways"
            best_score = -np.inf
            for regime, params in self.regimes.items():
                # Log-likelihood proxy
                mean_diff = (obs_mean - params["mean"]) ** 2
                std_diff = (obs_std - params["std"]) ** 2
                score = -(mean_diff / 0.001 + std_diff / 0.01)
                if score > best_score:
                    best_score = score
                    best_regime = regime
            result[i] = best_regime
        return result

    def classify_numeric(self, returns: np.ndarray) -> np.ndarray:
        """Return numeric regime: +1 bull, -1 bear, 0 sideways."""
        regimes = self.classify(returns)
        mapping = {"bull": 1.0, "bear": -1.0, "sideways": 0.0, "unknown": np.nan}
        return np.array([mapping[r] for r in regimes])


class EnsembleModel:
    """Combine multiple model scores via weighted average."""

    def __init__(self, weights: Optional[List[float]] = None):
        self.weights = weights

    def combine(self, scores: List[np.ndarray]) -> np.ndarray:
        """Combine score arrays. Each array should be the same length."""
        if not scores:
            return np.array([])
        n = len(scores[0])
        weights = self.weights or [1.0 / len(scores)] * len(scores)
        if len(weights) != len(scores):
            weights = [1.0 / len(scores)] * len(scores)
        # Normalize weights
        w_sum = sum(weights)
        weights = [w / w_sum for w in weights]
        result = np.zeros(n)
        weight_sum = np.zeros(n)
        for score, w in zip(scores, weights):
            score = np.asarray(score, dtype=float)
            mask = ~np.isnan(score)
            result[mask] += w * score[mask]
            weight_sum[mask] += w
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.where(weight_sum > 0, result / weight_sum, np.nan)
        return result


# ------------------------------------------------------------------
# Optional sklearn-based models
# ------------------------------------------------------------------

class RandomForestPredictor:
    """Random Forest wrapper (requires sklearn)."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 5, random_state: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.model = None
        self._available = False
        try:
            from sklearn.ensemble import RandomForestRegressor
            self.model = RandomForestRegressor(
                n_estimators=n_estimators, max_depth=max_depth, random_state=random_state
            )
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def fit(self, X: np.ndarray, y: np.ndarray) -> "RandomForestPredictor":
        if not self._available:
            return self
        mask = ~(np.any(np.isnan(X), axis=1) | np.isnan(y))
        self.model.fit(X[mask], y[mask])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._available:
            return np.full(len(X), np.nan)
        result = np.full(len(X), np.nan)
        mask = ~np.any(np.isnan(X), axis=1)
        if mask.any():
            result[mask] = self.model.predict(X[mask])
        return result


class XGBoostPredictor:
    """XGBoost wrapper (requires xgboost)."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 4, learning_rate: float = 0.1):
        self.params = dict(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate)
        self.model = None
        self._available = False
        try:
            import xgboost as xgb
            self.model = xgb.XGBRegressor(**self.params, verbosity=0)
            self._available = True
        except ImportError:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def fit(self, X: np.ndarray, y: np.ndarray) -> "XGBoostPredictor":
        if not self._available:
            return self
        mask = ~(np.any(np.isnan(X), axis=1) | np.isnan(y))
        self.model.fit(X[mask], y[mask])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._available:
            return np.full(len(X), np.nan)
        result = np.full(len(X), np.nan)
        mask = ~np.any(np.isnan(X), axis=1)
        if mask.any():
            result[mask] = self.model.predict(X[mask])
        return result


def walk_forward_split(
    n_samples: int,
    train_size: int = 252,
    test_size: int = 21,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generate walk-forward train/test index splits.

    Slides a window: train on *train_size* samples, test on next *test_size*.
    """
    splits = []
    start = 0
    while start + train_size + test_size <= n_samples:
        train_idx = np.arange(start, start + train_size)
        test_idx = np.arange(start + train_size, start + train_size + test_size)
        splits.append((train_idx, test_idx))
        start += test_size
    return splits
