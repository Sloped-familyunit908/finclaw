"""
Tests for FinClaw Strategy Plugin System
Covers: plugin_types, plugin_loader, registry, builtin_adapters,
        talib_adapter, backtrader_adapter, pine_parser.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugin_system.plugin_types import StrategyPlugin
from src.plugin_system.plugin_loader import PluginLoader
from src.plugin_system.registry import StrategyRegistry
from src.plugin_system.builtin_adapters import (
    TrendFollowingPlugin, MeanReversionPlugin, MomentumPlugin,
    ValueMomentumPlugin, get_builtin_plugins,
)
from src.plugin_system.talib_adapter import (
    TALibSignalGenerator, talib_strategy, compute_indicator,
    available_indicators, _sma, _ema, _rsi, _macd, _bbands,
    _stoch, _atr, _adx, _cci, _willr, _mfi, FALLBACK_INDICATORS,
)
from src.plugin_system.pine_parser import PineScriptPlugin, PineParser, from_pine
from src.plugin_system.backtrader_adapter import BacktraderAdapter, _PandasDataFeed, _PandasLine, _SignalCollector


# ─── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Generate realistic OHLCV DataFrame."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2020-01-01", periods=n)
    base = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "Open": base + np.random.randn(n) * 0.2,
        "High": base + abs(np.random.randn(n)) * 0.5,
        "Low": base - abs(np.random.randn(n)) * 0.5,
        "Close": base,
        "Volume": np.random.randint(1000, 50000, n).astype(float),
    }, index=dates)
    return df


@pytest.fixture
def small_df():
    """Small DataFrame for edge cases."""
    return pd.DataFrame({
        "Close": [100, 101, 102],
    }, index=pd.date_range("2020-01-01", periods=3))


# ─── StrategyPlugin (Abstract) ─────────────────────────────────

class TestStrategyPluginInterface:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            StrategyPlugin()

    def test_concrete_subclass(self, sample_df):
        class DummyStrategy(StrategyPlugin):
            name = "dummy"
            version = "0.1.0"
            markets = ["us_stock"]
            def generate_signals(self, data):
                return pd.Series(0, index=data.index)
            def get_parameters(self):
                return {}

        s = DummyStrategy()
        assert s.name == "dummy"
        signals = s.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_validate_ok(self):
        class Good(StrategyPlugin):
            name = "good"
            risk_level = "low"
            markets = ["crypto"]
            def generate_signals(self, data): return pd.Series(0, index=data.index)
            def get_parameters(self): return {}
        assert Good().validate() == []

    def test_validate_issues(self):
        class Bad(StrategyPlugin):
            risk_level = "extreme"
            def generate_signals(self, data): return pd.Series(0, index=data.index)
            def get_parameters(self): return {}
        issues = Bad().validate()
        assert len(issues) >= 2  # name + risk_level + markets

    def test_get_info(self):
        class Info(StrategyPlugin):
            name = "info"
            version = "2.0"
            author = "me"
            risk_level = "high"
            markets = ["forex"]
            def generate_signals(self, data): return pd.Series()
            def get_parameters(self): return {}
        info = Info().get_info()
        assert info["name"] == "info"
        assert info["author"] == "me"

    def test_set_parameters(self):
        class Param(StrategyPlugin):
            name = "param"
            markets = ["us_stock"]
            def __init__(self):
                self.window = 20
            def generate_signals(self, data): return pd.Series()
            def get_parameters(self): return {"window": self.window}
        p = Param()
        p.set_parameters({"window": 50})
        assert p.window == 50

    def test_backtest_config_default(self):
        class BC(StrategyPlugin):
            name = "bc"
            markets = ["us_stock"]
            def generate_signals(self, data): return pd.Series()
            def get_parameters(self): return {}
        config = BC().backtest_config()
        assert "initial_capital" in config

    def test_repr(self):
        class R(StrategyPlugin):
            name = "repr_test"
            version = "3.0"
            markets = ["us_stock"]
            def generate_signals(self, data): return pd.Series()
            def get_parameters(self): return {}
        assert "repr_test" in repr(R())


# ─── Built-in Adapters ─────────────────────────────────────────

class TestBuiltinAdapters:
    def test_get_builtin_plugins(self):
        plugins = get_builtin_plugins()
        assert len(plugins) == 4
        names = {p.name for p in plugins}
        assert "trend_following" in names
        assert "mean_reversion" in names

    def test_trend_following_signals(self, sample_df):
        p = TrendFollowingPlugin()
        signals = p.generate_signals(sample_df)
        assert len(signals) == len(sample_df)
        assert signals.dtype in [np.int64, np.float64, int]

    def test_trend_following_params(self):
        p = TrendFollowingPlugin(fast_period=10, slow_period=30)
        params = p.get_parameters()
        assert params["fast_period"] == 10

    def test_mean_reversion_signals(self, sample_df):
        p = MeanReversionPlugin()
        signals = p.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_momentum_signals(self, sample_df):
        p = MomentumPlugin()
        signals = p.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_value_momentum_signals(self, sample_df):
        p = ValueMomentumPlugin()
        signals = p.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_all_have_metadata(self):
        for p in get_builtin_plugins():
            assert p.name != "unnamed"
            assert p.version
            assert p.markets
            assert p.risk_level in ("low", "medium", "high")


# ─── Plugin Loader ──────────────────────────────────────────────

class TestPluginLoader:
    def test_discover_builtin(self):
        loader = PluginLoader()
        plugins = loader.discover_builtin()
        assert len(plugins) >= 4

    def test_discover_all(self):
        loader = PluginLoader()
        plugins = loader.discover_all()
        assert len(plugins) >= 4

    def test_get_by_name(self):
        loader = PluginLoader()
        loader.discover_all()
        p = loader.get("trend_following")
        assert p is not None
        assert p.name == "trend_following"

    def test_get_missing(self):
        loader = PluginLoader()
        assert loader.get("nonexistent") is None

    def test_unload(self):
        loader = PluginLoader()
        loader.discover_all()
        assert loader.unload("trend_following")
        assert loader.get("trend_following") is None

    def test_load_file(self, tmp_path):
        code = '''
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin

class FileStrategy(StrategyPlugin):
    name = "file_loaded"
    version = "0.1.0"
    markets = ["us_stock"]
    risk_level = "low"

    def generate_signals(self, data):
        return pd.Series(0, index=data.index)

    def get_parameters(self):
        return {}
'''
        f = tmp_path / "my_strat.py"
        f.write_text(code)
        loader = PluginLoader()
        plugins = loader.load_file(str(f))
        assert len(plugins) == 1
        assert plugins[0].name == "file_loaded"

    def test_load_file_not_found(self):
        loader = PluginLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file("/nonexistent.py")

    def test_load_directory(self, tmp_path):
        code = '''
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin

class DirStrategy(StrategyPlugin):
    name = "dir_loaded"
    version = "0.1.0"
    markets = ["crypto"]
    risk_level = "medium"
    def generate_signals(self, data):
        return pd.Series(0, index=data.index)
    def get_parameters(self):
        return {}
'''
        (tmp_path / "strat1.py").write_text(code)
        (tmp_path / "_hidden.py").write_text(code)  # should be ignored
        loader = PluginLoader()
        plugins = loader.load_directory(str(tmp_path))
        assert len(plugins) == 1

    def test_load_directory_empty(self, tmp_path):
        loader = PluginLoader()
        assert loader.load_directory(str(tmp_path)) == []

    def test_load_directory_nonexistent(self):
        loader = PluginLoader()
        assert loader.load_directory("/nonexistent") == []


# ─── Strategy Registry ─────────────────────────────────────────

class TestStrategyRegistry:
    def test_load_all(self):
        reg = StrategyRegistry()
        plugins = reg.load_all()
        assert len(plugins) >= 4

    def test_list(self):
        reg = StrategyRegistry()
        reg.load_all()
        assert len(reg.list()) >= 4

    def test_names(self):
        reg = StrategyRegistry()
        reg.load_all()
        assert "trend_following" in reg.names()

    def test_get(self):
        reg = StrategyRegistry()
        reg.load_all()
        assert reg.get("mean_reversion") is not None

    def test_filter_by_market(self):
        reg = StrategyRegistry()
        reg.load_all()
        crypto = reg.filter(market="crypto")
        for s in crypto:
            assert "crypto" in s.markets

    def test_filter_by_risk(self):
        reg = StrategyRegistry()
        reg.load_all()
        low = reg.filter(risk_level="low")
        for s in low:
            assert s.risk_level == "low"

    def test_filter_combined(self):
        reg = StrategyRegistry()
        reg.load_all()
        result = reg.filter(market="us_stock", risk_level="medium")
        for s in result:
            assert "us_stock" in s.markets
            assert s.risk_level == "medium"

    def test_register_manual(self):
        class Custom(StrategyPlugin):
            name = "custom_reg"
            markets = ["forex"]
            risk_level = "high"
            def generate_signals(self, data): return pd.Series(0, index=data.index)
            def get_parameters(self): return {}

        reg = StrategyRegistry()
        reg.register(Custom())
        assert reg.get("custom_reg") is not None

    def test_unregister(self):
        reg = StrategyRegistry()
        reg.load_all()
        assert reg.unregister("trend_following")
        assert reg.get("trend_following") is None

    def test_vote(self, sample_df):
        reg = StrategyRegistry()
        reg.load_all()
        combined = reg.vote(["trend_following", "mean_reversion"], sample_df)
        assert len(combined) == len(sample_df)
        assert set(combined.unique()).issubset({-1, 0, 1})

    def test_vote_empty(self, sample_df):
        reg = StrategyRegistry()
        combined = reg.vote([], sample_df)
        assert (combined == 0).all()

    def test_vote_missing_strategy(self, sample_df):
        reg = StrategyRegistry()
        reg.load_all()
        combined = reg.vote(["nonexistent"], sample_df)
        assert (combined == 0).all()


# ─── TA-Lib Adapter (Fallback Mode) ────────────────────────────

class TestTALibFallback:
    def test_sma(self, sample_df):
        result = _sma(sample_df["Close"], 20)
        assert len(result) == len(sample_df)
        assert result.iloc[19:].notna().all()

    def test_ema(self, sample_df):
        result = _ema(sample_df["Close"], 20)
        assert result.notna().sum() > 0

    def test_rsi(self, sample_df):
        result = _rsi(sample_df["Close"], 14)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_macd(self, sample_df):
        m, s, h = _macd(sample_df["Close"])
        assert len(m) == len(sample_df)

    def test_bbands(self, sample_df):
        u, m, l = _bbands(sample_df["Close"])
        valid_mask = u.notna() & m.notna() & l.notna()
        assert (u[valid_mask] >= m[valid_mask]).all()
        assert (m[valid_mask] >= l[valid_mask]).all()

    def test_stoch(self, sample_df):
        sk, sd = _stoch(sample_df["High"], sample_df["Low"], sample_df["Close"])
        assert len(sk) == len(sample_df)

    def test_atr(self, sample_df):
        result = _atr(sample_df["High"], sample_df["Low"], sample_df["Close"])
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_adx(self, sample_df):
        result = _adx(sample_df["High"], sample_df["Low"], sample_df["Close"])
        assert len(result) == len(sample_df)

    def test_cci(self, sample_df):
        result = _cci(sample_df["High"], sample_df["Low"], sample_df["Close"])
        assert len(result) == len(sample_df)

    def test_willr(self, sample_df):
        result = _willr(sample_df["High"], sample_df["Low"], sample_df["Close"])
        assert len(result) == len(sample_df)

    def test_mfi(self, sample_df):
        result = _mfi(sample_df["High"], sample_df["Low"], sample_df["Close"], sample_df["Volume"])
        assert len(result) == len(sample_df)


class TestTALibAdapter:
    def test_compute_indicator_sma(self, sample_df):
        result = compute_indicator("sma", sample_df, period=20)
        assert "sma" in result

    def test_compute_indicator_rsi(self, sample_df):
        result = compute_indicator("rsi", sample_df, period=14)
        assert "rsi" in result

    def test_compute_indicator_macd(self, sample_df):
        result = compute_indicator("macd", sample_df)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result

    def test_compute_indicator_bbands(self, sample_df):
        result = compute_indicator("bbands", sample_df)
        assert "upper" in result and "lower" in result

    def test_compute_unknown(self, sample_df):
        with pytest.raises(ValueError, match="Unknown indicator"):
            compute_indicator("nonexistent_xyz", sample_df)

    def test_available_indicators(self):
        inds = available_indicators()
        assert "rsi" in inds
        assert "sma" in inds

    def test_signal_generator_rsi(self, sample_df):
        gen = TALibSignalGenerator("rsi", period=14, overbought=70, oversold=30)
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)
        assert set(signals.unique()).issubset({-1, 0, 1})

    def test_signal_generator_macd(self, sample_df):
        gen = TALibSignalGenerator("macd")
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_signal_generator_bbands(self, sample_df):
        gen = TALibSignalGenerator("bbands")
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_signal_generator_sma(self, sample_df):
        gen = TALibSignalGenerator("sma", period=20)
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_signal_generator_stoch(self, sample_df):
        gen = TALibSignalGenerator("stoch")
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_signal_generator_cci(self, sample_df):
        gen = TALibSignalGenerator("cci")
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_signal_generator_adx(self, sample_df):
        gen = TALibSignalGenerator("adx")
        signals = gen.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_talib_strategy_convenience(self, sample_df):
        s = talib_strategy("rsi", name="my_rsi", period=14)
        assert s.name == "my_rsi"
        signals = s.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_get_parameters(self):
        gen = TALibSignalGenerator("rsi", period=14, overbought=80)
        params = gen.get_parameters()
        assert params["indicator"] == "rsi"
        assert params["period"] == 14

    def test_metadata(self):
        gen = TALibSignalGenerator("macd", markets=["crypto"])
        assert "crypto" in gen.markets
        assert "macd" in gen.name.lower()


# ─── Backtrader Adapter ────────────────────────────────────────

class TestBacktraderAdapter:
    def test_adapter_without_backtrader(self, sample_df):
        """BacktraderAdapter works structurally even without backtrader."""
        adapter = BacktraderAdapter(
            bt_strategy_cls=None,
            name="test_bt",
            markets=["us_stock"],
        )
        assert adapter.name == "test_bt"
        with pytest.raises((ImportError, ValueError)):
            adapter.generate_signals(sample_df)

    def test_get_parameters_no_cls(self):
        adapter = BacktraderAdapter(name="empty")
        params = adapter.get_parameters()
        assert isinstance(params, dict)

    def test_backtest_config(self):
        adapter = BacktraderAdapter(name="cfg")
        config = adapter.backtest_config()
        assert "initial_capital" in config

    def test_pandas_line(self):
        s = pd.Series([10.0, 20.0, 30.0])
        line = _PandasLine(s)
        line.set_idx(1)
        assert line[0] == 20.0
        assert line[-1] == 10.0
        assert float(line) == 20.0

    def test_pandas_data_feed(self, sample_df):
        feed = _PandasDataFeed(sample_df)
        feed.set_idx(10)
        assert feed.close[0] > 0
        assert feed[0] == feed.close[0]
        assert len(feed) == len(sample_df)

    def test_signal_collector(self):
        collector = _SignalCollector()
        collector.set_bar(5)
        collector.buy()
        collector.set_bar(10)
        collector.sell()
        assert len(collector.signals) == 2
        assert collector.signals[0] == (5, 1)
        assert collector.signals[1] == (10, -1)


# ─── Pine Script Parser ────────────────────────────────────────

class TestPineParser:
    def test_parse_sma_cross(self):
        code = """
//@version=5
strategy("SMA Cross")
fast = ta.sma(close, 10)
slow = ta.sma(close, 50)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
        parser = PineParser(code)
        assert "fast" in parser.variables
        assert "slow" in parser.variables
        assert len(parser.entry_conditions) >= 1
        assert len(parser.close_conditions) >= 1

    def test_pine_plugin_signals(self, sample_df):
        code = """
//@version=5
strategy("SMA Cross")
fast = ta.sma(close, 10)
slow = ta.sma(close, 50)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
        plugin = PineScriptPlugin(code, name="pine_test")
        signals = plugin.generate_signals(sample_df)
        assert len(signals) == len(sample_df)
        assert set(signals.unique()).issubset({-1, 0, 1})

    def test_pine_rsi_strategy(self, sample_df):
        code = """
//@version=5
strategy("RSI Strategy")
rsi = ta.rsi(close, 14)
if rsi < 30
    strategy.entry("Long", strategy.long)
if rsi > 70
    strategy.close("Long")
"""
        plugin = from_pine(code, name="pine_rsi")
        signals = plugin.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_pine_ema_strategy(self, sample_df):
        code = """
//@version=5
strategy("EMA Cross")
fast = ta.ema(close, 12)
slow = ta.ema(close, 26)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
        plugin = PineScriptPlugin(code, name="pine_ema")
        signals = plugin.generate_signals(sample_df)
        assert len(signals) == len(sample_df)

    def test_pine_metadata(self):
        code = 'strategy("My Strategy")\nfast = ta.sma(close, 10)'
        plugin = PineScriptPlugin(code, name="meta_test", risk_level="high", markets=["crypto"])
        assert plugin.name == "meta_test"
        assert plugin.risk_level == "high"
        assert plugin.description == "My Strategy"

    def test_pine_source_code(self):
        code = "strategy(\"test\")\nfast = ta.sma(close, 10)"
        plugin = PineScriptPlugin(code)
        assert plugin.source_code == code

    def test_pine_get_parameters(self):
        code = "fast = ta.sma(close, 10)\nslow = ta.sma(close, 50)"
        plugin = PineScriptPlugin(code)
        params = plugin.get_parameters()
        assert "fast" in params["variables"]

    def test_from_pine_convenience(self, sample_df):
        plugin = from_pine("fast = ta.sma(close, 10)", name="conv")
        assert plugin.name == "conv"
