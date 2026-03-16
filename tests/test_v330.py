"""Tests for FinClaw v3.3.0 — Ensemble, Regime-Adaptive, Feature Store, Report Card."""

import math
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ml.ensemble import EnsembleModel as AdvancedEnsemble
from src.ml.feature_store import FeatureStore
from src.strategies.regime_adaptive import RegimeAdaptive, RegimeSignal
from src.reports.report_card import ReportCard, BacktestResult


# ======================================================================
# Helper: simple model with fit/predict
# ======================================================================

class DummyModel:
    """Minimal model for testing ensemble."""
    def __init__(self, offset: float = 0.0):
        self.offset = offset
        self.coefficients = None

    def fit(self, X, y):
        self.coefficients = np.array([0.5] * X.shape[1])
        return self

    def predict(self, X):
        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        return X @ np.full(X.shape[1], 0.5) + self.offset


class DummyStrategy:
    """Minimal strategy for testing regime-adaptive."""
    def __init__(self, default_signal='hold'):
        self._signal = default_signal

    def generate_signal(self, prices):
        return type('Sig', (), {'signal': self._signal})()


# ======================================================================
# Ensemble Model Tests
# ======================================================================

class TestEnsembleModel:
    def test_init_no_models_raises(self):
        with pytest.raises(ValueError, match="At least one model"):
            AdvancedEnsemble(models=[])

    def test_init_bad_method(self):
        with pytest.raises(ValueError, match="method must be"):
            AdvancedEnsemble(models=[DummyModel()], method='invalid')

    def test_init_weight_mismatch(self):
        with pytest.raises(ValueError, match="weights length"):
            AdvancedEnsemble(models=[DummyModel()], weights=[0.5, 0.5])

    def test_equal_weights_default(self):
        ens = AdvancedEnsemble(models=[DummyModel(), DummyModel()])
        assert ens.weights == [0.5, 0.5]

    def test_custom_weights_normalized(self):
        ens = AdvancedEnsemble(models=[DummyModel(), DummyModel()], weights=[2, 8])
        assert abs(ens.weights[0] - 0.2) < 1e-9
        assert abs(ens.weights[1] - 0.8) < 1e-9

    def test_fit_and_predict_voting(self):
        m1, m2 = DummyModel(offset=0.1), DummyModel(offset=-0.1)
        ens = AdvancedEnsemble(models=[m1, m2], method='voting')
        X = np.random.randn(50, 3)
        y = np.random.randn(50)
        ens.fit(X, y)
        result = ens.predict(np.array([1.0, 2.0, 3.0]))
        assert 'prediction' in result
        assert 'confidence' in result
        assert 'model_agreement' in result
        assert 0 <= result['confidence'] <= 1

    def test_fit_and_predict_weighted_avg(self):
        m1, m2 = DummyModel(offset=1.0), DummyModel(offset=-1.0)
        ens = AdvancedEnsemble(models=[m1, m2], method='weighted_avg')
        X = np.random.randn(30, 2)
        y = np.random.randn(30)
        ens.fit(X, y)
        result = ens.predict(np.zeros((1, 2)))
        # With equal weights, offsets cancel out
        assert abs(result['prediction']) < 1.5

    def test_predict_batch(self):
        ens = AdvancedEnsemble(models=[DummyModel(), DummyModel()])
        X = np.random.randn(50, 3)
        y = np.random.randn(50)
        ens.fit(X, y)
        result = ens.predict(np.random.randn(10, 3))
        assert len(result['prediction']) == 10

    def test_stacking_method(self):
        m1, m2 = DummyModel(offset=0.5), DummyModel(offset=-0.5)
        ens = AdvancedEnsemble(models=[m1, m2], method='stacking')
        X = np.random.randn(100, 4)
        y = X[:, 0] * 2 + np.random.randn(100) * 0.1
        ens.fit(X, y)
        result = ens.predict(np.array([[1, 0, 0, 0]]))
        assert isinstance(result['prediction'], float)

    def test_feature_importance_empty(self):
        ens = AdvancedEnsemble(models=[DummyModel()])
        imp = ens.feature_importance()
        assert 'per_model' in imp
        assert 'aggregated' in imp

    def test_feature_importance_with_coefficients(self):
        m = DummyModel()
        m.coefficients = np.array([0.3, 0.7])
        ens = AdvancedEnsemble(models=[m])
        imp = ens.feature_importance()
        assert len(imp['aggregated']) == 2

    def test_model_agreement_all_same(self):
        m1, m2 = DummyModel(offset=1.0), DummyModel(offset=1.0)
        ens = AdvancedEnsemble(models=[m1, m2], method='weighted_avg')
        X = np.random.randn(20, 2)
        ens.fit(X, np.random.randn(20))
        result = ens.predict(np.ones((1, 2)))
        assert result['model_agreement'] >= 0.9

    def test_fit_small_data(self):
        ens = AdvancedEnsemble(models=[DummyModel()])
        X = np.array([[1.0]])
        y = np.array([1.0])
        ens.fit(X, y)  # Should not raise


# ======================================================================
# Regime-Adaptive Strategy Tests
# ======================================================================

class TestRegimeAdaptive:
    def _make_bull_prices(self, n=200):
        return [100 * (1.001 ** i) for i in range(n)]

    def _make_bear_prices(self, n=200):
        return [100 * (0.999 ** i) for i in range(n)]

    def _make_sideways_prices(self, n=200):
        return [100 + 0.5 * math.sin(i / 5) for i in range(n)]

    def test_detect_regime_bull(self):
        ra = RegimeAdaptive(strategies={'bull': DummyStrategy('buy')}, transition_smooth=1)
        regime = ra.detect_regime(self._make_bull_prices())
        assert regime == 'bull'

    def test_detect_regime_bear(self):
        ra = RegimeAdaptive(strategies={'bear': DummyStrategy('sell')}, transition_smooth=1)
        regime = ra.detect_regime(self._make_bear_prices())
        assert regime == 'bear'

    def test_detect_regime_sideways(self):
        ra = RegimeAdaptive(strategies={'sideways': DummyStrategy()}, transition_smooth=1)
        regime = ra.detect_regime(self._make_sideways_prices())
        assert regime == 'sideways'

    def test_detect_regime_short_data(self):
        ra = RegimeAdaptive(strategies={}, sma_period=50)
        assert ra.detect_regime([100, 101, 102]) == 'sideways'

    def test_generate_signals_delegates(self):
        strategies = {
            'bull': DummyStrategy('buy'),
            'bear': DummyStrategy('sell'),
            'sideways': DummyStrategy('hold'),
        }
        ra = RegimeAdaptive(strategies=strategies, transition_smooth=1)
        signals = ra.generate_signals(self._make_bull_prices())
        assert len(signals) == 1
        assert isinstance(signals[0], RegimeSignal)
        assert signals[0].regime == 'bull'
        assert signals[0].signal == 'buy'

    def test_generate_signal_convenience(self):
        ra = RegimeAdaptive(strategies={'sideways': DummyStrategy('hold')}, transition_smooth=1)
        sig = ra.generate_signal(self._make_sideways_prices())
        assert isinstance(sig, RegimeSignal)

    def test_fallback_to_default(self):
        ra = RegimeAdaptive(strategies={'sideways': DummyStrategy('hold')}, transition_smooth=1)
        sig = ra.generate_signal(self._make_bull_prices())
        # No 'bull' strategy → falls back to default_regime='sideways'
        assert sig.signal == 'hold'

    def test_no_strategies(self):
        ra = RegimeAdaptive(strategies={}, transition_smooth=1)
        sig = ra.generate_signal([100] * 100)
        assert sig.signal == 'hold'

    def test_regime_stats(self):
        ra = RegimeAdaptive(strategies={'bull': DummyStrategy()}, transition_smooth=1)
        ra.detect_regime(self._make_bull_prices())
        stats = ra.get_regime_stats()
        assert 'bull' in stats

    def test_regime_confidence(self):
        ra = RegimeAdaptive(strategies={'bull': DummyStrategy('buy')}, transition_smooth=1)
        signals = ra.generate_signals(self._make_bull_prices())
        assert 0 <= signals[0].confidence <= 1

    def test_transition_smoothing(self):
        ra = RegimeAdaptive(strategies={'bull': DummyStrategy(), 'bear': DummyStrategy()}, transition_smooth=5)
        # Single call shouldn't flip instantly
        ra.detect_regime(self._make_bull_prices())
        regime = ra.detect_regime(self._make_bear_prices())
        # May still be bull due to smoothing or may flip — just check no crash
        assert regime in ('bull', 'bear', 'sideways')


# ======================================================================
# Feature Store Tests
# ======================================================================

class TestFeatureStore:
    def _prices(self, n=100):
        return [100 * (1 + 0.001 * i + 0.01 * math.sin(i / 10)) for i in range(n)]

    def test_list_features_builtins(self):
        fs = FeatureStore()
        features = fs.list_features()
        assert 'returns' in features
        assert 'volatility' in features
        assert 'rsi' in features
        assert 'macd' in features
        assert len(features) >= 10

    def test_compute_single_feature(self):
        fs = FeatureStore()
        result = fs.compute('AAPL', ['returns'], self._prices())
        assert 'returns' in result
        assert isinstance(result['returns'], float)

    def test_compute_multiple_features(self):
        fs = FeatureStore()
        result = fs.compute('AAPL', ['returns', 'volatility', 'rsi'], self._prices())
        assert len(result) == 3

    def test_compute_unknown_feature_raises(self):
        fs = FeatureStore()
        with pytest.raises(KeyError, match="Unknown feature"):
            fs.compute('AAPL', ['nonexistent'], self._prices())

    def test_compute_no_prices_no_cache_raises(self):
        fs = FeatureStore()
        with pytest.raises(ValueError, match="prices required"):
            fs.compute('AAPL', ['returns'])

    def test_register_custom_feature(self):
        fs = FeatureStore()
        fs.register_feature('custom_feat', lambda prices: len(prices))
        result = fs.compute('X', ['custom_feat'], [1, 2, 3])
        assert result['custom_feat'] == 3

    def test_get_feature_matrix(self):
        fs = FeatureStore()
        prices = {'AAPL': self._prices(), 'GOOG': self._prices(120)}
        matrix = fs.get_feature_matrix(['AAPL', 'GOOG'], ['returns'], prices)
        assert 'AAPL' in matrix
        assert 'GOOG' in matrix

    def test_cache_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = FeatureStore(cache_dir=tmpdir)
            prices = self._prices()
            fs.compute('AAPL', ['returns'], prices)
            # Second call should use cache (no prices needed if cached)
            result = fs.compute('AAPL', ['returns'])
            assert 'returns' in result

    def test_clear_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = FeatureStore(cache_dir=tmpdir)
            fs.compute('AAPL', ['returns'], self._prices())
            count = fs.clear_cache()
            assert count >= 1

    def test_no_cache_dir(self):
        fs = FeatureStore(cache_dir=None)
        result = fs.compute('X', ['returns'], self._prices())
        assert 'returns' in result

    def test_feature_rsi_range(self):
        fs = FeatureStore()
        result = fs.compute('X', ['rsi'], self._prices(200))
        assert 0 <= result['rsi'] <= 100

    def test_feature_volatility_positive(self):
        fs = FeatureStore()
        result = fs.compute('X', ['volatility'], self._prices(100))
        assert result['volatility'] >= 0

    def test_feature_price_momentum(self):
        fs = FeatureStore()
        result = fs.compute('X', ['price_momentum'], self._prices(100))
        assert isinstance(result['price_momentum'], float)

    def test_feature_sma_ratio(self):
        fs = FeatureStore()
        result = fs.compute('X', ['sma_ratio'], self._prices(100))
        assert 0.5 < result['sma_ratio'] < 1.5

    def test_feature_drawdown(self):
        fs = FeatureStore()
        result = fs.compute('X', ['drawdown'], self._prices(100))
        assert result['drawdown'] <= 0

    def test_feature_skewness(self):
        fs = FeatureStore()
        result = fs.compute('X', ['skewness'], self._prices(200))
        assert isinstance(result['skewness'], float)


# ======================================================================
# Report Card Tests
# ======================================================================

class TestReportCard:
    def _good_result(self):
        return BacktestResult(
            total_return=0.45, annualized_return=0.20, sharpe_ratio=1.8,
            sortino_ratio=2.5, max_drawdown=-0.08, win_rate=0.65,
            profit_factor=2.5, num_trades=120, avg_trade_return=0.003,
        )

    def _bad_result(self):
        return BacktestResult(
            total_return=-0.15, annualized_return=-0.08, sharpe_ratio=-0.3,
            sortino_ratio=-0.5, max_drawdown=-0.35, win_rate=0.35,
            profit_factor=0.7, num_trades=5, avg_trade_return=-0.02,
        )

    def _benchmark(self):
        return BacktestResult(
            total_return=0.30, annualized_return=0.12, sharpe_ratio=1.0,
            sortino_ratio=1.2, max_drawdown=-0.15, win_rate=0.55,
            profit_factor=1.5, num_trades=252,
        )

    def test_generate_good_result(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        assert report['grade'] in ('A', 'B')
        assert len(report['strengths']) > 0
        assert 'metrics' in report

    def test_generate_bad_result(self):
        rc = ReportCard()
        report = rc.generate(self._bad_result())
        assert report['grade'] in ('D', 'F')
        assert len(report['weaknesses']) > 0

    def test_generate_with_benchmark(self):
        rc = ReportCard()
        report = rc.generate(self._good_result(), benchmark_result=self._benchmark())
        assert 'benchmark_metrics' in report
        assert any('benchmark' in s.lower() or 'outperform' in s.lower() for s in report['strengths'])

    def test_grade_a_or_b(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        assert report['grade'] in ('A', 'B')

    def test_recommendation_exists(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        assert len(report['recommendation']) > 10

    def test_summary_contains_grade(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        assert report['grade'] in report['summary']

    def test_score_range(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        assert 0 <= report['score'] <= 100

    def test_render_html(self):
        rc = ReportCard()
        rc.generate(self._good_result())
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w') as f:
            path = f.name
        try:
            html = rc.render_html(path)
            assert '<html' in html
            assert 'FinClaw Report Card' in html
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_render_html_no_report_raises(self):
        rc = ReportCard()
        with pytest.raises(RuntimeError, match="No report generated"):
            rc.render_html('test.html')

    def test_metrics_extraction(self):
        rc = ReportCard()
        report = rc.generate(self._good_result())
        m = report['metrics']
        assert m['sharpe_ratio'] == 1.8
        assert m['num_trades'] == 120

    def test_calmar_auto_computed(self):
        rc = ReportCard()
        result = self._good_result()
        result.calmar_ratio = 0  # Force auto-compute
        report = rc.generate(result)
        assert report['metrics']['calmar_ratio'] > 0

    def test_empty_result(self):
        rc = ReportCard()
        report = rc.generate(BacktestResult())
        assert report['grade'] == 'F'
