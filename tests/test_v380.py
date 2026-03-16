"""Tests for v3.8.0 ML Pipeline: FeaturePipeline, ModelSelector, PredictionTracker, FinancialDataSplitter."""
import pytest
import random
import math

from src.ml.feature_pipeline import FeaturePipeline
from src.ml.model_selection import (
    ModelSelector, LinearRegression as LR, RidgeRegression, LassoRegression,
    SimpleRandomForest, SimpleGradientBoost,
)
from src.ml.prediction_tracker import PredictionTracker
from src.ml.data_splitter import FinancialDataSplitter


# ==================== FeaturePipeline ====================

class TestFeaturePipeline:

    def test_empty_pipeline(self):
        fp = FeaturePipeline()
        data = {"close": [1, 2, 3]}
        result = fp.fit_transform(data)
        assert result == data

    def test_add_step_chaining(self):
        fp = FeaturePipeline()
        ret = fp.add_step("a", lambda d, **kw: d)
        assert ret is fp

    def test_duplicate_step_raises(self):
        fp = FeaturePipeline()
        fp.add_step("a", lambda d, **kw: d)
        with pytest.raises(ValueError, match="Duplicate"):
            fp.add_step("a", lambda d, **kw: d)

    def test_transform_before_fit_raises(self):
        fp = FeaturePipeline()
        fp.add_step("a", lambda d, **kw: d)
        with pytest.raises(RuntimeError):
            fp.transform({"x": [1]})

    def test_lag_features(self):
        fp = FeaturePipeline()
        fp.add_step("lag", FeaturePipeline.lag_features(["close"], [1, 2]))
        result = fp.fit_transform({"close": [10, 20, 30, 40]})
        assert "close_lag1" in result
        assert "close_lag2" in result
        assert result["close_lag1"][0] is None
        assert result["close_lag1"][1] == 10

    def test_lag_missing_column(self):
        fp = FeaturePipeline()
        fp.add_step("lag", FeaturePipeline.lag_features(["missing"], [1]))
        result = fp.fit_transform({"close": [1, 2]})
        assert "missing_lag1" not in result

    def test_rolling_features(self):
        fp = FeaturePipeline()
        fp.add_step("roll", FeaturePipeline.rolling_features(["close"], [3]))
        result = fp.fit_transform({"close": [10, 20, 30, 40, 50]})
        assert "close_roll3" in result
        assert result["close_roll3"][0] is None
        assert result["close_roll3"][1] is None
        assert result["close_roll3"][2] == 20.0  # mean(10,20,30)

    def test_rolling_missing_column(self):
        fp = FeaturePipeline()
        fp.add_step("roll", FeaturePipeline.rolling_features(["nope"], [2]))
        result = fp.fit_transform({"x": [1]})
        assert "nope_roll2" not in result

    def test_target_encoding_fit_transform(self):
        fp = FeaturePipeline()
        fp.add_step("te", FeaturePipeline.target_encoding("sector"))
        data = {
            "sector": ["tech", "tech", "fin", "fin"],
            "target": [10, 20, 5, 15],
        }
        result = fp.fit_transform(data)
        assert "sector_encoded" in result
        assert result["sector_encoded"][0] == 15.0  # mean of tech
        assert result["sector_encoded"][2] == 10.0  # mean of fin

    def test_target_encoding_transform(self):
        fp = FeaturePipeline()
        fp.add_step("te", FeaturePipeline.target_encoding("sector"))
        train = {"sector": ["A", "A", "B"], "target": [10, 20, 5]}
        fp.fit_transform(train)
        test = {"sector": ["A", "B", "C"], "target": [0, 0, 0]}
        result = fp.transform(test)
        assert result["sector_encoded"][0] == 15.0
        assert result["sector_encoded"][1] == 5.0
        # C is unknown -> global mean
        assert abs(result["sector_encoded"][2] - 11.6667) < 0.01

    def test_target_encoding_missing_column(self):
        fp = FeaturePipeline()
        fp.add_step("te", FeaturePipeline.target_encoding("missing"))
        result = fp.fit_transform({"x": [1], "target": [2]})
        assert "missing_encoded" not in result

    def test_multi_step_pipeline(self):
        fp = FeaturePipeline()
        fp.add_step("lag", FeaturePipeline.lag_features(["close"], [1]))
        fp.add_step("roll", FeaturePipeline.rolling_features(["close"], [2]))
        result = fp.fit_transform({"close": [1, 2, 3, 4]})
        assert "close_lag1" in result
        assert "close_roll2" in result


# ==================== ModelSelector ====================

class TestModelSelector:

    @pytest.fixture
    def sample_data(self):
        random.seed(42)
        X = [[random.gauss(0, 1), random.gauss(0, 1)] for _ in range(100)]
        y = [x[0] * 2 + x[1] * 0.5 + random.gauss(0, 0.1) for x in X]
        return X, y

    def test_linear_regression(self):
        model = LR()
        X = [[1.0], [2.0], [3.0], [4.0]]
        y = [2.0, 4.0, 6.0, 8.0]
        model.fit(X, y)
        preds = model.predict([[5.0]])
        assert len(preds) == 1

    def test_linear_empty(self):
        model = LR()
        model.fit([], [])
        assert model.predict([[1.0]]) == [0.0]

    def test_ridge(self):
        model = RidgeRegression(alpha=1.0)
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 2.0, 3.0]
        model.fit(X, y)
        preds = model.predict([[2.0]])
        assert len(preds) == 1

    def test_lasso(self):
        model = LassoRegression(alpha=1.0)
        X = [[1.0], [2.0], [3.0]]
        y = [1.0, 2.0, 3.0]
        model.fit(X, y)
        preds = model.predict([[2.0]])
        assert len(preds) == 1

    def test_random_forest(self, sample_data):
        X, y = sample_data
        model = SimpleRandomForest(n_trees=5)
        model.fit(X, y)
        preds = model.predict(X[:5])
        assert len(preds) == 5

    def test_random_forest_empty(self):
        model = SimpleRandomForest()
        assert model.predict([[1.0]]) == [0.0]

    def test_gradient_boost(self, sample_data):
        X, y = sample_data
        model = SimpleGradientBoost(n_rounds=5)
        model.fit(X, y)
        preds = model.predict(X[:5])
        assert len(preds) == 5

    def test_auto_select(self, sample_data):
        X, y = sample_data
        ms = ModelSelector()
        result = ms.auto_select(X, y, metric='sharpe')
        assert "model" in result
        assert "score" in result
        assert result["model"] in ModelSelector.MODELS

    def test_auto_select_mse(self, sample_data):
        X, y = sample_data
        ms = ModelSelector()
        result = ms.auto_select(X, y, metric='mse')
        assert result["model"] is not None

    def test_compare(self, sample_data):
        X, y = sample_data
        ms = ModelSelector()
        results = ms.compare(X, y)
        assert len(results) == 5
        assert all("model" in r and "score" in r for r in results)
        # Sorted descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_all_models_registered(self):
        assert set(ModelSelector.MODELS.keys()) == {
            'linear', 'ridge', 'lasso', 'random_forest', 'gradient_boost'
        }


# ==================== PredictionTracker ====================

class TestPredictionTracker:

    def test_log_prediction(self):
        pt = PredictionTracker()
        pid = pt.log_prediction("linear", "AAPL", 150.0)
        assert pid in pt.predictions
        assert pt.predictions[pid]["model"] == "linear"

    def test_log_with_actual(self):
        pt = PredictionTracker()
        pid = pt.log_prediction("rf", "MSFT", 300.0, actual=305.0)
        assert pt.predictions[pid]["actual"] == 305.0

    def test_update_actual(self):
        pt = PredictionTracker()
        pid = pt.log_prediction("linear", "AAPL", 150.0)
        assert pt.update_actual(pid, 155.0)
        assert pt.predictions[pid]["actual"] == 155.0

    def test_update_actual_not_found(self):
        pt = PredictionTracker()
        assert not pt.update_actual("nonexistent", 100.0)

    def test_accuracy_report_empty(self):
        pt = PredictionTracker()
        report = pt.accuracy_report()
        assert report["count"] == 0
        assert report["mse"] is None

    def test_accuracy_report(self):
        pt = PredictionTracker()
        pt.log_prediction("m", "A", 10.0, actual=12.0)
        pt.log_prediction("m", "B", 20.0, actual=18.0)
        pt.log_prediction("m", "C", 5.0, actual=5.0)
        report = pt.accuracy_report()
        assert report["count"] == 3
        assert report["mse"] is not None
        assert report["mae"] is not None
        assert report["rmse"] is not None

    def test_accuracy_report_filter_model(self):
        pt = PredictionTracker()
        pt.log_prediction("m1", "A", 10.0, actual=12.0)
        pt.log_prediction("m2", "B", 20.0, actual=18.0)
        report = pt.accuracy_report(model="m1")
        assert report["count"] == 1

    def test_directional_accuracy(self):
        pt = PredictionTracker()
        pt.log_prediction("m", "A", 5.0, actual=3.0)   # Both positive
        pt.log_prediction("m", "B", -2.0, actual=-1.0)  # Both negative
        pt.log_prediction("m", "C", 5.0, actual=-3.0)   # Mismatch
        report = pt.accuracy_report()
        assert report["directional_accuracy"] == pytest.approx(2 / 3, abs=0.01)

    def test_calibration_check_empty(self):
        pt = PredictionTracker()
        result = pt.calibration_check("m")
        assert result["bins"] == []
        assert result["calibrated"] is None

    def test_calibration_check(self):
        pt = PredictionTracker()
        for i in range(20):
            pt.log_prediction("m", "X", float(i), actual=float(i + random.gauss(0, 0.5)))
        result = pt.calibration_check("m")
        assert result["model"] == "m"
        assert len(result["bins"]) > 0
        assert result["correlation"] is not None


# ==================== FinancialDataSplitter ====================

class TestFinancialDataSplitter:

    def test_time_series_split_basic(self):
        data = list(range(100))
        splits = FinancialDataSplitter.time_series_split(data, n_splits=3, gap=2)
        assert len(splits) > 0
        for train, test in splits:
            assert max(train) + 2 < min(test)  # Gap respected

    def test_time_series_split_no_overlap(self):
        data = list(range(50))
        splits = FinancialDataSplitter.time_series_split(data, n_splits=3, gap=5)
        for train, test in splits:
            assert not set(train) & set(test)

    def test_time_series_split_too_small(self):
        with pytest.raises(ValueError):
            FinancialDataSplitter.time_series_split([1, 2], n_splits=5, gap=5)

    def test_purged_kfold_basic(self):
        data = list(range(100))
        splits = FinancialDataSplitter.purged_kfold(data, n_splits=5, embargo_pct=0.02)
        assert len(splits) == 5
        for train, test in splits:
            assert not set(train) & set(test)

    def test_purged_kfold_embargo(self):
        data = list(range(100))
        splits = FinancialDataSplitter.purged_kfold(data, n_splits=5, embargo_pct=0.05)
        for train, test in splits:
            # No train index within embargo distance of test
            test_min, test_max = min(test), max(test)
            embargo = 5  # 100 * 0.05
            for t in train:
                assert t < test_min - embargo or t >= test_max + embargo

    def test_purged_kfold_too_small(self):
        with pytest.raises(ValueError):
            FinancialDataSplitter.purged_kfold([1, 2], n_splits=5)

    def test_combinatorial_purged_basic(self):
        data = list(range(60))
        splits = FinancialDataSplitter.combinatorial_purged(data, n_splits=6, n_test_splits=2)
        # C(6,2) = 15 combinations
        assert len(splits) == 15
        for train, test in splits:
            assert not set(train) & set(test)
            assert sorted(train + test) == list(range(60))

    def test_combinatorial_purged_coverage(self):
        data = list(range(30))
        splits = FinancialDataSplitter.combinatorial_purged(data, n_splits=5, n_test_splits=2)
        # C(5,2) = 10
        assert len(splits) == 10

    def test_combinatorial_invalid_params(self):
        with pytest.raises(ValueError):
            FinancialDataSplitter.combinatorial_purged([1]*10, n_splits=5, n_test_splits=5)

    def test_combinatorial_too_small(self):
        with pytest.raises(ValueError):
            FinancialDataSplitter.combinatorial_purged([1, 2], n_splits=5, n_test_splits=2)


# ==================== Integration ====================

class TestMLPipelineIntegration:

    def test_pipeline_with_splitter_and_model(self):
        """End-to-end: feature pipeline -> split -> model select."""
        random.seed(123)
        n = 100
        data = {
            "close": [100 + i + random.gauss(0, 5) for i in range(n)],
            "volume": [1000 + random.gauss(0, 100) for _ in range(n)],
        }
        # Feature pipeline
        fp = FeaturePipeline()
        fp.add_step("lag", FeaturePipeline.lag_features(["close"], [1]))
        fp.add_step("roll", FeaturePipeline.rolling_features(["close"], [5]))
        features = fp.fit_transform(data)

        # Build X, y from features (skip Nones)
        close = features["close"]
        lag1 = features["close_lag1"]
        roll5 = features["close_roll5"]
        X, y = [], []
        for i in range(5, n):
            if lag1[i] is not None and roll5[i] is not None:
                X.append([lag1[i], roll5[i]])
                y.append(close[i])

        # Split
        splits = FinancialDataSplitter.time_series_split(X, n_splits=3, gap=2)
        assert len(splits) > 0

        # Model selection
        ms = ModelSelector()
        result = ms.auto_select(X, y)
        assert result["model"] is not None

    def test_prediction_tracking_flow(self):
        """Log predictions, update actuals, check report."""
        pt = PredictionTracker()
        pids = []
        for i in range(10):
            pid = pt.log_prediction("test_model", "AAPL", float(i * 2))
            pids.append(pid)

        for i, pid in enumerate(pids):
            pt.update_actual(pid, float(i * 2 + random.gauss(0, 0.5)))

        report = pt.accuracy_report("test_model")
        assert report["count"] == 10
        assert report["mse"] is not None

    def test_imports_from_init(self):
        """All new classes importable from src.ml."""
        from src.ml import FeaturePipeline, ModelSelector, PredictionTracker, FinancialDataSplitter
        assert FeaturePipeline is not None
        assert ModelSelector is not None
        assert PredictionTracker is not None
        assert FinancialDataSplitter is not None
