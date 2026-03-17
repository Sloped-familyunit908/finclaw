"""
Tests for v1.5.0 ML integration:
- Feature engineering
- ML models (linear regression, MA predictor, regime classifier, ensemble)
- Sentiment analyzer
- Alpha model
- Walk-forward pipeline
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml.features import FeatureEngine
from src.ml.models import (
    LinearRegression,
    MAPredictor,
    RegimeClassifier,
    EnsembleModel,
    RandomForestPredictor,
    XGBoostPredictor,
    walk_forward_split,
)
from src.ml.sentiment import SimpleSentiment
from src.ml.alpha import AlphaModel, Signal
from src.ml.pipeline import (
    WalkForwardPipeline,
    PipelineMetrics,
    information_coefficient,
    rank_information_coefficient,
    portfolio_turnover,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def price_data():
    """Generate synthetic OHLCV data (300 bars)."""
    np.random.seed(42)
    n = 300
    returns = np.random.normal(0.0005, 0.02, n)
    close = 100.0 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    volume = np.random.randint(1000, 100000, n).astype(float)
    return close, high, low, volume


@pytest.fixture
def feature_engine(price_data):
    close, high, low, volume = price_data
    return FeatureEngine(close, high, low, volume)


# ============================================================
# Feature Engineering Tests
# ============================================================

class TestFeatureEngine:
    def test_returns_1d(self, feature_engine):
        r = feature_engine.returns(1)
        assert len(r) == 300
        assert np.isnan(r[0])
        assert not np.isnan(r[1])

    def test_returns_periods(self, feature_engine):
        for p in (1, 5, 21, 63, 252):
            r = feature_engine.returns(p)
            assert np.isnan(r[p - 1])
            if p < 300:
                assert not np.isnan(r[p])

    def test_log_returns(self, feature_engine):
        lr = feature_engine.log_returns(1)
        r = feature_engine.returns(1)
        # log(1+r) ≈ r for small r
        mask = ~(np.isnan(lr) | np.isnan(r))
        np.testing.assert_allclose(lr[mask], np.log(1 + r[mask]), rtol=1e-10)

    def test_rolling_volatility(self, feature_engine):
        vol = feature_engine.rolling_volatility(21)
        assert np.isnan(vol[0])
        # Vol should be positive where defined
        valid = vol[~np.isnan(vol)]
        assert len(valid) > 0
        assert np.all(valid >= 0)

    def test_rsi_range(self, feature_engine):
        rsi = feature_engine.rsi(14)
        valid = rsi[~np.isnan(rsi)]
        assert len(valid) > 0
        assert np.all(valid >= 0)
        assert np.all(valid <= 100)

    def test_macd(self, feature_engine):
        macd_line, signal_line, histogram = feature_engine.macd()
        assert len(macd_line) == 300
        # Histogram = MACD - Signal
        mask = ~(np.isnan(macd_line) | np.isnan(signal_line))
        np.testing.assert_allclose(histogram[mask], macd_line[mask] - signal_line[mask], atol=1e-10)

    def test_rate_of_change(self, feature_engine):
        roc = feature_engine.rate_of_change(10)
        assert np.isnan(roc[9])
        assert not np.isnan(roc[10])

    def test_stochastic_oscillator(self, feature_engine):
        k, d = feature_engine.stochastic_oscillator()
        valid_k = k[~np.isnan(k)]
        assert len(valid_k) > 0
        assert np.all(valid_k >= 0)
        assert np.all(valid_k <= 100)

    def test_obv(self, feature_engine):
        obv = feature_engine.obv()
        assert len(obv) == 300
        assert obv[0] == 0.0

    def test_vwap_ratio(self, feature_engine):
        vr = feature_engine.vwap_ratio(20)
        valid = vr[~np.isnan(vr)]
        assert len(valid) > 0
        # Should be around 1.0
        assert np.mean(valid) > 0.9
        assert np.mean(valid) < 1.1

    def test_volume_momentum(self, feature_engine):
        vm = feature_engine.volume_momentum(20)
        valid = vm[~np.isnan(vm)]
        assert len(valid) > 0

    def test_sma_ratio(self, feature_engine):
        sr = feature_engine.sma_ratio(20, 50)
        valid = sr[~np.isnan(sr)]
        assert len(valid) > 0
        assert np.mean(valid) > 0.8

    def test_ema_ratio(self, feature_engine):
        er = feature_engine.ema_ratio(12, 26)
        valid = er[~np.isnan(er)]
        assert len(valid) > 0

    def test_adx(self, feature_engine):
        adx = feature_engine.adx(14)
        valid = adx[~np.isnan(adx)]
        assert len(valid) > 0

    def test_bollinger_band_width(self, feature_engine):
        bb = feature_engine.bollinger_band_width()
        valid = bb[~np.isnan(bb)]
        assert len(valid) > 0
        assert np.all(valid >= 0)

    def test_distance_from_52w(self, feature_engine):
        hd, ld = feature_engine.distance_from_52w()
        valid_h = hd[~np.isnan(hd)]
        valid_l = ld[~np.isnan(ld)]
        assert len(valid_h) > 0
        # Distance from high should be <= 0
        assert np.all(valid_h <= 1e-10)
        # Distance from low should be >= 0
        assert np.all(valid_l >= -1e-10)

    def test_generate_all(self, feature_engine):
        features = feature_engine.generate_all()
        assert len(features) >= 20
        for name, arr in features.items():
            assert len(arr) == 300, f"Feature {name} has wrong length"

    def test_cross_sectional_zscore(self):
        np.random.seed(1)
        matrix = {
            "AAPL": np.array([1.0, 2.0, 3.0]),
            "GOOGL": np.array([2.0, 4.0, 6.0]),
            "MSFT": np.array([3.0, 6.0, 9.0]),
        }
        result = FeatureEngine.cross_sectional_zscore(matrix)
        assert set(result.keys()) == {"AAPL", "GOOGL", "MSFT"}
        # At each time step, z-scores should sum to ~0
        for i in range(3):
            vals = [result[t][i] for t in result]
            assert abs(sum(vals)) < 1e-10

    def test_cross_sectional_zscore_empty(self):
        result = FeatureEngine.cross_sectional_zscore({})
        assert result == {}

    def test_multi_period_returns(self, feature_engine):
        mpr = feature_engine.multi_period_returns()
        assert "ret_1d" in mpr
        assert "ret_252d" in mpr

    def test_close_only_init(self):
        """Engine works with close prices only."""
        close = np.linspace(100, 110, 50)
        engine = FeatureEngine(close)
        features = engine.generate_all()
        assert len(features) >= 20


# ============================================================
# Model Tests
# ============================================================

class TestLinearRegression:
    def test_fit_predict(self):
        np.random.seed(10)
        X = np.random.randn(100, 3)
        true_coefs = np.array([1.5, -0.5, 2.0])
        y = X @ true_coefs + 0.3 + np.random.randn(100) * 0.1
        model = LinearRegression()
        model.fit(X, y)
        np.testing.assert_allclose(model.coefficients, true_coefs, atol=0.2)
        assert abs(model.intercept - 0.3) < 0.2
        r2 = model.score(X, y)
        assert r2 > 0.9

    def test_predict_without_fit(self):
        model = LinearRegression()
        result = model.predict(np.array([[1, 2, 3]]))
        assert len(result) == 1

    def test_handles_nan(self):
        X = np.array([[1, 2], [np.nan, 3], [3, 4], [4, 5]])
        y = np.array([1, np.nan, 3, 4])
        model = LinearRegression()
        model.fit(X, y)
        assert model.coefficients is not None


class TestMAPredictor:
    def test_bullish_trend(self):
        prices = np.linspace(100, 150, 50)
        pred = MAPredictor(5, 20)
        signals = pred.predict(prices)
        # In uptrend, should be mostly +1
        assert np.sum(signals[19:] == 1.0) > len(signals[19:]) * 0.5

    def test_output_shape(self):
        prices = np.random.randn(100) * 10 + 100
        pred = MAPredictor()
        signals = pred.predict(prices)
        assert len(signals) == 100


class TestRegimeClassifier:
    def test_bull_regime(self):
        np.random.seed(5)
        returns = np.random.normal(0.001, 0.01, 200)
        clf = RegimeClassifier(lookback=63)
        regimes = clf.classify(returns)
        # Should detect some regime
        assert "unknown" not in regimes[63:]

    def test_classify_numeric(self):
        np.random.seed(5)
        returns = np.random.normal(0.001, 0.01, 200)
        clf = RegimeClassifier(lookback=63)
        numeric = clf.classify_numeric(returns)
        assert len(numeric) == 200
        valid = numeric[~np.isnan(numeric)]
        assert all(v in (-1.0, 0.0, 1.0) for v in valid)


class TestEnsembleModel:
    def test_combine_equal_weights(self):
        s1 = np.array([1.0, 2.0, 3.0])
        s2 = np.array([3.0, 2.0, 1.0])
        ensemble = EnsembleModel()
        result = ensemble.combine([s1, s2])
        np.testing.assert_allclose(result, [2.0, 2.0, 2.0])

    def test_combine_with_nan(self):
        s1 = np.array([1.0, np.nan, 3.0])
        s2 = np.array([2.0, 2.0, np.nan])
        ensemble = EnsembleModel()
        result = ensemble.combine([s1, s2])
        assert not np.isnan(result[0])
        assert not np.isnan(result[1])
        assert not np.isnan(result[2])

    def test_custom_weights(self):
        s1 = np.array([10.0])
        s2 = np.array([0.0])
        ensemble = EnsembleModel(weights=[3.0, 1.0])
        result = ensemble.combine([s1, s2])
        assert result[0] == pytest.approx(7.5)

    def test_empty(self):
        ensemble = EnsembleModel()
        result = ensemble.combine([])
        assert len(result) == 0


# ============================================================
# Sentiment Tests
# ============================================================

class TestSentiment:
    def test_bullish_text(self):
        s = SimpleSentiment()
        score = s.analyze("Strong growth and momentum, beat expectations")
        assert score > 0

    def test_bearish_text(self):
        s = SimpleSentiment()
        score = s.analyze("Weak results, risk of decline and downgrade")
        assert score < 0

    def test_neutral_text(self):
        s = SimpleSentiment()
        score = s.analyze("The company reported quarterly results today")
        assert score == 0.0

    def test_empty_text(self):
        s = SimpleSentiment()
        assert s.analyze("") == 0.0

    def test_batch(self):
        s = SimpleSentiment()
        results = s.analyze_batch(["strong growth", "weak decline", "hello world"])
        assert len(results) == 3
        assert results[0] > 0
        assert results[1] < 0
        assert results[2] == 0.0

    def test_get_keywords_found(self):
        s = SimpleSentiment()
        found = s.get_keywords_found("Strong growth and risk")
        assert "strong" in found
        assert "growth" in found
        assert "risk" in found

    def test_score_bounded(self):
        s = SimpleSentiment()
        score = s.analyze("growth beat strong upgrade momentum bullish rally surge")
        assert -1.0 <= score <= 1.0


# ============================================================
# Alpha Model Tests
# ============================================================

class TestAlphaModel:
    def test_generate_alphas(self):
        signals = [
            Signal("momentum", lambda t: {"AAPL": 0.5, "GOOGL": -0.3, "MSFT": 0.1}.get(t, 0)),
            Signal("value", lambda t: {"AAPL": -0.2, "GOOGL": 0.6, "MSFT": 0.3}.get(t, 0)),
        ]
        model = AlphaModel(signals, weights=[1.0, 1.0], normalize=False)
        alphas = model.generate_alphas(["AAPL", "GOOGL", "MSFT"])
        assert len(alphas) == 3
        assert all(isinstance(v, float) for v in alphas.values())

    def test_rank(self):
        signals = [Signal("s1", lambda t: {"A": 1.0, "B": 2.0, "C": 0.5}.get(t, 0))]
        model = AlphaModel(signals, normalize=False)
        ranked = model.rank(["A", "B", "C"])
        assert ranked[0] == "B"  # highest

    def test_top_n(self):
        signals = [Signal("s1", lambda t: ord(t))]
        model = AlphaModel(signals, normalize=False)
        top = model.top_n(["A", "B", "C", "D"], n=2)
        assert len(top) == 2

    def test_empty_universe(self):
        model = AlphaModel([Signal("s", lambda t: 0.0)])
        assert model.generate_alphas([]) == {}

    def test_normalize(self):
        signals = [Signal("s", lambda t: {"A": 10.0, "B": 20.0, "C": 30.0}.get(t, 0))]
        model = AlphaModel(signals, normalize=True)
        alphas = model.generate_alphas(["A", "B", "C"])
        vals = list(alphas.values())
        assert abs(np.mean(vals)) < 1e-10

    def test_weight_mismatch_raises(self):
        with pytest.raises(ValueError):
            AlphaModel([Signal("s", lambda t: 0)], weights=[1.0, 2.0])


# ============================================================
# Pipeline Tests
# ============================================================

class TestPipelineMetrics:
    def test_ic(self):
        p = np.array([1, 2, 3, 4, 5.0])
        a = np.array([1.1, 2.2, 2.9, 4.1, 5.0])
        ic = information_coefficient(p, a)
        assert ic > 0.95

    def test_rank_ic(self):
        p = np.array([1, 2, 3, 4, 5.0])
        a = np.array([2, 1, 4, 3, 5.0])  # some rank disagreement
        ric = rank_information_coefficient(p, a)
        assert 0 < ric < 1

    def test_turnover(self):
        w1 = np.array([0.5, 0.3, 0.2])
        w2 = np.array([0.3, 0.4, 0.3])
        t = portfolio_turnover(w1, w2)
        assert t > 0

    def test_pipeline_metrics_summary(self):
        m = PipelineMetrics(ic_mean=0.05, ic_std=0.02, rank_ic_mean=0.04, n_splits=5)
        s = m.summary()
        assert s["ic_mean"] == 0.05
        assert s["n_splits"] == 5


class TestWalkForwardSplit:
    def test_basic_split(self):
        splits = walk_forward_split(300, train_size=100, test_size=20)
        assert len(splits) > 0
        for train_idx, test_idx in splits:
            assert len(train_idx) == 100
            assert len(test_idx) == 20
            assert test_idx[0] == train_idx[-1] + 1

    def test_not_enough_data(self):
        splits = walk_forward_split(50, train_size=100, test_size=20)
        assert len(splits) == 0


class TestWalkForwardPipeline:
    def test_run_basic(self, price_data):
        close, high, low, volume = price_data
        pipeline = WalkForwardPipeline(train_size=100, test_size=21, target_horizon=5)
        metrics = pipeline.run(close, high, low, volume)
        assert metrics.n_splits > 0
        assert len(metrics.ic_per_split) == metrics.n_splits

    def test_run_close_only(self, price_data):
        close = price_data[0]
        pipeline = WalkForwardPipeline(train_size=100, test_size=21, target_horizon=5)
        metrics = pipeline.run(close)
        assert metrics.n_splits > 0

    def test_insufficient_data(self):
        close = np.linspace(100, 110, 30)
        pipeline = WalkForwardPipeline(train_size=252, test_size=21)
        metrics = pipeline.run(close)
        assert metrics.n_splits == 0


# ============================================================
# Optional sklearn/xgboost model tests
# ============================================================

class TestOptionalModels:
    def test_random_forest_availability(self):
        rf = RandomForestPredictor()
        # Just check it doesn't crash
        if rf.available:
            X = np.random.randn(50, 3)
            y = np.random.randn(50)
            rf.fit(X, y)
            preds = rf.predict(X)
            assert len(preds) == 50
        else:
            preds = rf.predict(np.random.randn(10, 3))
            assert np.all(np.isnan(preds))

    def test_xgboost_availability(self):
        xgb = XGBoostPredictor()
        if xgb.available:
            X = np.random.randn(50, 3)
            y = np.random.randn(50)
            xgb.fit(X, y)
            preds = xgb.predict(X)
            assert len(preds) == 50
        else:
            preds = xgb.predict(np.random.randn(10, 3))
            assert np.all(np.isnan(preds))
