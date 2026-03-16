"""Model Selection with cross-validation for financial ML."""

import math
import random
from typing import Any


class LinearRegression:
    """Simple OLS linear regression."""
    def __init__(self):
        self.weights = None
        self.bias = 0.0

    def fit(self, X: list[list[float]], y: list[float]):
        n = len(X)
        if n == 0:
            return self
        k = len(X[0])
        # Simple gradient descent
        self.weights = [0.0] * k
        self.bias = 0.0
        lr = 0.001
        for _ in range(200):
            for i in range(n):
                pred = sum(self.weights[j] * X[i][j] for j in range(k)) + self.bias
                err = pred - y[i]
                for j in range(k):
                    self.weights[j] -= lr * err * X[i][j] / n
                self.bias -= lr * err / n
        return self

    def predict(self, X: list[list[float]]) -> list[float]:
        if self.weights is None:
            return [0.0] * len(X)
        return [sum(self.weights[j] * x[j] for j in range(len(x))) + self.bias for x in X]


class RidgeRegression(LinearRegression):
    """Ridge regression with L2 penalty."""
    def __init__(self, alpha: float = 1.0):
        super().__init__()
        self.alpha = alpha

    def fit(self, X, y):
        super().fit(X, y)
        if self.weights:
            shrink = 1.0 / (1.0 + self.alpha * 0.01)
            self.weights = [w * shrink for w in self.weights]
        return self


class LassoRegression(LinearRegression):
    """Lasso regression with L1 penalty."""
    def __init__(self, alpha: float = 1.0):
        super().__init__()
        self.alpha = alpha

    def fit(self, X, y):
        super().fit(X, y)
        if self.weights:
            threshold = self.alpha * 0.001
            self.weights = [
                w - threshold if w > threshold else (w + threshold if w < -threshold else 0.0)
                for w in self.weights
            ]
        return self


class SimpleRandomForest:
    """Simplified random forest using decision stumps."""
    def __init__(self, n_trees: int = 10):
        self.n_trees = n_trees
        self.trees: list[tuple[int, float, float, float]] = []  # (feature_idx, threshold, left_val, right_val)

    def fit(self, X: list[list[float]], y: list[float]):
        n = len(X)
        k = len(X[0]) if X else 0
        self.trees = []
        for _ in range(self.n_trees):
            # Bootstrap sample
            indices = [random.randint(0, n - 1) for _ in range(n)]
            fi = random.randint(0, max(0, k - 1))
            vals = sorted(set(X[i][fi] for i in indices))
            if len(vals) < 2:
                self.trees.append((fi, 0.0, sum(y) / max(1, n), sum(y) / max(1, n)))
                continue
            thresh = vals[len(vals) // 2]
            left = [y[i] for i in indices if X[i][fi] <= thresh]
            right = [y[i] for i in indices if X[i][fi] > thresh]
            lv = sum(left) / max(1, len(left))
            rv = sum(right) / max(1, len(right))
            self.trees.append((fi, thresh, lv, rv))
        return self

    def predict(self, X: list[list[float]]) -> list[float]:
        if not self.trees:
            return [0.0] * len(X)
        results = []
        for x in X:
            preds = []
            for fi, thresh, lv, rv in self.trees:
                preds.append(lv if x[fi] <= thresh else rv)
            results.append(sum(preds) / len(preds))
        return results


class SimpleGradientBoost:
    """Simplified gradient boosting with decision stumps."""
    def __init__(self, n_rounds: int = 10, learning_rate: float = 0.1):
        self.n_rounds = n_rounds
        self.lr = learning_rate
        self.stumps: list[tuple[int, float, float, float]] = []
        self.base_pred = 0.0

    def fit(self, X: list[list[float]], y: list[float]):
        n = len(X)
        k = len(X[0]) if X else 0
        self.base_pred = sum(y) / max(1, n)
        residuals = [y[i] - self.base_pred for i in range(n)]
        self.stumps = []
        for _ in range(self.n_rounds):
            fi = random.randint(0, max(0, k - 1))
            vals = sorted(set(X[i][fi] for i in range(n)))
            if len(vals) < 2:
                continue
            thresh = vals[len(vals) // 2]
            left = [residuals[i] for i in range(n) if X[i][fi] <= thresh]
            right = [residuals[i] for i in range(n) if X[i][fi] > thresh]
            lv = sum(left) / max(1, len(left))
            rv = sum(right) / max(1, len(right))
            self.stumps.append((fi, thresh, lv, rv))
            for i in range(n):
                pred = lv if X[i][fi] <= thresh else rv
                residuals[i] -= self.lr * pred
        return self

    def predict(self, X: list[list[float]]) -> list[float]:
        results = []
        for x in X:
            p = self.base_pred
            for fi, thresh, lv, rv in self.stumps:
                p += self.lr * (lv if x[fi] <= thresh else rv)
            results.append(p)
        return results


class ModelSelector:
    """Compare and auto-select ML models for financial prediction."""

    MODELS = {
        'linear': LinearRegression,
        'ridge': RidgeRegression,
        'lasso': LassoRegression,
        'random_forest': SimpleRandomForest,
        'gradient_boost': SimpleGradientBoost,
    }

    def _mse(self, actual: list[float], predicted: list[float]) -> float:
        return sum((a - p) ** 2 for a, p in zip(actual, predicted)) / max(1, len(actual))

    def _sharpe(self, actual: list[float], predicted: list[float]) -> float:
        """Directional accuracy as proxy for sharpe-like metric."""
        if len(actual) < 2:
            return 0.0
        returns = []
        for a, p in zip(actual, predicted):
            # Positive return if prediction direction matches
            returns.append(abs(a) if (a > 0) == (p > 0) else -abs(a))
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / max(1, len(returns))
        std = math.sqrt(var) if var > 0 else 1e-10
        return mean_r / std

    def _cross_validate(self, model_cls, features: list[list[float]], target: list[float],
                        n_splits: int = 5, metric: str = 'sharpe') -> float:
        n = len(features)
        fold_size = max(1, n // n_splits)
        scores = []
        for i in range(n_splits):
            start = i * fold_size
            end = min(start + fold_size, n)
            if start >= n:
                break
            test_X = features[start:end]
            test_y = target[start:end]
            train_X = features[:start] + features[end:]
            train_y = target[:start] + target[end:]
            if not train_X or not test_X:
                continue
            model = model_cls()
            model.fit(train_X, train_y)
            preds = model.predict(test_X)
            if metric == 'sharpe':
                scores.append(self._sharpe(test_y, preds))
            else:
                scores.append(-self._mse(test_y, preds))  # Negative MSE (higher is better)
        return sum(scores) / max(1, len(scores))

    def auto_select(self, features: list[list[float]], target: list[float],
                    metric: str = 'sharpe') -> dict:
        """Cross-validate all models, return best."""
        results = self.compare(features, target, metric)
        if not results:
            return {"model": None, "score": 0.0}
        best = max(results, key=lambda r: r["score"])
        return best

    def compare(self, features: list[list[float]], target: list[float],
                metric: str = 'sharpe') -> list[dict]:
        """Compare all models and return sorted results."""
        results = []
        for name, cls in self.MODELS.items():
            score = self._cross_validate(cls, features, target, metric=metric)
            results.append({"model": name, "score": round(score, 6), "class": cls})
        return sorted(results, key=lambda r: r["score"], reverse=True)
