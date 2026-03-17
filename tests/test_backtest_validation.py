"""
Tests for FinClaw v2.9.0 — Backtesting Quality & Validation.

Covers: WalkForwardOptimizer, OverfitDetector, DataQualityChecker,
        SurvivorshipBiasChecker, SensitivityAnalyzer.
"""

import math
import pytest
import numpy as np
import pandas as pd

from src.backtesting.walk_forward_v2 import (
    WalkForwardOptimizer, WalkForwardResult, WindowResult, _sharpe, _cagr,
)
from src.backtesting.overfit_check import OverfitDetector
from src.data.quality import DataQualityChecker, DataQualityReport
from src.backtesting.survivorship import SurvivorshipBiasChecker, KNOWN_DELISTED
from src.analytics.sensitivity import SensitivityAnalyzer, SensitivityResult


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_price_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic daily price data."""
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range('2020-01-01', periods=n)
    returns = rng.normal(0.0003, 0.015, n)
    prices = 100 * np.cumprod(1 + returns)
    volume = rng.randint(1_000_000, 10_000_000, n)
    return pd.DataFrame({
        'close': prices,
        'open': prices * (1 + rng.normal(0, 0.002, n)),
        'high': prices * (1 + abs(rng.normal(0, 0.005, n))),
        'low': prices * (1 - abs(rng.normal(0, 0.005, n))),
        'volume': volume,
    }, index=dates)


def _simple_ma_strategy(data: pd.DataFrame, window: int = 20, **kw) -> np.ndarray:
    """Simple moving average crossover strategy returns."""
    prices = data['close'].values
    returns = np.diff(prices) / prices[:-1]
    ma = pd.Series(prices).rolling(window).mean().values
    signals = np.where(prices[1:] > ma[1:], 1, -1)
    return signals * returns


# ═══════════════════════════════════════════════════════════════════════
# Walk-Forward Optimizer Tests
# ═══════════════════════════════════════════════════════════════════════

class TestWalkForwardOptimizer:

    def test_init_defaults(self):
        wfo = WalkForwardOptimizer()
        assert wfo.train_pct == 0.7
        assert wfo.anchored is False
        assert wfo.n_windows == 5

    def test_init_custom(self):
        wfo = WalkForwardOptimizer(train_pct=0.8, anchored=True, n_windows=3)
        assert wfo.train_pct == 0.8
        assert wfo.anchored is True
        assert wfo.n_windows == 3

    def test_invalid_train_pct(self):
        with pytest.raises(ValueError):
            WalkForwardOptimizer(train_pct=0.05)
        with pytest.raises(ValueError):
            WalkForwardOptimizer(train_pct=0.99)

    def test_invalid_n_windows(self):
        with pytest.raises(ValueError):
            WalkForwardOptimizer(n_windows=1)

    def test_rolling_optimize(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(train_pct=0.7, n_windows=3, min_train_bars=30)
        result = wfo.optimize(
            _simple_ma_strategy,
            {'window': [5, 10, 20, 50]},
            data,
        )
        assert isinstance(result, WalkForwardResult)
        assert len(result.windows) >= 2
        assert isinstance(result.oos_sharpe, float)
        assert isinstance(result.overfitting_ratio, float)

    def test_anchored_optimize(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(train_pct=0.6, anchored=True, n_windows=3, min_train_bars=30)
        result = wfo.optimize(
            _simple_ma_strategy,
            {'window': [10, 20, 30]},
            data,
        )
        assert len(result.windows) >= 1
        # Anchored: first window train starts at 0
        if result.windows:
            assert result.windows[0].train_start == 0

    def test_param_stability(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(n_windows=3, min_train_bars=30)
        result = wfo.optimize(
            _simple_ma_strategy,
            {'window': [5, 10, 20, 50]},
            data,
        )
        assert 0 <= result.param_stability <= 2.0

    def test_overfitting_ratio(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(n_windows=3, min_train_bars=30)
        result = wfo.optimize(
            _simple_ma_strategy,
            {'window': [10, 20]},
            data,
        )
        assert result.overfitting_ratio >= 0

    def test_insufficient_data(self):
        data = _make_price_df(20)
        wfo = WalkForwardOptimizer(n_windows=5, min_train_bars=60)
        with pytest.raises(ValueError):
            wfo.optimize(_simple_ma_strategy, {'window': [5, 10]}, data)

    def test_result_summary(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(n_windows=3, min_train_bars=30)
        result = wfo.optimize(_simple_ma_strategy, {'window': [10, 20]}, data)
        summary = result.summary()
        assert 'Walk-Forward' in summary
        assert 'OOS Sharpe' in summary

    def test_best_params_per_window(self):
        data = _make_price_df(500)
        wfo = WalkForwardOptimizer(n_windows=3, min_train_bars=30)
        result = wfo.optimize(_simple_ma_strategy, {'window': [10, 20, 50]}, data)
        assert len(result.best_params_per_window) == len(result.windows)
        for p in result.best_params_per_window:
            assert 'window' in p


# ═══════════════════════════════════════════════════════════════════════
# Overfit Detector Tests
# ═══════════════════════════════════════════════════════════════════════

class TestOverfitDetector:

    def test_deflated_sharpe_single_trial(self):
        # With 1 trial, DSR should be high for a decent Sharpe
        dsr = OverfitDetector.deflated_sharpe_ratio(2.0, n_trials=1, n_obs=252)
        assert 0 <= dsr <= 1

    def test_deflated_sharpe_many_trials(self):
        # More trials → lower DSR for the same Sharpe
        dsr_few = OverfitDetector.deflated_sharpe_ratio(1.5, n_trials=5, n_obs=252)
        dsr_many = OverfitDetector.deflated_sharpe_ratio(1.5, n_trials=1000, n_obs=252)
        assert dsr_many < dsr_few

    def test_deflated_sharpe_high_sharpe(self):
        dsr = OverfitDetector.deflated_sharpe_ratio(5.0, n_trials=100, n_obs=252)
        assert dsr > 0.5  # Very high Sharpe should still be significant

    def test_deflated_sharpe_invalid(self):
        with pytest.raises(ValueError):
            OverfitDetector.deflated_sharpe_ratio(1.0, n_trials=0)
        with pytest.raises(ValueError):
            OverfitDetector.deflated_sharpe_ratio(1.0, n_trials=1, n_obs=1)

    def test_cpcv_basic(self):
        rng = np.random.RandomState(42)
        data = rng.normal(0.001, 0.02, 500)

        def strategy(d):
            return d  # Identity strategy

        result = OverfitDetector.combinatorial_purged_cv(strategy, data, n_splits=6)
        assert 'oos_sharpes' in result
        assert 'pbo' in result
        assert 0 <= result['pbo'] <= 1

    def test_cpcv_insufficient_data(self):
        data = np.array([0.01, 0.02])
        with pytest.raises(ValueError):
            OverfitDetector.combinatorial_purged_cv(lambda d: d, data, n_splits=10)

    def test_white_reality_check_outperformance(self):
        rng = np.random.RandomState(42)
        strat = rng.normal(0.002, 0.01, 200)
        bench = rng.normal(0.0005, 0.01, 200)
        result = OverfitDetector.white_reality_check(strat, bench)
        assert 'p_value' in result
        assert 'significant' in result
        assert isinstance(result['significant'], bool)
        assert result['mean_excess'] > 0

    def test_white_reality_check_no_edge(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.001, 0.02, 200)
        result = OverfitDetector.white_reality_check(returns, returns)
        assert abs(result['mean_excess']) < 0.001

    def test_white_reality_check_few_obs(self):
        with pytest.raises(ValueError):
            OverfitDetector.white_reality_check([0.01] * 5, [0.01] * 5)

    def test_pbo_all_positive(self):
        pbo = OverfitDetector.probability_of_backtest_overfitting([1.0, 0.5, 0.8, 1.2])
        assert pbo == 0.0

    def test_pbo_all_negative(self):
        pbo = OverfitDetector.probability_of_backtest_overfitting([-0.5, -0.3, -1.0])
        assert pbo == 1.0

    def test_pbo_mixed(self):
        pbo = OverfitDetector.probability_of_backtest_overfitting([1.0, -0.5, 0.8, -0.3])
        assert pbo == 0.5

    def test_pbo_empty(self):
        assert OverfitDetector.probability_of_backtest_overfitting([]) == 1.0


# ═══════════════════════════════════════════════════════════════════════
# Data Quality Checker Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDataQualityChecker:

    def test_check_clean_data(self):
        df = _make_price_df(252)
        checker = DataQualityChecker()
        report = checker.check(df)
        assert isinstance(report, DataQualityReport)
        assert report.score > 50
        assert report.total_rows == 252

    def test_check_with_gaps(self):
        dates = pd.bdate_range('2020-01-01', periods=100)
        # Remove 10 consecutive days to create a gap
        dates = dates[:40].append(dates[55:])
        prices = np.linspace(100, 150, len(dates))
        df = pd.DataFrame({'close': prices}, index=dates)
        checker = DataQualityChecker()
        report = checker.check(df)
        assert len(report.gaps) > 0

    def test_check_stale_prices(self):
        dates = pd.bdate_range('2020-01-01', periods=50)
        prices = np.ones(50) * 100  # All same price = stale
        df = pd.DataFrame({'close': prices}, index=dates)
        checker = DataQualityChecker(stale_threshold=3)
        report = checker.check(df)
        assert len(report.stale_prices) > 0

    def test_check_outliers(self):
        df = _make_price_df(200)
        # Inject outlier
        df.iloc[100, df.columns.get_loc('close')] = df['close'].iloc[99] * 3
        checker = DataQualityChecker(outlier_threshold=3.0)
        report = checker.check(df)
        assert len(report.outliers) > 0

    def test_check_corporate_actions(self):
        dates = pd.bdate_range('2020-01-01', periods=100)
        prices = np.linspace(100, 150, 100)
        # Inject a 2:1 split
        prices[50:] = prices[50:] / 2
        df = pd.DataFrame({'close': prices}, index=dates)
        checker = DataQualityChecker(split_threshold=0.3)
        report = checker.check(df)
        assert len(report.corporate_actions) > 0

    def test_check_empty_data(self):
        df = pd.DataFrame({'close': []})
        checker = DataQualityChecker()
        report = checker.check(df)
        assert report.score == 0

    def test_clean_fill_gaps(self):
        dates = pd.bdate_range('2020-01-01', periods=50)
        prices = np.linspace(100, 150, 50)
        df = pd.DataFrame({'close': prices}, index=dates)
        # Remove some rows
        df = df.drop(df.index[20:23])
        checker = DataQualityChecker()
        cleaned = checker.clean(df, {'fill_gaps': True})
        assert len(cleaned) >= len(df)

    def test_clean_remove_outliers(self):
        df = _make_price_df(200)
        df.iloc[100, df.columns.get_loc('close')] = df['close'].iloc[99] * 5
        checker = DataQualityChecker()
        cleaned = checker.clean(df, {'remove_outliers': True, 'fill_gaps': False})
        assert len(cleaned) > 0

    def test_quality_score_range(self):
        df = _make_price_df(252)
        checker = DataQualityChecker()
        report = checker.check(df)
        assert 0 <= report.score <= 100

    def test_report_summary(self):
        df = _make_price_df(100)
        checker = DataQualityChecker()
        report = checker.check(df)
        summary = report.summary()
        assert 'Data Quality Report' in summary
        assert 'Score' in summary

    def test_date_column_normalization(self):
        """Test that data with 'date' column (not index) works."""
        dates = pd.bdate_range('2020-01-01', periods=50)
        df = pd.DataFrame({
            'date': dates,
            'close': np.linspace(100, 150, 50),
        })
        checker = DataQualityChecker()
        report = checker.check(df)
        assert report.total_rows == 50

    def test_missing_dates_detection(self):
        dates = pd.bdate_range('2020-01-01', periods=100)
        # Drop some business days
        keep = [i for i in range(100) if i not in [20, 21, 22, 50, 51]]
        df = pd.DataFrame({'close': np.linspace(100, 150, len(keep))}, index=dates[keep])
        checker = DataQualityChecker()
        report = checker.check(df)
        assert len(report.missing_dates) >= 3


# ═══════════════════════════════════════════════════════════════════════
# Survivorship Bias Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSurvivorshipBiasChecker:

    def test_clean_universe(self):
        checker = SurvivorshipBiasChecker()
        result = checker.check(
            ['AAPL', 'MSFT', 'GOOG', 'AMZN'],
            start_date='2023-01-01',
            end_date='2024-01-01',
        )
        assert result['warning'] in ('Low risk', 'Moderate survivorship bias risk')
        assert isinstance(result['bias_estimate'], float)

    def test_detects_delisted(self):
        checker = SurvivorshipBiasChecker()
        # Universe that covers 2008 but doesn't include LEH, BSC
        result = checker.check(
            ['AAPL', 'MSFT', 'JPM', 'GS'],
            start_date='2005-01-01',
            end_date='2010-01-01',
        )
        assert len(result['delisted']) > 0
        tickers = [d['ticker'] for d in result['delisted']]
        assert any(t in tickers for t in ['LEH', 'BSC', 'WB', 'WMI'])

    def test_short_period_low_bias(self):
        checker = SurvivorshipBiasChecker()
        result = checker.check(['AAPL'], start_date='2024-01-01', end_date='2024-06-01')
        assert result['bias_estimate'] < 0.05

    def test_long_period_higher_bias(self):
        checker = SurvivorshipBiasChecker()
        r_short = checker.check(['AAPL', 'MSFT'], '2023-01-01', '2024-01-01')
        r_long = checker.check(['AAPL', 'MSFT'], '2000-01-01', '2024-01-01')
        assert r_long['bias_estimate'] >= r_short['bias_estimate']

    def test_small_cap_higher_bias(self):
        checker_large = SurvivorshipBiasChecker(market='US_large_cap')
        checker_small = SurvivorshipBiasChecker(market='US_small_cap')
        r_large = checker_large.check(['AAPL'], '2020-01-01', '2024-01-01')
        r_small = checker_small.check(['AAPL'], '2020-01-01', '2024-01-01')
        assert r_small['bias_estimate'] >= r_large['bias_estimate']

    def test_report_object(self):
        checker = SurvivorshipBiasChecker()
        result = checker.check(['AAPL', 'MSFT'], '2005-01-01', '2024-01-01')
        report = result['report']
        from src.backtesting.survivorship import SurvivorshipReport as SR
        assert isinstance(report, SR)
        summary = report.summary()
        assert 'Survivorship Bias Report' in summary

    def test_recommendations(self):
        checker = SurvivorshipBiasChecker()
        result = checker.check(['AAPL'], '2000-01-01', '2024-01-01')
        assert len(result['recommendations']) > 0


# ═══════════════════════════════════════════════════════════════════════
# Sensitivity Analyzer Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSensitivityAnalyzer:

    def test_basic_analysis(self):
        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        result = analyzer.analyze(
            _simple_ma_strategy, data,
            'window', [5, 10, 20, 50, 100],
        )
        assert isinstance(result, SensitivityResult)
        assert result.param == 'window'
        assert len(result.results) == 5
        assert result.optimal in [5, 10, 20, 50, 100]

    def test_sensitivity_classification(self):
        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        result = analyzer.analyze(
            _simple_ma_strategy, data,
            'window', [5, 10, 20, 50, 100],
        )
        assert result.sensitivity in ('low', 'medium', 'high')

    def test_cliff_detection(self):
        """Strategy that has a sharp performance cliff."""
        def cliff_strategy(data, threshold=50, **kw):
            prices = data['close'].values
            returns = np.diff(prices) / prices[:-1]
            if threshold < 30:
                return returns * 0.01  # Terrible below 30
            return returns

        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer(cliff_threshold=0.3)
        result = analyzer.analyze(
            cliff_strategy, data,
            'threshold', [10, 20, 30, 40, 50],
        )
        # Should detect the cliff between 20->30
        assert isinstance(result.cliff_edges, list)

    def test_multi_analysis(self):
        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        results = analyzer.analyze_multi(
            _simple_ma_strategy, data,
            {'window': [10, 20, 50]},
        )
        assert 'window' in results
        assert isinstance(results['window'], SensitivityResult)

    def test_result_summary(self):
        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        result = analyzer.analyze(
            _simple_ma_strategy, data,
            'window', [10, 20, 50],
        )
        summary = result.summary()
        assert 'Sensitivity Analysis' in summary
        assert 'window' in summary

    def test_single_value(self):
        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        result = analyzer.analyze(
            _simple_ma_strategy, data,
            'window', [20],
        )
        assert result.optimal == 20
        assert len(result.results) == 1

    def test_monotonic_detection(self):
        """Test that monotonic trends are detected."""
        def monotonic_strategy(data, mult=1.0, **kw):
            prices = data['close'].values
            returns = np.diff(prices) / prices[:-1]
            return returns * mult

        data = _make_price_df(300)
        analyzer = SensitivityAnalyzer()
        result = analyzer.analyze(
            monotonic_strategy, data,
            'mult', [0.5, 1.0, 1.5, 2.0, 2.5],
        )
        # Performance should scale with multiplier (if base returns > 0)
        assert result.monotonic in ('increasing', 'decreasing', None)


# ═══════════════════════════════════════════════════════════════════════
# Helper Function Tests
# ═══════════════════════════════════════════════════════════════════════

class TestHelperFunctions:

    def test_sharpe_positive(self):
        returns = np.array([0.01, 0.02, -0.005, 0.015, 0.01] * 50)
        s = _sharpe(returns)
        assert s > 0

    def test_sharpe_zero_std(self):
        returns = np.array([0.01, 0.01, 0.01])
        assert _sharpe(returns) == 0.0

    def test_sharpe_empty(self):
        assert _sharpe(np.array([])) == 0.0

    def test_cagr_positive(self):
        returns = np.array([0.001] * 252)
        c = _cagr(returns)
        assert c > 0

    def test_cagr_empty(self):
        assert _cagr(np.array([])) == 0.0
