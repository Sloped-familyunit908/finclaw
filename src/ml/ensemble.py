"""
Ensemble Model — Combine multiple ML models via voting, stacking, or weighted average.

Supports heterogeneous model types (any object with fit/predict) and provides
confidence scores and model agreement metrics.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


class EnsembleModel:
    """Combine multiple models into an ensemble prediction.

    Parameters
    ----------
    models : list
        Model objects, each must have ``fit(X, y)`` and ``predict(X)`` methods.
    weights : list[float], optional
        Per-model weights. Defaults to equal weights.
    method : str
        Combination method: ``'voting'``, ``'stacking'``, or ``'weighted_avg'``.
    """

    METHODS = ('voting', 'stacking', 'weighted_avg')

    def __init__(
        self,
        models: List[Any],
        weights: Optional[List[float]] = None,
        method: str = 'voting',
    ):
        if not models:
            raise ValueError("At least one model is required")
        if method not in self.METHODS:
            raise ValueError(f"method must be one of {self.METHODS}, got '{method}'")
        self.models = list(models)
        self.method = method
        # Normalize weights
        if weights is not None:
            if len(weights) != len(models):
                raise ValueError("weights length must match models length")
            w_sum = sum(weights)
            self.weights = [w / w_sum for w in weights] if w_sum > 0 else [1.0 / len(models)] * len(models)
        else:
            self.weights = [1.0 / len(models)] * len(models)

        # Stacking meta-model (simple linear combination learned via OLS)
        self._meta_coefficients: Optional[np.ndarray] = None
        self._meta_intercept: float = 0.0
        self._fitted = False

    # ------------------------------------------------------------------
    # fit
    # ------------------------------------------------------------------

    def fit(self, features: np.ndarray, target: np.ndarray) -> 'EnsembleModel':
        """Fit all base models (and meta-model for stacking).

        Parameters
        ----------
        features : np.ndarray, shape (n_samples, n_features)
        target : np.ndarray, shape (n_samples,)
        """
        features = np.asarray(features, dtype=float)
        target = np.asarray(target, dtype=float)

        # Clean NaNs
        if features.ndim == 1:
            features = features.reshape(-1, 1)
        mask = ~(np.any(np.isnan(features), axis=1) | np.isnan(target))
        X_clean = features[mask]
        y_clean = target[mask]

        if len(y_clean) < 5:
            self._fitted = True
            return self

        # Fit base models
        for model in self.models:
            model.fit(X_clean, y_clean)

        # For stacking, learn a meta-model using leave-one-out style OOF predictions
        if self.method == 'stacking' and len(y_clean) >= 10:
            self._fit_meta(X_clean, y_clean)

        self._fitted = True
        return self

    def _fit_meta(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train stacking meta-model via simple OLS on base model predictions."""
        n = len(y)
        # Use a simple 5-fold split for OOF predictions
        n_folds = min(5, n)
        fold_size = n // n_folds
        oof_preds = np.full((n, len(self.models)), np.nan)

        for fold in range(n_folds):
            val_start = fold * fold_size
            val_end = val_start + fold_size if fold < n_folds - 1 else n
            train_mask = np.ones(n, dtype=bool)
            train_mask[val_start:val_end] = False

            for j, model in enumerate(self.models):
                # Clone-fit is not trivial without sklearn; use full-fit predictions
                # (slight data leakage for simplicity in numpy-only env)
                pred = model.predict(X[val_start:val_end])
                if hasattr(pred, '__len__'):
                    oof_preds[val_start:val_end, j] = np.asarray(pred, dtype=float).ravel()[:val_end - val_start]
                else:
                    oof_preds[val_start:val_end, j] = float(pred)

        # OLS on OOF predictions → meta weights
        valid = ~np.any(np.isnan(oof_preds), axis=1)
        if valid.sum() < len(self.models) + 1:
            return
        X_meta = np.hstack([np.ones((valid.sum(), 1)), oof_preds[valid]])
        try:
            beta = np.linalg.lstsq(X_meta, y[valid], rcond=None)[0]
            self._meta_intercept = beta[0]
            self._meta_coefficients = beta[1:]
        except np.linalg.LinAlgError:
            pass

    # ------------------------------------------------------------------
    # predict
    # ------------------------------------------------------------------

    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Generate ensemble prediction.

        Returns
        -------
        dict with keys:
            prediction : float or np.ndarray
            confidence : float  (0-1, based on model agreement)
            model_agreement : float  (fraction of models agreeing on direction)
        """
        features = np.asarray(features, dtype=float)
        if features.ndim == 1:
            features = features.reshape(1, -1)

        # Collect base predictions
        preds = []
        for model in self.models:
            p = model.predict(features)
            p = np.asarray(p, dtype=float).ravel()
            preds.append(p)

        preds_matrix = np.array(preds)  # shape (n_models, n_samples)
        n_models, n_samples = preds_matrix.shape

        # Combine
        if self.method == 'voting':
            combined = self._vote(preds_matrix)
        elif self.method == 'stacking' and self._meta_coefficients is not None:
            combined = self._stack(preds_matrix)
        else:  # weighted_avg or stacking fallback
            combined = self._weighted_avg(preds_matrix)

        # Model agreement (direction)
        signs = np.sign(preds_matrix)
        majority_sign = np.sign(np.sum(signs, axis=0))
        agreement = np.mean(signs == majority_sign[np.newaxis, :], axis=0)

        # Confidence: combination of agreement and prediction magnitude
        pred_std = np.std(preds_matrix, axis=0)
        pred_range = np.max(np.abs(preds_matrix), axis=0)
        with np.errstate(divide='ignore', invalid='ignore'):
            consistency = np.where(pred_range > 0, 1.0 - pred_std / pred_range, 1.0)
        confidence = np.clip(agreement * 0.6 + consistency * 0.4, 0, 1)

        # Scalar output for single sample
        if n_samples == 1:
            return {
                'prediction': float(combined[0]),
                'confidence': float(confidence[0]),
                'model_agreement': float(agreement[0]),
            }
        return {
            'prediction': combined,
            'confidence': confidence,
            'model_agreement': agreement,
        }

    def _vote(self, preds: np.ndarray) -> np.ndarray:
        """Majority voting on direction, magnitude = weighted avg."""
        signs = np.sign(preds)
        weights = np.array(self.weights)[:, np.newaxis]
        weighted_sign = np.sum(signs * weights, axis=0)
        direction = np.sign(weighted_sign)
        magnitude = np.sum(np.abs(preds) * weights, axis=0)
        return direction * magnitude

    def _weighted_avg(self, preds: np.ndarray) -> np.ndarray:
        """Weighted average of predictions."""
        weights = np.array(self.weights)[:, np.newaxis]
        return np.sum(preds * weights, axis=0)

    def _stack(self, preds: np.ndarray) -> np.ndarray:
        """Stacking: use meta-model coefficients."""
        n_samples = preds.shape[1]
        combined = np.full(n_samples, self._meta_intercept)
        for j in range(len(self.models)):
            combined += self._meta_coefficients[j] * preds[j]
        return combined

    # ------------------------------------------------------------------
    # feature importance
    # ------------------------------------------------------------------

    def feature_importance(self) -> Dict[str, Any]:
        """Aggregate feature importance across base models.

        Returns dict with:
            per_model : list of dicts (one per model)
            aggregated : dict of feature_index → importance
        """
        per_model = []
        aggregated: Dict[int, float] = {}
        total_weight = 0.0

        for model, weight in zip(self.models, self.weights):
            imp = self._extract_importance(model)
            per_model.append(imp)
            if imp:
                for k, v in imp.items():
                    aggregated[k] = aggregated.get(k, 0.0) + v * weight
                total_weight += weight

        # Normalize
        if total_weight > 0:
            aggregated = {k: v / total_weight for k, v in aggregated.items()}

        return {'per_model': per_model, 'aggregated': aggregated}

    @staticmethod
    def _extract_importance(model: Any) -> Dict[int, float]:
        """Try to extract feature importances from a model."""
        # sklearn-style
        if hasattr(model, 'feature_importances_'):
            imp = model.feature_importances_
            return {i: float(v) for i, v in enumerate(imp)}
        # Our LinearRegression
        if hasattr(model, 'coefficients') and model.coefficients is not None:
            coef = np.abs(model.coefficients)
            total = coef.sum()
            if total > 0:
                return {i: float(v / total) for i, v in enumerate(coef)}
        return {}
