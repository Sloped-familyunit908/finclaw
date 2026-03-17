"""Tests for the Golden Cross example strategy plugin."""

import pandas as pd
import numpy as np
import pytest

from finclaw_strategy_example.strategy import GoldenCrossStrategy


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data with a trend change."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2020-01-01", periods=n)
    # Create a price series with uptrend then downtrend
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    prices[150:] -= np.arange(150) * 0.1  # Add downtrend
    df = pd.DataFrame({
        "Open": prices + np.random.randn(n) * 0.1,
        "High": prices + abs(np.random.randn(n)) * 0.5,
        "Low": prices - abs(np.random.randn(n)) * 0.5,
        "Close": prices,
        "Volume": np.random.randint(1000, 10000, n),
    }, index=dates)
    return df


class TestGoldenCross:
    def test_metadata(self):
        s = GoldenCrossStrategy()
        assert s.name == "golden_cross"
        assert s.version == "1.0.0"
        assert "us_stock" in s.markets
        assert s.risk_level == "low"

    def test_generate_signals_shape(self, sample_data):
        s = GoldenCrossStrategy()
        signals = s.generate_signals(sample_data)
        assert len(signals) == len(sample_data)
        assert set(signals.unique()).issubset({-1, 0, 1})

    def test_parameters(self):
        s = GoldenCrossStrategy(fast_period=10, slow_period=30)
        params = s.get_parameters()
        assert params["fast_period"] == 10
        assert params["slow_period"] == 30

    def test_backtest_config(self):
        s = GoldenCrossStrategy()
        config = s.backtest_config()
        assert "initial_capital" in config
        assert "commission" in config

    def test_insufficient_data(self):
        s = GoldenCrossStrategy()
        small = pd.DataFrame({"Close": [100, 101]}, index=pd.date_range("2020-01-01", periods=2))
        signals = s.generate_signals(small)
        assert (signals == 0).all()

    def test_set_parameters(self):
        s = GoldenCrossStrategy()
        s.set_parameters({"fast_period": 30})
        assert s.fast_period == 30
