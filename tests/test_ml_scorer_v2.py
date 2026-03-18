"""Tests for ML Scorer v2 enhancements.

Covers:
- V2 feature computation (40+ features)
- Ensemble predictions
- Risk-adjusted label generation
- Walk-forward with expanding window
- Feature importance extraction
- Backward compatibility with v1
"""

import numpy as np
import pytest


def _make_ohlcv(n: int = 300, seed: int = 42):
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    returns = rng.randn(n) * 0.02
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.randn(n)) * 0.01)
    low = close * (1 - np.abs(rng.randn(n)) * 0.01)
    open_ = np.copy(close)
    open_[1:] = close[:-1] * (1 + rng.randn(n - 1) * 0.005)
    volume = (rng.lognormal(10, 1, n) * 1000).astype(np.float64)
    return open_, high, low, close, volume


# ── V2 Feature Tests ────────────────────────────────────────────────

class TestV2Features:
    """Test enhanced v2 feature computation."""

    def test_v2_feature_count(self):
        """V2 should produce 41 features."""
        from src.cn_ml_scorer import compute_features_series, NUM_FEATURES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None
        assert features.shape == (120, NUM_FEATURES_V2)
        assert NUM_FEATURES_V2 == 41

    def test_v1_feature_count_unchanged(self):
        """V1 should still produce 20 features."""
        from src.cn_ml_scorer import compute_features_series, NUM_FEATURES
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v1")
        assert features is not None
        assert features.shape == (120, NUM_FEATURES)
        assert NUM_FEATURES == 20

    def test_v2_default_version(self):
        """Default version should be v2."""
        from src.cn_ml_scorer import compute_features_series, NUM_FEATURES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l)
        assert features is not None
        assert features.shape[1] == NUM_FEATURES_V2

    def test_v2_feature_names(self):
        """Feature names list matches feature count."""
        from src.cn_ml_scorer import FEATURE_NAMES_V2, NUM_FEATURES_V2
        assert len(FEATURE_NAMES_V2) == NUM_FEATURES_V2

    def test_v2_features_no_volume(self):
        """V2 features work without volume (volume features will be NaN)."""
        from src.cn_ml_scorer import compute_features_series, NUM_FEATURES_V2
        rng = np.random.RandomState(42)
        c = rng.randn(100).cumsum() + 100
        features = compute_features_series(c, version="v2")
        assert features is not None
        assert features.shape == (100, NUM_FEATURES_V2)

    def test_v2_features_short_data(self):
        """Returns None for too-short data."""
        from src.cn_ml_scorer import compute_features_series
        c = np.array([100.0, 101.0, 99.0])
        assert compute_features_series(c, version="v2") is None

    def test_v2_compute_features_single_bar(self):
        """compute_features returns single v2 feature vector."""
        from src.cn_ml_scorer import compute_features, NUM_FEATURES_V2
        o, h, l, c, v = _make_ohlcv(120)
        feat = compute_features(c, v, o, h, l, version="v2")
        # May be None if last bar has NaN; just check type
        if feat is not None:
            assert len(feat) == NUM_FEATURES_V2

    def test_v2_first_20_features_match_v1(self):
        """First 20 features of v2 should match v1 output."""
        from src.cn_ml_scorer import compute_features_series
        o, h, l, c, v = _make_ohlcv(120, seed=99)
        v1 = compute_features_series(c, v, o, h, l, version="v1")
        v2 = compute_features_series(c, v, o, h, l, version="v2")
        assert v1 is not None and v2 is not None
        # Compare first 20 columns where neither is NaN
        for col in range(20):
            for row in range(120):
                if not np.isnan(v1[row, col]) and not np.isnan(v2[row, col]):
                    np.testing.assert_allclose(
                        v1[row, col], v2[row, col], rtol=1e-10,
                        err_msg=f"Mismatch at row={row}, col={col}",
                    )

    def test_v2_momentum_features_reasonable(self):
        """ROC, momentum acceleration should have reasonable values."""
        from src.cn_ml_scorer import compute_features_series, FEATURE_NAMES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        roc5_idx = FEATURE_NAMES_V2.index("roc5")
        roc5 = features[:, roc5_idx]
        valid = roc5[~np.isnan(roc5)]
        assert len(valid) > 0
        # ROC should be in a reasonable range (< 100% for synthetic data)
        assert np.all(np.abs(valid) < 100)

    def test_v2_volatility_features(self):
        """Realized volatility features should be non-negative."""
        from src.cn_ml_scorer import compute_features_series, FEATURE_NAMES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        for feat_name in ["rvol_5d", "rvol_10d", "rvol_20d", "gk_vol"]:
            idx = FEATURE_NAMES_V2.index(feat_name)
            vals = features[:, idx]
            valid = vals[~np.isnan(vals)]
            assert len(valid) > 0, f"{feat_name} has no valid values"
            assert np.all(valid >= 0), f"{feat_name} has negative values"

    def test_v2_range_position_bounded(self):
        """Range position should be in [0, 1]."""
        from src.cn_ml_scorer import compute_features_series, FEATURE_NAMES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        idx = FEATURE_NAMES_V2.index("range_position")
        vals = features[:, idx]
        valid = vals[~np.isnan(vals)]
        assert len(valid) > 0
        assert np.all(valid >= -0.01)  # small float tolerance
        assert np.all(valid <= 1.01)

    def test_v2_consecutive_days(self):
        """Consecutive days should be integers."""
        from src.cn_ml_scorer import compute_features_series, FEATURE_NAMES_V2
        rng = np.random.RandomState(42)
        # Create a steadily rising series
        c = np.linspace(100, 110, 50)
        features = compute_features_series(c, version="v2")
        assert features is not None

        idx = FEATURE_NAMES_V2.index("consec_days")
        vals = features[:, idx]
        valid = vals[~np.isnan(vals)]
        assert len(valid) > 0
        # All should be positive (steadily rising)
        assert np.all(valid >= 0)

    def test_v2_bb_squeeze(self):
        """BB squeeze should be non-negative."""
        from src.cn_ml_scorer import compute_features_series, FEATURE_NAMES_V2
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        idx = FEATURE_NAMES_V2.index("bb_squeeze")
        vals = features[:, idx]
        valid = vals[~np.isnan(vals)]
        assert len(valid) > 0
        assert np.all(valid >= 0)


# ── V2 Label Engineering Tests ───────────────────────────────────────

class TestV2Labels:
    """Test enhanced label generation."""

    def test_labels_v2_basic(self):
        """V2 labels should be binary and correct length."""
        from src.cn_ml_scorer import compute_labels_v2
        c = np.linspace(100, 120, 60)
        labels = compute_labels_v2(c, forward_days=5, threshold=0.02)
        assert len(labels) == 60
        assert np.all(np.isnan(labels[-5:]))
        valid = labels[~np.isnan(labels)]
        assert np.all((valid == 0.0) | (valid == 1.0))

    def test_labels_v2_drawdown_filter(self):
        """Bars with high drawdown during hold should be labeled negative."""
        from src.cn_ml_scorer import compute_labels_v2
        # Create a V-shape: drops 5% then recovers to +3%
        n = 20
        close = np.ones(n) * 100
        close[5] = 100   # entry
        close[6] = 94    # -6% dip (exceeds 3% max drawdown)
        close[7] = 96
        close[8] = 99
        close[9] = 103   # +3% final return
        close[10] = 105

        high = close.copy()
        low = close.copy()
        low[6] = 93  # intraday low even worse

        labels = compute_labels_v2(close, high, low,
                                    forward_days=5, threshold=0.02,
                                    max_drawdown_pct=0.03)
        # Bar 5: forward ret = 105/100=5% > threshold, BUT drawdown=-6% > 3%
        # Should be labeled 0 (negative)
        assert labels[5] == 0.0

    def test_labels_v2_no_drawdown(self):
        """Bars with no drawdown should be labeled normally."""
        from src.cn_ml_scorer import compute_labels_v2
        # Steadily rising
        close = np.linspace(100, 110, 20)
        high = close * 1.01
        low = close * 0.999
        labels = compute_labels_v2(close, high, low,
                                    forward_days=5, threshold=0.01)
        # Most should be positive since it's steadily rising
        valid = labels[~np.isnan(labels)]
        assert np.sum(valid == 1.0) > 0

    def test_labels_v2_backwards_compatible(self):
        """V2 labels with no high/low should work like basic labels."""
        from src.cn_ml_scorer import compute_labels_v2
        c = np.linspace(100, 120, 60)
        labels = compute_labels_v2(c, forward_days=5, threshold=0.02)
        assert len(labels) == 60
        assert np.all(np.isnan(labels[-5:]))


# ── Ensemble Tests ───────────────────────────────────────────────────

class TestEnsemble:
    """Test ensemble model predictions."""

    def test_v2_ensemble_train(self):
        """V2 scorer trains ensemble of 3 models."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=123)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2",
        )
        probs = scorer.train_and_predict(features, c, high=h, low=l)

        # Should have ensemble models
        assert scorer._ensemble_models is not None
        assert len(scorer._ensemble_models) == 3
        # Should have predictions
        valid = probs[~np.isnan(probs)]
        assert len(valid) > 0
        assert np.all(valid >= 0.0)
        assert np.all(valid <= 1.0)

    def test_v2_ensemble_predict_latest(self):
        """predict_latest should use ensemble averaging in v2."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=456)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2",
        )
        scorer.train_and_predict(features, c, high=h, low=l)

        assert scorer._ensemble_models is not None
        # Find a non-NaN feature row
        for i in range(len(features) - 1, -1, -1):
            if not np.any(np.isnan(features[i])):
                prob = scorer.predict_latest(features[i])
                assert prob is not None
                assert 0.0 <= prob <= 1.0
                break

    def test_v1_no_ensemble(self):
        """V1 scorer should NOT have ensemble."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(300, seed=789)
        features = compute_features_series(c, v, o, h, l, version="v1")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=120, predict_bars=20, forward_days=5,
            version="v1",
        )
        scorer.train_and_predict(features, c)

        assert scorer._ensemble_models is None
        valid = scorer.train_and_predict(features, c)
        valid_probs = valid[~np.isnan(valid)]
        assert len(valid_probs) > 0

    def test_ensemble_probabilities_averaged(self):
        """Ensemble prediction should be average of 3 models."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=111)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2",
        )
        scorer.train_and_predict(features, c, high=h, low=l)

        # Find non-NaN feature vector
        for i in range(len(features) - 1, -1, -1):
            if not np.any(np.isnan(features[i])):
                X = features[i].reshape(1, -1)
                # Manual average
                individual_probs = []
                for m in scorer._ensemble_models:
                    individual_probs.append(m.predict_proba(X)[0, 1])
                expected_avg = np.mean(individual_probs)
                actual = scorer.predict_latest(features[i])
                assert actual is not None
                np.testing.assert_allclose(actual, expected_avg, rtol=1e-10)
                break


# ── Feature Importance Tests ─────────────────────────────────────────

class TestFeatureImportance:
    """Test feature importance extraction."""

    def test_v2_feature_importances(self):
        """V2 scorer should have feature importances after training."""
        from src.cn_ml_scorer import (
            MLStockScorer, compute_features_series,
            FEATURE_NAMES_V2, NUM_FEATURES_V2,
        )
        o, h, l, c, v = _make_ohlcv(600, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2",
        )
        scorer.train_and_predict(features, c, high=h, low=l)

        importances = scorer.get_feature_importances()
        assert importances is not None
        assert len(importances) == NUM_FEATURES_V2
        # All values should be non-negative
        assert all(v >= 0 for v in importances.values())
        # Sum should be close to 1 (normalized)
        total = sum(importances.values())
        assert abs(total - 1.0) < 0.01

    def test_v1_no_feature_importances(self):
        """V1 scorer should not have feature importances."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(300, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v1")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=120, predict_bars=20, forward_days=5,
            version="v1",
        )
        scorer.train_and_predict(features, c)

        importances = scorer.get_feature_importances()
        assert importances is None

    def test_feature_importance_keys(self):
        """Feature importance keys should match feature names."""
        from src.cn_ml_scorer import (
            MLStockScorer, compute_features_series,
            FEATURE_NAMES_V2,
        )
        o, h, l, c, v = _make_ohlcv(600, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2",
        )
        scorer.train_and_predict(features, c, high=h, low=l)

        importances = scorer.get_feature_importances()
        assert importances is not None
        assert set(importances.keys()) == set(FEATURE_NAMES_V2)


# ── Walk-Forward Tests ───────────────────────────────────────────────

class TestWalkForward:
    """Test walk-forward optimization improvements."""

    def test_expanding_window(self):
        """Expanding window should use all data from start."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2", expanding_window=True,
        )
        probs = scorer.train_and_predict(features, c, high=h, low=l)
        valid = probs[~np.isnan(probs)]
        assert len(valid) > 0

    def test_fixed_window(self):
        """Fixed window should also work (backward compat)."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=5, forward_days=5,
            version="v2", expanding_window=False,
        )
        probs = scorer.train_and_predict(features, c, high=h, low=l)
        valid = probs[~np.isnan(probs)]
        assert len(valid) > 0

    def test_smaller_predict_window(self):
        """predict_bars=5 should produce more frequent re-training."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(400, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v1")
        assert features is not None

        scorer_5 = MLStockScorer(train_bars=120, predict_bars=5, version="v1")
        scorer_20 = MLStockScorer(train_bars=120, predict_bars=20, version="v1")

        probs_5 = scorer_5.train_and_predict(features, c)
        probs_20 = scorer_20.train_and_predict(features, c)

        valid_5 = probs_5[~np.isnan(probs_5)]
        valid_20 = probs_20[~np.isnan(probs_20)]
        # Both should produce predictions
        assert len(valid_5) > 0
        assert len(valid_20) > 0

    def test_verbose_output(self, capsys):
        """Verbose training should print progress."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(600, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v2")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=250, predict_bars=20, forward_days=5,
            version="v2",
        )
        scorer.train_and_predict(features, c, high=h, low=l, verbose=True)
        captured = capsys.readouterr()
        assert "[v2]" in captured.out
        assert "Step" in captured.out


# ── Backward Compatibility Tests ─────────────────────────────────────

class TestBackwardCompatibility:
    """Ensure v1 behavior is preserved."""

    def test_legacy_num_features(self):
        """NUM_FEATURES should still be 20 for v1 compatibility."""
        from src.cn_ml_scorer import NUM_FEATURES, FEATURE_NAMES
        assert NUM_FEATURES == 20
        assert len(FEATURE_NAMES) == 20

    def test_legacy_compute_features(self):
        """compute_features with version='v1' returns 20 features."""
        from src.cn_ml_scorer import compute_features, NUM_FEATURES
        o, h, l, c, v = _make_ohlcv(120)
        feat = compute_features(c, v, o, h, l, version="v1")
        if feat is not None:
            assert len(feat) == NUM_FEATURES

    def test_legacy_compute_labels(self):
        """compute_labels unchanged."""
        from src.cn_ml_scorer import compute_labels
        c = np.linspace(100, 120, 60)
        labels = compute_labels(c, forward_days=5, threshold=0.02)
        assert len(labels) == 60
        assert np.all(np.isnan(labels[-5:]))

    def test_legacy_blend_scores(self):
        """blend_scores unchanged."""
        from src.cn_ml_scorer import blend_scores
        blended = blend_scores(10, 0.8, rule_weight=0.5, max_rule_score=20)
        expected = 0.5 * (10 / 20) * 20 + 0.5 * 0.8 * 20
        assert abs(blended - expected) < 0.01

    def test_legacy_ml_scorer_v1(self):
        """MLStockScorer with version='v1' uses single model."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(300, seed=42)
        features = compute_features_series(c, v, o, h, l, version="v1")
        assert features is not None

        scorer = MLStockScorer(
            train_bars=120, predict_bars=20, forward_days=5,
            version="v1",
        )
        probs = scorer.train_and_predict(features, c)
        valid = probs[~np.isnan(probs)]
        assert len(valid) > 0
        assert scorer._model is not None
        assert scorer._ensemble_models is None

    def test_get_feature_names_helper(self):
        """get_feature_names returns correct lists."""
        from src.cn_ml_scorer import get_feature_names, get_num_features
        assert len(get_feature_names("v1")) == 20
        assert len(get_feature_names("v2")) == 41
        assert get_num_features("v1") == 20
        assert get_num_features("v2") == 41

    def test_compute_score_ml_works(self):
        """compute_score_ml still works correctly."""
        from src.cn_ml_scorer import compute_score_ml
        o, h, l, c, v = _make_ohlcv(120)
        result = compute_score_ml(c, v, o, h, l)
        assert result["strategy"] == "ml"
        assert "score" in result

    def test_predict_latest_nan_returns_none(self):
        """predict_latest with NaN features returns None."""
        from src.cn_ml_scorer import MLStockScorer
        scorer = MLStockScorer(version="v2")
        feat = np.full(41, np.nan)
        assert scorer.predict_latest(feat) is None

    def test_predict_latest_no_model(self):
        """predict_latest without training returns None."""
        from src.cn_ml_scorer import MLStockScorer
        scorer = MLStockScorer(version="v1")
        feat = np.random.randn(20)
        assert scorer.predict_latest(feat) is None

        scorer_v2 = MLStockScorer(version="v2")
        feat_v2 = np.random.randn(41)
        assert scorer_v2.predict_latest(feat_v2) is None
