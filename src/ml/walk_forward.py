"""
Walk-forward validation for ML models.

Provides train/test splitting with configurable gap to avoid look-ahead bias,
model evaluation with accuracy/precision/recall metrics, and summary reporting.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple


class WalkForwardValidator:
    """Walk-forward cross-validator for time-series models.

    Slides a fixed-width training window forward through the data,
    with an optional gap between train and test to avoid look-ahead bias.

    Parameters
    ----------
    train_size : int
        Number of samples in each training window.
    test_size : int
        Number of samples in each test window.
    gap : int
        Number of samples to skip between train end and test start.
    """

    def __init__(self, train_size: int, test_size: int, gap: int = 0):
        if train_size < 1:
            raise ValueError("train_size must be >= 1")
        if test_size < 1:
            raise ValueError("test_size must be >= 1")
        if gap < 0:
            raise ValueError("gap must be >= 0")
        self.train_size = train_size
        self.test_size = test_size
        self.gap = gap
        self._results: List[Dict[str, Any]] = []

    def split(self, data: list) -> List[Tuple[List[int], List[int]]]:
        """Generate train/test index splits.

        Parameters
        ----------
        data : list
            The dataset (used only for length).

        Returns
        -------
        list of (train_indices, test_indices) tuples
        """
        n = len(data)
        splits = []
        start = 0
        while start + self.train_size + self.gap + self.test_size <= n:
            train_idx = list(range(start, start + self.train_size))
            test_start = start + self.train_size + self.gap
            test_idx = list(range(test_start, test_start + self.test_size))
            splits.append((train_idx, test_idx))
            start += self.test_size
        return splits

    def evaluate(
        self,
        model: Any,
        data: list,
        features: List[str],
        target: str,
        feature_extractor: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run walk-forward evaluation.

        Each element of *data* should be a dict with keys matching
        *features* and *target*.  Alternatively, provide a *feature_extractor*
        callable ``(data_slice, features) -> (X_2d_list, y_list)``.

        Parameters
        ----------
        model : object
            Must support ``.fit(X, y)`` and ``.predict(X)`` where X/y are
            lists-of-lists and lists respectively.
        data : list
            Full dataset (list of dicts or custom objects).
        features : list of str
            Feature column names.
        target : str
            Target column name.
        feature_extractor : callable, optional
            Custom function to extract X, y from a data slice.

        Returns
        -------
        dict with keys: accuracy, precision, recall, n_splits, per_split
        """
        splits = self.split(data)
        if not splits:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "n_splits": 0, "per_split": []}

        self._results = []
        all_correct = 0
        all_total = 0
        all_tp = 0
        all_fp = 0
        all_fn = 0

        for train_idx, test_idx in splits:
            train_slice = [data[i] for i in train_idx]
            test_slice = [data[i] for i in test_idx]

            if feature_extractor:
                X_train, y_train = feature_extractor(train_slice, features)
                X_test, y_test = feature_extractor(test_slice, features)
            else:
                X_train = [[row[f] for f in features] for row in train_slice]
                y_train = [row[target] for row in train_slice]
                X_test = [[row[f] for f in features] for row in test_slice]
                y_test = [row[target] for row in test_slice]

            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            # Compute metrics
            correct = sum(1 for p, a in zip(preds, y_test) if p == a)
            total = len(y_test)
            tp = sum(1 for p, a in zip(preds, y_test) if p == 1 and a == 1)
            fp = sum(1 for p, a in zip(preds, y_test) if p == 1 and a != 1)
            fn = sum(1 for p, a in zip(preds, y_test) if p != 1 and a == 1)

            acc = correct / total if total > 0 else 0.0
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            split_result = {
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "n_samples": total,
                "correct": correct,
            }
            self._results.append(split_result)
            all_correct += correct
            all_total += total
            all_tp += tp
            all_fp += fp
            all_fn += fn

        overall = {
            "accuracy": all_correct / all_total if all_total > 0 else 0.0,
            "precision": all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0,
            "recall": all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0,
            "n_splits": len(splits),
            "per_split": self._results,
        }
        return overall

    def report(self) -> str:
        """Generate a human-readable report of the last evaluation.

        Returns
        -------
        str
            Formatted report string.
        """
        if not self._results:
            return "No evaluation results. Run evaluate() first."

        lines = ["Walk-Forward Validation Report", "=" * 40]
        for i, r in enumerate(self._results):
            lines.append(
                f"Split {i + 1}: accuracy={r['accuracy']:.4f}  "
                f"precision={r['precision']:.4f}  recall={r['recall']:.4f}  "
                f"n={r['n_samples']}"
            )

        n = len(self._results)
        avg_acc = sum(r["accuracy"] for r in self._results) / n
        avg_prec = sum(r["precision"] for r in self._results) / n
        avg_rec = sum(r["recall"] for r in self._results) / n
        lines.append("-" * 40)
        lines.append(
            f"Average:  accuracy={avg_acc:.4f}  "
            f"precision={avg_prec:.4f}  recall={avg_rec:.4f}  "
            f"splits={n}"
        )
        return "\n".join(lines)
