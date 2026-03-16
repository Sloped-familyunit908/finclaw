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


class DecisionTreeClassifier:
    """Pure-Python decision tree classifier using recursive binary splits.

    Parameters
    ----------
    max_depth : int
        Maximum tree depth.
    min_samples_split : int
        Minimum samples required to split an internal node.
    """

    def __init__(self, max_depth: int = 5, min_samples_split: int = 2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self._tree = None

    def fit(self, X: list, y: list) -> "DecisionTreeClassifier":
        """Fit the tree on X (list of lists) and y (list of labels)."""
        self._tree = self._build(X, y, depth=0)
        return self

    def predict(self, X: list) -> list:
        """Predict class labels for each row in X."""
        if self._tree is None:
            return [0] * len(X)
        return [self._predict_one(row, self._tree) for row in X]

    def _gini(self, y: list) -> float:
        n = len(y)
        if n == 0:
            return 0.0
        counts: dict = {}
        for v in y:
            counts[v] = counts.get(v, 0) + 1
        return 1.0 - sum((c / n) ** 2 for c in counts.values())

    def _best_split(self, X: list, y: list):
        best_feat, best_val, best_score = None, None, float("inf")
        best_left_idx, best_right_idx = [], []
        n_features = len(X[0]) if X else 0
        n = len(y)
        for feat in range(n_features):
            values = sorted(set(row[feat] for row in X))
            for i in range(len(values) - 1):
                threshold = (values[i] + values[i + 1]) / 2.0
                left_idx = [j for j in range(n) if X[j][feat] <= threshold]
                right_idx = [j for j in range(n) if X[j][feat] > threshold]
                if not left_idx or not right_idx:
                    continue
                left_y = [y[j] for j in left_idx]
                right_y = [y[j] for j in right_idx]
                score = (len(left_y) * self._gini(left_y) + len(right_y) * self._gini(right_y)) / n
                if score < best_score:
                    best_score = score
                    best_feat = feat
                    best_val = threshold
                    best_left_idx = left_idx
                    best_right_idx = right_idx
        return best_feat, best_val, best_left_idx, best_right_idx

    def _majority(self, y: list):
        counts: dict = {}
        for v in y:
            counts[v] = counts.get(v, 0) + 1
        return max(counts, key=counts.get)

    def _build(self, X: list, y: list, depth: int) -> dict:
        if depth >= self.max_depth or len(y) < self.min_samples_split or len(set(y)) == 1:
            return {"leaf": True, "value": self._majority(y)}
        feat, val, left_idx, right_idx = self._best_split(X, y)
        if feat is None:
            return {"leaf": True, "value": self._majority(y)}
        left_X = [X[i] for i in left_idx]
        left_y = [y[i] for i in left_idx]
        right_X = [X[i] for i in right_idx]
        right_y = [y[i] for i in right_idx]
        return {
            "leaf": False,
            "feature": feat,
            "threshold": val,
            "left": self._build(left_X, left_y, depth + 1),
            "right": self._build(right_X, right_y, depth + 1),
        }

    def _predict_one(self, row: list, node: dict):
        if node["leaf"]:
            return node["value"]
        if row[node["feature"]] <= node["threshold"]:
            return self._predict_one(row, node["left"])
        return self._predict_one(row, node["right"])


class RandomForestClassifier:
    """Pure-Python random forest classifier (bagging of decision trees).

    Parameters
    ----------
    n_trees : int
        Number of trees in the forest.
    max_depth : int
        Maximum depth per tree.
    sample_ratio : float
        Fraction of data to bootstrap-sample per tree.
    """

    def __init__(self, n_trees: int = 10, max_depth: int = 5, sample_ratio: float = 0.8):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.sample_ratio = sample_ratio
        self._trees: List[DecisionTreeClassifier] = []
        self._rng_seed = 42

    def fit(self, X: list, y: list) -> "RandomForestClassifier":
        """Fit the forest via bootstrap aggregation."""
        import random
        rng = random.Random(self._rng_seed)
        self._trees = []
        n = len(y)
        sample_n = max(1, int(n * self.sample_ratio))
        for _ in range(self.n_trees):
            indices = [rng.randint(0, n - 1) for _ in range(sample_n)]
            X_s = [X[i] for i in indices]
            y_s = [y[i] for i in indices]
            tree = DecisionTreeClassifier(max_depth=self.max_depth)
            tree.fit(X_s, y_s)
            self._trees.append(tree)
        return self

    def predict(self, X: list) -> list:
        """Predict via majority vote."""
        if not self._trees:
            return [0] * len(X)
        all_preds = [tree.predict(X) for tree in self._trees]
        result = []
        for i in range(len(X)):
            votes: dict = {}
            for preds in all_preds:
                v = preds[i]
                votes[v] = votes.get(v, 0) + 1
            result.append(max(votes, key=votes.get))
        return result


class GradientBooster:
    """Pure-Python gradient boosting classifier for binary classification.

    Uses simple decision stumps (depth-1 trees) as weak learners.
    Targets: labels should be 0 or 1.

    Parameters
    ----------
    n_rounds : int
        Number of boosting rounds.
    lr : float
        Learning rate (shrinkage).
    max_depth : int
        Max depth of each weak learner.
    """

    def __init__(self, n_rounds: int = 50, lr: float = 0.1, max_depth: int = 1):
        self.n_rounds = n_rounds
        self.lr = lr
        self.max_depth = max_depth
        self._stumps: list = []
        self._init_pred: float = 0.0

    def fit(self, X: list, y: list) -> "GradientBooster":
        """Fit via gradient boosting with log-loss."""
        import math as _math

        n = len(y)
        # Convert labels to float
        y_f = [float(v) for v in y]
        # Initial prediction = log(odds)
        pos = sum(y_f)
        neg = n - pos
        self._init_pred = _math.log(pos / neg) if neg > 0 and pos > 0 else 0.0

        F = [self._init_pred] * n
        self._stumps = []

        for _ in range(self.n_rounds):
            # Probabilities
            probs = [1.0 / (1.0 + _math.exp(-f)) for f in F]
            # Negative gradient (residuals)
            residuals = [y_f[i] - probs[i] for i in range(n)]
            # Fit a tree to residuals
            tree = DecisionTreeClassifier(max_depth=self.max_depth, min_samples_split=2)
            tree.fit(X, residuals)
            preds = tree.predict(X)
            # Update F
            for i in range(n):
                F[i] += self.lr * preds[i]
            self._stumps.append(tree)

        return self

    def predict(self, X: list) -> list:
        """Predict binary labels (0 or 1)."""
        import math as _math

        n = len(X)
        F = [self._init_pred] * n
        for tree in self._stumps:
            preds = tree.predict(X)
            for i in range(n):
                F[i] += self.lr * preds[i]
        return [1 if 1.0 / (1.0 + _math.exp(-f)) >= 0.5 else 0 for f in F]

    def predict_proba(self, X: list) -> list:
        """Predict probabilities for class 1."""
        import math as _math

        n = len(X)
        F = [self._init_pred] * n
        for tree in self._stumps:
            preds = tree.predict(X)
            for i in range(n):
                F[i] += self.lr * preds[i]
        return [1.0 / (1.0 + _math.exp(-f)) for f in F]


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
