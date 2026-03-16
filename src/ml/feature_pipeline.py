"""Feature Engineering Pipeline for financial ML workflows."""

from typing import Callable, Any
import math


class FeaturePipeline:
    """Composable feature engineering pipeline with fit/transform semantics."""

    def __init__(self):
        self.steps: list[tuple[str, Callable]] = []
        self._fitted_state: dict[str, Any] = {}
        self._is_fitted = False

    def add_step(self, name: str, transform: Callable) -> "FeaturePipeline":
        """Add a named transform step. Returns self for chaining."""
        if any(n == name for n, _ in self.steps):
            raise ValueError(f"Duplicate step name: {name}")
        self.steps.append((name, transform))
        return self

    def fit_transform(self, data: dict) -> dict:
        """Fit all steps and transform data. data is a dict of column->list."""
        result = dict(data)
        self._fitted_state = {}
        for name, fn in self.steps:
            out = fn(result, fit=True)
            if isinstance(out, tuple):
                result, state = out
                self._fitted_state[name] = state
            else:
                result = out
        self._is_fitted = True
        return result

    def transform(self, data: dict) -> dict:
        """Transform data using fitted pipeline. Must call fit_transform first."""
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform first.")
        result = dict(data)
        for name, fn in self.steps:
            state = self._fitted_state.get(name)
            if state is not None:
                result = fn(result, fit=False, state=state)
            else:
                out = fn(result, fit=False)
                result = out if not isinstance(out, tuple) else out[0]
        return result

    @staticmethod
    def lag_features(columns: list[str], lags: list[int]) -> Callable:
        """Create lagged feature columns."""
        def _transform(data: dict, fit: bool = False, **kw) -> dict:
            result = dict(data)
            for col in columns:
                if col not in data:
                    continue
                values = data[col]
                for lag in lags:
                    lagged = [None] * lag + values[:-lag] if lag > 0 else values
                    result[f"{col}_lag{lag}"] = lagged
            return result
        return _transform

    @staticmethod
    def rolling_features(columns: list[str], windows: list[int]) -> Callable:
        """Create rolling mean feature columns."""
        def _transform(data: dict, fit: bool = False, **kw) -> dict:
            result = dict(data)
            for col in columns:
                if col not in data:
                    continue
                values = data[col]
                for w in windows:
                    rolled = []
                    for i in range(len(values)):
                        if i < w - 1:
                            rolled.append(None)
                        else:
                            window_vals = [v for v in values[i - w + 1:i + 1] if v is not None]
                            rolled.append(sum(window_vals) / len(window_vals) if window_vals else None)
                    result[f"{col}_roll{w}"] = rolled
            return result
        return _transform

    @staticmethod
    def target_encoding(column: str) -> Callable:
        """Target-encode a categorical column using mean of target in fit, stored mapping in transform."""
        def _transform(data: dict, fit: bool = False, state: dict = None, **kw):
            if column not in data or "target" not in data:
                return (data, {}) if fit else data
            cats = data[column]
            targets = data["target"]
            if fit:
                # Build encoding map
                sums: dict[str, float] = {}
                counts: dict[str, int] = {}
                for c, t in zip(cats, targets):
                    if c is not None and t is not None:
                        sums[c] = sums.get(c, 0.0) + t
                        counts[c] = counts.get(c, 0) + 1
                mapping = {k: sums[k] / counts[k] for k in sums}
                global_mean = sum(t for t in targets if t is not None) / max(1, sum(1 for t in targets if t is not None))
                result = dict(data)
                result[f"{column}_encoded"] = [mapping.get(c, global_mean) for c in cats]
                return result, {"mapping": mapping, "global_mean": global_mean}
            else:
                mapping = state["mapping"]
                global_mean = state["global_mean"]
                result = dict(data)
                result[f"{column}_encoded"] = [mapping.get(c, global_mean) for c in cats]
                return result
        return _transform
