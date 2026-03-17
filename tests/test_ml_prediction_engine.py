"""Tests for ML Prediction Engine v5.3.0.

Covers:
- DecisionTreeClassifier (pure Python)
- RandomForestClassifier (pure Python)
- GradientBooster (pure Python)
- WalkForwardValidator
- FeatureEngine enhancements
- CLI predict subcommand
- Integration tests
"""

import math
import subprocess
import sys

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# DecisionTreeClassifier
# ---------------------------------------------------------------------------

class TestDecisionTreeClassifier:
    def _cls(self):
        from src.ml.models import DecisionTreeClassifier
        return DecisionTreeClassifier

    def test_fit_predict_basic(self):
        DT = self._cls()
        X = [[0, 0], [0, 1], [1, 0], [1, 1]]
        y = [0, 0, 1, 1]
        model = DT(max_depth=3)
        model.fit(X, y)
        preds = model.predict(X)
        assert preds == [0, 0, 1, 1]

    def test_single_class(self):
        DT = self._cls()
        X = [[1], [2], [3]]
        y = [1, 1, 1]
        model = DT().fit(X, y)
        assert model.predict([[5]]) == [1]

    def test_max_depth_1(self):
        DT = self._cls()
        X = [[i] for i in range(10)]
        y = [0]*5 + [1]*5
        model = DT(max_depth=1).fit(X, y)
        preds = model.predict(X)
        assert sum(preds) >= 3  # at least some 1s

    def test_predict_before_fit(self):
        DT = self._cls()
        model = DT()
        preds = model.predict([[1, 2]])
        assert preds == [0]

    def test_multiclass(self):
        DT = self._cls()
        X = [[0], [1], [2], [3], [4], [5]]
        y = [0, 0, 1, 1, 2, 2]
        model = DT(max_depth=5).fit(X, y)
        preds = model.predict(X)
        # Should get most right
        correct = sum(1 for p, a in zip(preds, y) if p == a)
        assert correct >= 4

    def test_gini_pure(self):
        DT = self._cls()
        model = DT()
        assert model._gini([1, 1, 1]) == 0.0

    def test_gini_mixed(self):
        DT = self._cls()
        model = DT()
        g = model._gini([0, 1])
        assert abs(g - 0.5) < 1e-10

    def test_large_dataset(self):
        DT = self._cls()
        import random
        rng = random.Random(42)
        X = [[rng.random(), rng.random()] for _ in range(200)]
        y = [1 if x[0] + x[1] > 1.0 else 0 for x in X]
        model = DT(max_depth=5).fit(X, y)
        preds = model.predict(X)
        acc = sum(1 for p, a in zip(preds, y) if p == a) / len(y)
        assert acc > 0.7


# ---------------------------------------------------------------------------
# RandomForestClassifier
# ---------------------------------------------------------------------------

class TestRandomForestClassifier:
    def _cls(self):
        from src.ml.models import RandomForestClassifier
        return RandomForestClassifier

    def test_fit_predict(self):
        RF = self._cls()
        X = [[0, 0], [0, 1], [1, 0], [1, 1]] * 5
        y = [0, 0, 1, 1] * 5
        model = RF(n_trees=5, max_depth=3).fit(X, y)
        preds = model.predict(X)
        acc = sum(1 for p, a in zip(preds, y) if p == a) / len(y)
        assert acc > 0.6

    def test_predict_before_fit(self):
        RF = self._cls()
        model = RF()
        assert model.predict([[1, 2]]) == [0]

    def test_single_tree(self):
        RF = self._cls()
        X = [[i] for i in range(20)]
        y = [0]*10 + [1]*10
        model = RF(n_trees=1, max_depth=3).fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 20

    def test_many_trees(self):
        RF = self._cls()
        import random
        rng = random.Random(42)
        X = [[rng.random(), rng.random()] for _ in range(100)]
        y = [1 if x[0] > 0.5 else 0 for x in X]
        model = RF(n_trees=20, max_depth=4).fit(X, y)
        preds = model.predict(X)
        acc = sum(1 for p, a in zip(preds, y) if p == a) / len(y)
        assert acc > 0.7

    def test_majority_vote(self):
        """Verify majority vote produces valid labels."""
        RF = self._cls()
        X = [[0], [1], [2], [3]]
        y = [0, 0, 1, 1]
        model = RF(n_trees=3).fit(X, y)
        preds = model.predict(X)
        assert all(p in (0, 1) for p in preds)


# ---------------------------------------------------------------------------
# GradientBooster
# ---------------------------------------------------------------------------

class TestGradientBooster:
    def _cls(self):
        from src.ml.models import GradientBooster
        return GradientBooster

    def test_fit_predict_binary(self):
        GB = self._cls()
        X = [[i] for i in range(20)]
        y = [0]*10 + [1]*10
        model = GB(n_rounds=30, lr=0.3).fit(X, y)
        preds = model.predict(X)
        acc = sum(1 for p, a in zip(preds, y) if p == a) / len(y)
        assert acc > 0.6

    def test_predict_proba(self):
        GB = self._cls()
        X = [[0], [1], [2], [3]]
        y = [0, 0, 1, 1]
        model = GB(n_rounds=20, lr=0.5).fit(X, y)
        probs = model.predict_proba(X)
        assert len(probs) == 4
        assert all(0 <= p <= 1 for p in probs)

    def test_all_same_class(self):
        GB = self._cls()
        X = [[1], [2], [3]]
        y = [1, 1, 1]
        # Should not crash even with log(odds) edge case
        model = GB(n_rounds=5).fit(X, y)
        preds = model.predict(X)
        assert len(preds) == 3

    def test_predict_before_fit(self):
        GB = self._cls()
        model = GB()
        # stumps empty, init_pred=0 => prob=0.5 => pred=1
        preds = model.predict([[1, 2]])
        assert len(preds) == 1

    def test_learning_rate_effect(self):
        GB = self._cls()
        import random
        rng = random.Random(42)
        X = [[rng.random()] for _ in range(50)]
        y = [1 if x[0] > 0.5 else 0 for x in X]
        model_fast = GB(n_rounds=30, lr=0.5).fit(X, y)
        model_slow = GB(n_rounds=30, lr=0.01).fit(X, y)
        # Fast should converge better on training data
        acc_fast = sum(1 for p, a in zip(model_fast.predict(X), y) if p == a) / len(y)
        acc_slow = sum(1 for p, a in zip(model_slow.predict(X), y) if p == a) / len(y)
        assert acc_fast >= acc_slow - 0.1  # fast at least close

    def test_two_features(self):
        GB = self._cls()
        X = [[0, 0], [0, 1], [1, 0], [1, 1]] * 10
        y = [0, 1, 1, 1] * 10  # OR gate
        model = GB(n_rounds=50, lr=0.3, max_depth=2).fit(X, y)
        preds = model.predict(X)
        acc = sum(1 for p, a in zip(preds, y) if p == a) / len(y)
        assert acc > 0.6


# ---------------------------------------------------------------------------
# WalkForwardValidator
# ---------------------------------------------------------------------------

class TestWalkForwardValidator:
    def _cls(self):
        from src.ml.walk_forward import WalkForwardValidator
        return WalkForwardValidator

    def test_split_basic(self):
        WFV = self._cls()
        v = WFV(train_size=10, test_size=5)
        splits = v.split(list(range(30)))
        assert len(splits) >= 2
        for train_idx, test_idx in splits:
            assert len(train_idx) == 10
            assert len(test_idx) == 5
            assert max(train_idx) < min(test_idx)

    def test_split_with_gap(self):
        WFV = self._cls()
        v = WFV(train_size=10, test_size=5, gap=3)
        splits = v.split(list(range(50)))
        for train_idx, test_idx in splits:
            assert min(test_idx) - max(train_idx) > 3

    def test_split_too_small(self):
        WFV = self._cls()
        v = WFV(train_size=10, test_size=5)
        splits = v.split(list(range(5)))
        assert splits == []

    def test_invalid_params(self):
        WFV = self._cls()
        with pytest.raises(ValueError):
            WFV(train_size=0, test_size=5)
        with pytest.raises(ValueError):
            WFV(train_size=5, test_size=0)
        with pytest.raises(ValueError):
            WFV(train_size=5, test_size=5, gap=-1)

    def test_evaluate_simple(self):
        WFV = self._cls()
        from src.ml.models import DecisionTreeClassifier

        # Generate separable data
        data = []
        for i in range(60):
            x = i / 60.0
            data.append({"f1": x, "f2": x * 2, "label": 1 if x > 0.5 else 0})

        v = WFV(train_size=30, test_size=10)
        model = DecisionTreeClassifier(max_depth=3)
        result = v.evaluate(model, data, ["f1", "f2"], "label")
        assert result["n_splits"] >= 1
        assert 0 <= result["accuracy"] <= 1

    def test_evaluate_with_extractor(self):
        WFV = self._cls()
        from src.ml.models import DecisionTreeClassifier

        data = list(range(60))

        def extractor(slice_, features):
            X = [[v / 60.0] for v in slice_]
            y = [1 if v > 30 else 0 for v in slice_]
            return X, y

        v = WFV(train_size=30, test_size=10)
        model = DecisionTreeClassifier(max_depth=3)
        result = v.evaluate(model, data, ["x"], "y", feature_extractor=extractor)
        assert result["n_splits"] >= 1

    def test_report_empty(self):
        WFV = self._cls()
        v = WFV(train_size=10, test_size=5)
        report = v.report()
        assert "No evaluation" in report

    def test_report_after_evaluate(self):
        WFV = self._cls()
        from src.ml.models import DecisionTreeClassifier

        data = [{"f": float(i), "y": 1 if i > 25 else 0} for i in range(60)]
        v = WFV(train_size=30, test_size=10)
        model = DecisionTreeClassifier(max_depth=3)
        v.evaluate(model, data, ["f"], "y")
        report = v.report()
        assert "Walk-Forward" in report
        assert "accuracy" in report


# ---------------------------------------------------------------------------
# FeatureEngine additional tests
# ---------------------------------------------------------------------------

class TestFeatureEngine:
    def _make(self, n=100):
        from src.ml.features import FeatureEngine
        rng = np.random.RandomState(42)
        close = 100 + np.cumsum(rng.randn(n) * 0.5)
        high = close + abs(rng.randn(n)) * 0.3
        low = close - abs(rng.randn(n)) * 0.3
        volume = rng.randint(1000, 10000, size=n).astype(float)
        return FeatureEngine(close, high, low, volume)

    def test_returns(self):
        fe = self._make()
        r = fe.returns(1)
        assert len(r) == 100
        assert np.isnan(r[0])
        assert not np.isnan(r[5])

    def test_log_returns(self):
        fe = self._make()
        lr = fe.log_returns(1)
        assert np.isnan(lr[0])

    def test_rolling_volatility(self):
        fe = self._make()
        vol = fe.rolling_volatility(21)
        assert np.isnan(vol[10])
        assert not np.isnan(vol[50])

    def test_rsi(self):
        fe = self._make()
        rsi = fe.rsi(14)
        valid = rsi[~np.isnan(rsi)]
        assert len(valid) > 0
        assert all(0 <= v <= 100 for v in valid)

    def test_macd(self):
        fe = self._make()
        macd_line, signal, hist = fe.macd()
        assert len(macd_line) == 100
        # histogram = macd - signal
        valid_idx = ~(np.isnan(macd_line) | np.isnan(signal) | np.isnan(hist))
        np.testing.assert_allclose(hist[valid_idx], (macd_line - signal)[valid_idx], atol=1e-10)

    def test_generate_all(self):
        fe = self._make()
        features = fe.generate_all()
        assert isinstance(features, dict)
        assert "rsi_14" in features
        assert "macd" in features
        assert "volatility_21d" in features
        assert len(features) > 10

    def test_obv(self):
        fe = self._make()
        obv = fe.obv()
        assert len(obv) == 100
        assert obv[0] == 0.0

    def test_vwap_ratio(self):
        fe = self._make()
        ratio = fe.vwap_ratio(20)
        valid = ratio[~np.isnan(ratio)]
        assert len(valid) > 0
        assert all(v > 0 for v in valid)

    def test_adx(self):
        fe = self._make()
        adx = fe.adx(14)
        assert len(adx) == 100

    def test_bollinger_band_width(self):
        fe = self._make()
        bb = fe.bollinger_band_width()
        valid = bb[~np.isnan(bb)]
        assert len(valid) > 0
        assert all(v >= 0 for v in valid)

    def test_cross_sectional_zscore(self):
        from src.ml.features import FeatureEngine
        matrix = {
            "AAPL": np.array([1.0, 2.0, 3.0]),
            "GOOG": np.array([2.0, 4.0, 6.0]),
            "MSFT": np.array([3.0, 6.0, 9.0]),
        }
        result = FeatureEngine.cross_sectional_zscore(matrix)
        assert "AAPL" in result
        # First element: AAPL=1, GOOG=2, MSFT=3, mean=2, std=1 => AAPL z=-1
        assert abs(result["AAPL"][0] - (-1.0)) < 0.01


# ---------------------------------------------------------------------------
# Import / __init__ tests
# ---------------------------------------------------------------------------

class TestImports:
    def test_import_decision_tree(self):
        from src.ml import DecisionTreeClassifier
        assert DecisionTreeClassifier is not None

    def test_import_random_forest(self):
        from src.ml import RandomForestClassifier
        assert RandomForestClassifier is not None

    def test_import_gradient_booster(self):
        from src.ml import GradientBooster
        assert GradientBooster is not None

    def test_import_walk_forward_validator(self):
        from src.ml import WalkForwardValidator
        assert WalkForwardValidator is not None


# ---------------------------------------------------------------------------
# CLI predict tests
# ---------------------------------------------------------------------------

class TestPredictCLI:
    def test_predict_run_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "predict", "run", "--help"],
            capture_output=True, text=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
        )
        assert "symbol" in result.stdout.lower() or result.returncode == 0

    def test_predict_backtest_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "predict", "backtest", "--help"],
            capture_output=True, text=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
        )
        assert "symbol" in result.stdout.lower() or result.returncode == 0


# ---------------------------------------------------------------------------
# Integration: model + walk-forward
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_decision_tree_walk_forward(self):
        from src.ml.models import DecisionTreeClassifier
        from src.ml.walk_forward import WalkForwardValidator

        data = [{"f": float(i % 10), "y": 1 if i % 10 > 5 else 0} for i in range(80)]
        wfv = WalkForwardValidator(train_size=40, test_size=10)
        model = DecisionTreeClassifier(max_depth=3)
        result = wfv.evaluate(model, data, ["f"], "y")
        assert result["n_splits"] >= 1

    def test_random_forest_walk_forward(self):
        from src.ml.models import RandomForestClassifier
        from src.ml.walk_forward import WalkForwardValidator

        data = [{"f1": float(i), "f2": float(i * 2), "y": 1 if i > 40 else 0} for i in range(80)]
        wfv = WalkForwardValidator(train_size=40, test_size=10)
        model = RandomForestClassifier(n_trees=5, max_depth=3)
        result = wfv.evaluate(model, data, ["f1", "f2"], "y")
        assert result["n_splits"] >= 1

    def test_gradient_boost_walk_forward(self):
        from src.ml.models import GradientBooster
        from src.ml.walk_forward import WalkForwardValidator

        data = [{"f": float(i), "y": 1 if i > 40 else 0} for i in range(80)]
        wfv = WalkForwardValidator(train_size=40, test_size=10)
        model = GradientBooster(n_rounds=20, lr=0.3)
        result = wfv.evaluate(model, data, ["f"], "y")
        assert result["n_splits"] >= 1
        report = wfv.report()
        assert "Walk-Forward" in report

    def test_feature_engine_to_model(self):
        """End-to-end: generate features -> build dataset -> train model."""
        from src.ml.features import FeatureEngine
        from src.ml.models import GradientBooster

        rng = np.random.RandomState(42)
        close = 100 + np.cumsum(rng.randn(200) * 0.5)
        fe = FeatureEngine(close)
        rsi = fe.rsi(14)
        ret = fe.returns(5)

        # Build labeled dataset (next-5d return > 0 => buy)
        data_X = []
        data_y = []
        for i in range(50, 190):
            if np.isnan(rsi[i]) or np.isnan(ret[i]):
                continue
            data_X.append([rsi[i]])
            # Forward return
            fwd = close[min(i + 5, 199)] / close[i] - 1
            data_y.append(1 if fwd > 0 else 0)

        model = GradientBooster(n_rounds=30, lr=0.3)
        model.fit(data_X, data_y)
        preds = model.predict(data_X)
        assert len(preds) == len(data_y)
        assert all(p in (0, 1) for p in preds)
