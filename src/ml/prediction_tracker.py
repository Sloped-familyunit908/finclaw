"""Prediction Tracker — log, update, and evaluate ML predictions."""

import uuid
import time
import math
from typing import Optional


class PredictionTracker:
    """Track model predictions and compute accuracy/calibration metrics."""

    def __init__(self):
        self._predictions: dict[str, dict] = {}

    def log_prediction(self, model: str, ticker: str, prediction: float,
                       actual: float = None) -> str:
        """Log a prediction. Returns prediction_id."""
        pid = str(uuid.uuid4())[:8]
        self._predictions[pid] = {
            "model": model,
            "ticker": ticker,
            "prediction": prediction,
            "actual": actual,
            "timestamp": time.time(),
        }
        return pid

    def update_actual(self, prediction_id: str, actual: float) -> bool:
        """Update the actual value for a logged prediction. Returns True if found."""
        if prediction_id not in self._predictions:
            return False
        self._predictions[prediction_id]["actual"] = actual
        return True

    def accuracy_report(self, model: str = None) -> dict:
        """Generate accuracy report. Filters by model if provided."""
        preds = [
            p for p in self._predictions.values()
            if p["actual"] is not None and (model is None or p["model"] == model)
        ]
        if not preds:
            return {"count": 0, "mse": None, "mae": None, "directional_accuracy": None}

        errors = [p["prediction"] - p["actual"] for p in preds]
        mse = sum(e ** 2 for e in errors) / len(errors)
        mae = sum(abs(e) for e in errors) / len(errors)

        # Directional accuracy: did we predict the sign correctly?
        correct = sum(
            1 for p in preds
            if (p["prediction"] > 0) == (p["actual"] > 0)
        )
        dir_acc = correct / len(preds)

        return {
            "count": len(preds),
            "mse": round(mse, 6),
            "mae": round(mae, 6),
            "directional_accuracy": round(dir_acc, 4),
            "rmse": round(math.sqrt(mse), 6),
        }

    def calibration_check(self, model: str) -> dict:
        """Check prediction calibration by binning predictions."""
        preds = [
            p for p in self._predictions.values()
            if p["actual"] is not None and p["model"] == model
        ]
        if not preds:
            return {"model": model, "bins": [], "calibrated": None}

        # Simple 5-bin calibration
        sorted_preds = sorted(preds, key=lambda p: p["prediction"])
        bin_size = max(1, len(sorted_preds) // 5)
        bins = []
        for i in range(0, len(sorted_preds), bin_size):
            chunk = sorted_preds[i:i + bin_size]
            avg_pred = sum(p["prediction"] for p in chunk) / len(chunk)
            avg_actual = sum(p["actual"] for p in chunk) / len(chunk)
            bins.append({
                "avg_prediction": round(avg_pred, 4),
                "avg_actual": round(avg_actual, 4),
                "count": len(chunk),
            })

        # Calibration score: correlation between avg_pred and avg_actual
        if len(bins) >= 2:
            pred_vals = [b["avg_prediction"] for b in bins]
            actual_vals = [b["avg_actual"] for b in bins]
            mean_p = sum(pred_vals) / len(pred_vals)
            mean_a = sum(actual_vals) / len(actual_vals)
            cov = sum((p - mean_p) * (a - mean_a) for p, a in zip(pred_vals, actual_vals))
            var_p = sum((p - mean_p) ** 2 for p in pred_vals)
            var_a = sum((a - mean_a) ** 2 for a in actual_vals)
            denom = math.sqrt(var_p * var_a) if var_p * var_a > 0 else 1e-10
            corr = cov / denom
            calibrated = corr > 0.5
        else:
            corr = None
            calibrated = None

        return {
            "model": model,
            "bins": bins,
            "correlation": round(corr, 4) if corr is not None else None,
            "calibrated": calibrated,
        }

    @property
    def predictions(self) -> dict:
        return dict(self._predictions)
