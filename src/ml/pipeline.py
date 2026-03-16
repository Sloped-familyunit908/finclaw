"""
Walk-forward ML pipeline.

Feature generation → Normalization → Train → Predict → Evaluate
with walk-forward validation and IC metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .features import FeatureEngine
from .models import LinearRegression, walk_forward_split


@dataclass
class PipelineMetrics:
    """Metrics from a walk-forward evaluation."""

    ic_mean: float = 0.0
    ic_std: float = 0.0
    rank_ic_mean: float = 0.0
    rank_ic_std: float = 0.0
    turnover_mean: float = 0.0
    n_splits: int = 0
    ic_per_split: List[float] = field(default_factory=list)
    rank_ic_per_split: List[float] = field(default_factory=list)

    def summary(self) -> Dict[str, float]:
        return {
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "rank_ic_mean": self.rank_ic_mean,
            "rank_ic_std": self.rank_ic_std,
            "turnover_mean": self.turnover_mean,
            "n_splits": self.n_splits,
        }


def _rank_array(arr: np.ndarray) -> np.ndarray:
    """Rank array values (average rank for ties)."""
    n = len(arr)
    order = np.argsort(arr)
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1, dtype=float)
    return ranks


def information_coefficient(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Pearson correlation between predictions and actuals (IC)."""
    mask = ~(np.isnan(predictions) | np.isnan(actuals))
    p = predictions[mask]
    a = actuals[mask]
    if len(p) < 3:
        return 0.0
    p_std = np.std(p)
    a_std = np.std(a)
    if p_std == 0 or a_std == 0:
        return 0.0
    return float(np.corrcoef(p, a)[0, 1])


def rank_information_coefficient(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Spearman rank correlation (Rank IC)."""
    mask = ~(np.isnan(predictions) | np.isnan(actuals))
    p = predictions[mask]
    a = actuals[mask]
    if len(p) < 3:
        return 0.0
    return information_coefficient(_rank_array(p), _rank_array(a))


def portfolio_turnover(weights_prev: np.ndarray, weights_curr: np.ndarray) -> float:
    """One-sided turnover between two weight vectors."""
    return float(np.sum(np.abs(weights_curr - weights_prev)) / 2.0)


class WalkForwardPipeline:
    """Walk-forward ML pipeline for alpha research.

    Parameters
    ----------
    train_size : int
        Number of samples in training window (default 252 = 1 year).
    test_size : int
        Number of samples in test window (default 21 = 1 month).
    model : object, optional
        Model with fit(X, y) and predict(X). Defaults to LinearRegression.
    feature_names : list of str, optional
        Subset of features to use. None = use all.
    target_horizon : int
        Forward return horizon for labels (default 21 days).
    """

    def __init__(
        self,
        train_size: int = 252,
        test_size: int = 21,
        model: Any = None,
        feature_names: Optional[List[str]] = None,
        target_horizon: int = 21,
    ):
        self.train_size = train_size
        self.test_size = test_size
        self.model = model or LinearRegression()
        self.feature_names = feature_names
        self.target_horizon = target_horizon

    def _build_features(self, close: np.ndarray, **kwargs) -> Dict[str, np.ndarray]:
        """Generate features from price data."""
        engine = FeatureEngine(close, **kwargs)
        features = engine.generate_all()
        if self.feature_names:
            features = {k: v for k, v in features.items() if k in self.feature_names}
        return features

    def _features_to_matrix(self, features: Dict[str, np.ndarray]) -> Tuple[np.ndarray, List[str]]:
        """Convert feature dict to (n_samples, n_features) matrix."""
        names = sorted(features.keys())
        if not names:
            return np.array([]).reshape(0, 0), []
        n = len(features[names[0]])
        X = np.column_stack([features[name] for name in names])
        return X, names

    def _make_labels(self, close: np.ndarray) -> np.ndarray:
        """Forward returns as prediction labels."""
        n = len(close)
        labels = np.full(n, np.nan)
        h = self.target_horizon
        if h < n:
            labels[: n - h] = close[h:] / close[: n - h] - 1.0
        return labels

    def _normalize(self, X_train: np.ndarray, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Z-score normalize using training statistics."""
        means = np.nanmean(X_train, axis=0)
        stds = np.nanstd(X_train, axis=0)
        stds = np.where(stds == 0, 1.0, stds)
        X_train_norm = (X_train - means) / stds
        X_test_norm = (X_test - means) / stds
        # Replace remaining NaN with 0
        X_train_norm = np.nan_to_num(X_train_norm, nan=0.0)
        X_test_norm = np.nan_to_num(X_test_norm, nan=0.0)
        return X_train_norm, X_test_norm

    def run(
        self,
        close: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
    ) -> PipelineMetrics:
        """Run walk-forward evaluation.

        Parameters
        ----------
        close, high, low, volume : array-like
            OHLCV data.

        Returns
        -------
        PipelineMetrics
            Evaluation results.
        """
        close = np.asarray(close, dtype=float)
        kwargs = {}
        if high is not None:
            kwargs["high"] = high
        if low is not None:
            kwargs["low"] = low
        if volume is not None:
            kwargs["volume"] = volume

        features = self._build_features(close, **kwargs)
        X, feat_names = self._features_to_matrix(features)
        y = self._make_labels(close)

        if X.shape[0] == 0 or X.shape[1] == 0:
            return PipelineMetrics()

        splits = walk_forward_split(len(close), self.train_size, self.test_size)
        if not splits:
            return PipelineMetrics()

        ics: List[float] = []
        rank_ics: List[float] = []
        turnovers: List[float] = []
        prev_predictions: Optional[np.ndarray] = None

        for train_idx, test_idx in splits:
            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]

            X_train_n, X_test_n = self._normalize(X_train, X_test)

            self.model.fit(X_train_n, y_train)
            preds = self.model.predict(X_test_n)

            ic = information_coefficient(preds, y_test)
            ric = rank_information_coefficient(preds, y_test)
            ics.append(ic)
            rank_ics.append(ric)

            if prev_predictions is not None and len(prev_predictions) == len(preds):
                # Approximate turnover from prediction changes
                p_norm = preds / (np.sum(np.abs(preds)) + 1e-10)
                pp_norm = prev_predictions / (np.sum(np.abs(prev_predictions)) + 1e-10)
                turnovers.append(portfolio_turnover(pp_norm, p_norm))
            prev_predictions = preds.copy()

        metrics = PipelineMetrics(
            ic_mean=float(np.mean(ics)) if ics else 0.0,
            ic_std=float(np.std(ics)) if ics else 0.0,
            rank_ic_mean=float(np.mean(rank_ics)) if rank_ics else 0.0,
            rank_ic_std=float(np.std(rank_ics)) if rank_ics else 0.0,
            turnover_mean=float(np.mean(turnovers)) if turnovers else 0.0,
            n_splits=len(splits),
            ic_per_split=ics,
            rank_ic_per_split=rank_ics,
        )
        return metrics
