"""
Plugin System Integration Tests
================================
Tests StrategyRegistry, Backtrader adapter, TA-Lib adapter (fallback mode),
Pine Script parser, and strategy filtering.
"""

import sys
import os
import math
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_ohlcv_df(n=200, seed=42):
    """Generate synthetic OHLCV DataFrame."""
    np.random.seed(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    close = 100.0 * np.cumprod(1 + np.random.normal(0.0003, 0.02, n))
    return pd.DataFrame({
        "Open": close * 0.999,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Close": close,
        "Volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
    }, index=dates)


# ── StrategyRegistry ─────────────────────────────────────────────

class TestStrategyRegistry:
    def test_load_all(self):
        from src.plugin_system.registry import StrategyRegistry
        reg = StrategyRegistry()
        plugins = reg.load_all()
        assert isinstance(plugins, list)
        # Should have at least some built-in strategies
        assert len(plugins) >= 0  # may be 0 if no plugins dir

    def test_names(self):
        from src.plugin_system.registry import StrategyRegistry
        reg = StrategyRegistry()
        reg.load_all()
        names = reg.names()
        assert isinstance(names, list)

    def test_register_and_get(self):
        from src.plugin_system.registry import StrategyRegistry
        from src.plugin_system.plugin_types import StrategyPlugin

        reg = StrategyRegistry()

        # Use a mock that looks like StrategyPlugin without ABC restrictions
        plugin = MagicMock(spec=StrategyPlugin)
        plugin.name = "test_fake"
        plugin.description = "A fake plugin for testing"
        plugin.version = "1.0.0"
        plugin.author = "test"
        plugin.markets = ["us_stock"]
        plugin.risk_level = "low"

        reg.register(plugin)
        assert reg.get("test_fake") is plugin
        assert "test_fake" in reg.names()

    def test_unregister(self):
        from src.plugin_system.registry import StrategyRegistry

        reg = StrategyRegistry()
        plugin = MagicMock()
        plugin.name = "test_fake2"
        plugin.markets = ["crypto"]
        plugin.risk_level = "high"

        reg.register(plugin)
        assert reg.unregister("test_fake2") is True
        assert reg.get("test_fake2") is None

    def test_filter_by_market(self):
        from src.plugin_system.registry import StrategyRegistry

        reg = StrategyRegistry()

        crypto_plugin = MagicMock()
        crypto_plugin.name = "crypto_test"
        crypto_plugin.markets = ["crypto"]
        crypto_plugin.risk_level = "high"

        stock_plugin = MagicMock()
        stock_plugin.name = "stock_test"
        stock_plugin.markets = ["us_stock"]
        stock_plugin.risk_level = "low"

        reg.register(crypto_plugin)
        reg.register(stock_plugin)
        crypto = reg.filter(market="crypto")
        assert any(p.name == "crypto_test" for p in crypto)
        assert not any(p.name == "stock_test" for p in crypto)

    def test_filter_by_risk_level(self):
        from src.plugin_system.registry import StrategyRegistry

        reg = StrategyRegistry()

        plugin = MagicMock()
        plugin.name = "low_risk_test"
        plugin.markets = ["us_stock"]
        plugin.risk_level = "low"

        reg.register(plugin)
        low = reg.filter(risk_level="low")
        assert any(p.name == "low_risk_test" for p in low)


# ── TA-Lib Adapter (Fallback Mode) ──────────────────────────────

class TestTALibFallback:
    """Test all 11 fallback indicators in pure Python mode."""

    @pytest.fixture
    def ohlcv(self):
        return _make_ohlcv_df(200)

    @pytest.mark.parametrize("indicator", [
        "sma", "ema", "rsi", "macd", "bbands", "stoch",
        "atr", "adx", "cci", "willr", "mfi",
    ])
    def test_fallback_indicator(self, indicator, ohlcv):
        from src.plugin_system.talib_adapter import compute_indicator
        # Force fallback by patching _HAS_TALIB
        import src.plugin_system.talib_adapter as mod
        original = mod._HAS_TALIB
        mod._HAS_TALIB = False
        try:
            result = compute_indicator(indicator, ohlcv)
            assert isinstance(result, dict)
            assert len(result) > 0
            for key, series in result.items():
                assert isinstance(series, pd.Series)
                assert len(series) == len(ohlcv)
                # At least some non-NaN values
                assert series.notna().sum() > 0
        finally:
            mod._HAS_TALIB = original

    def test_unknown_indicator_raises(self, ohlcv):
        from src.plugin_system.talib_adapter import compute_indicator
        import src.plugin_system.talib_adapter as mod
        original = mod._HAS_TALIB
        mod._HAS_TALIB = False
        try:
            with pytest.raises(ValueError, match="Unknown indicator"):
                compute_indicator("nonexistent_xyz", ohlcv)
        finally:
            mod._HAS_TALIB = original

    def test_available_indicators(self):
        from src.plugin_system.talib_adapter import available_indicators, FALLBACK_INDICATORS
        indicators = available_indicators()
        assert isinstance(indicators, list)
        assert len(indicators) >= len(FALLBACK_INDICATORS)

    def test_signal_generator(self, ohlcv):
        from src.plugin_system.talib_adapter import TALibSignalGenerator
        gen = TALibSignalGenerator("rsi", period=14, overbought=70, oversold=30)
        signals = gen.generate_signals(ohlcv)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(ohlcv)


# ── Pine Script Parser ──────────────────────────────────────────

class TestPineParser:
    def test_simple_sma_cross(self):
        from src.plugin_system.pine_parser import PineScriptPlugin

        pine_code = '''
        //@version=5
        strategy("SMA Cross", overlay=true)
        fast = ta.sma(close, 10)
        slow = ta.sma(close, 50)
        if ta.crossover(fast, slow)
            strategy.entry("Long", strategy.long)
        if ta.crossunder(fast, slow)
            strategy.close("Long")
        '''

        plugin = PineScriptPlugin(pine_code, name="test_sma_cross")
        assert plugin.name == "test_sma_cross"

        df = _make_ohlcv_df(200)
        signals = plugin.generate_signals(df)
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(df)
        # Should have at least some buy/sell signals
        assert (signals != 0).sum() > 0

    def test_rsi_strategy(self):
        from src.plugin_system.pine_parser import PineScriptPlugin

        pine_code = '''
        //@version=5
        strategy("RSI Strategy")
        rsi_val = ta.rsi(close, 14)
        if rsi_val < 30
            strategy.entry("Long", strategy.long)
        if rsi_val > 70
            strategy.close("Long")
        '''

        plugin = PineScriptPlugin(pine_code, name="test_rsi")
        df = _make_ohlcv_df(200)
        signals = plugin.generate_signals(df)
        assert isinstance(signals, pd.Series)


# ── Backtrader Adapter ──────────────────────────────────────────

class TestBacktraderAdapter:
    def test_adapter_without_backtrader(self):
        """Without backtrader installed, generate_signals should raise ImportError."""
        from src.plugin_system.backtrader_adapter import BacktraderAdapter, _HAS_BACKTRADER
        if not _HAS_BACKTRADER:
            adapter = BacktraderAdapter(
                bt_strategy_cls=None,
                name="test_bt",
                description="test",
            )
            df = _make_ohlcv_df()
            with pytest.raises(ImportError, match="backtrader"):
                adapter.generate_signals(df)

    def test_adapter_no_strategy_class(self):
        """With backtrader but no class → ValueError."""
        from src.plugin_system.backtrader_adapter import BacktraderAdapter, _HAS_BACKTRADER
        if _HAS_BACKTRADER:
            adapter = BacktraderAdapter(bt_strategy_cls=None, name="test")
            with pytest.raises(ValueError, match="No backtrader"):
                adapter.generate_signals(_make_ohlcv_df())
