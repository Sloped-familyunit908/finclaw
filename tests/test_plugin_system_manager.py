"""
Tests for FinClaw Plugin System v4.3.0
40+ tests covering plugin base, manager, strategy, indicator, exchange plugins, and CLI.
"""

import os
import sys
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.plugin_base import Plugin
from src.plugins.plugin_manager import PluginManager, PluginInfo
from src.plugins.strategy_plugin import StrategyPlugin
from src.plugins.indicator_plugin import IndicatorPlugin
from src.plugins.exchange_plugin import ExchangePlugin


# ─── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def tmp_plugin_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def pm(tmp_plugin_dir):
    return PluginManager(plugin_dir=tmp_plugin_dir)


@pytest.fixture
def sample_ohlcv():
    """Generate sample OHLCV data for testing."""
    import random
    random.seed(42)
    base = 100.0
    candles = []
    for i in range(100):
        o = base + random.uniform(-2, 2)
        h = o + random.uniform(0, 3)
        l = o - random.uniform(0, 3)
        c = (o + h + l) / 3
        candles.append({
            "timestamp": 1700000000 + i * 86400,
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": round(random.uniform(1000, 10000), 2),
        })
        base = c
    return candles


def _write_plugin(directory, name, content):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{name}.py")
    with open(path, "w") as f:
        f.write(content)
    return path


SIMPLE_STRATEGY = '''
from src.plugins.strategy_plugin import StrategyPlugin

class SimpleStrategy(StrategyPlugin):
    name = "simple_test"
    version = "1.0.0"
    description = "Test strategy"

    def generate_signals(self, data):
        return [{"action": "buy", "symbol": "TEST", "confidence": 0.5, "reason": "test"}]

    def get_parameters(self):
        return {"window": 10}
'''

SIMPLE_INDICATOR = '''
from src.plugins.indicator_plugin import IndicatorPlugin

class SimpleIndicator(IndicatorPlugin):
    name = "simple_indicator"
    version = "1.0.0"
    description = "Test indicator"

    def calculate(self, data, **params):
        p = self.validate_params(**params)
        return [{"timestamp": d.get("timestamp"), "value": d["close"]} for d in data[-p["period"]:]]

    def get_params_schema(self):
        return {"period": {"type": "int", "default": 14, "min": 1, "max": 200}}
'''

LEGACY_PLUGIN = '''
PLUGIN_TYPE = "strategy"
__version__ = "0.5.0"
__description__ = "Legacy style plugin"

def register(manager):
    manager.add_strategy("legacy_test", {"type": "legacy"})
'''


# ─── Plugin Base Tests ────────────────────────────────────────────

class TestPluginBase:
    def test_plugin_is_abstract(self):
        """Plugin can be subclassed."""
        class MyPlugin(Plugin):
            name = "my"
            version = "1.0"
            description = "test"
        p = MyPlugin()
        assert p.name == "my"

    def test_get_info(self):
        class MyPlugin(Plugin):
            name = "my"
            version = "2.0"
            description = "desc"
            plugin_type = "custom"
        info = MyPlugin().get_info()
        assert info["name"] == "my"
        assert info["version"] == "2.0"
        assert info["type"] == "custom"

    def test_on_load_default(self):
        class MyPlugin(Plugin):
            name = "t"
        p = MyPlugin()
        result = p.on_load({})  # should not raise
        assert result is None, "Default on_load should return None"

    def test_on_unload_default(self):
        class MyPlugin(Plugin):
            name = "t"
        p = MyPlugin()
        result = p.on_unload()  # should not raise
        assert result is None, "Default on_unload should return None"


# ─── PluginManager Tests ─────────────────────────────────────────

class TestPluginManager:
    def test_init_default_dir(self):
        pm = PluginManager()
        assert "finclaw" in pm.plugin_dir

    def test_init_custom_dir(self, tmp_plugin_dir):
        pm = PluginManager(plugin_dir=tmp_plugin_dir)
        assert pm.plugin_dir == tmp_plugin_dir

    def test_discover_empty(self, pm):
        assert pm.discover() == []

    def test_discover_finds_plugins(self, pm):
        _write_plugin(pm.plugin_dir, "test_plug", SIMPLE_STRATEGY)
        found = pm.discover()
        assert "test_plug" in found

    def test_discover_ignores_underscored(self, pm):
        _write_plugin(pm.plugin_dir, "_hidden", SIMPLE_STRATEGY)
        assert "_hidden" not in pm.discover()

    def test_load_strategy(self, pm):
        _write_plugin(pm.plugin_dir, "strat", SIMPLE_STRATEGY)
        info = pm.load("strat")
        assert info.name == "simple_test"
        assert info.plugin_type == "strategy"
        assert info.version == "1.0.0"

    def test_load_by_path(self, pm, tmp_path):
        path = _write_plugin(str(tmp_path / "other"), "mystrat", SIMPLE_STRATEGY)
        info = pm.load(path)
        assert info.name == "simple_test"

    def test_load_duplicate_raises(self, pm):
        _write_plugin(pm.plugin_dir, "dup", SIMPLE_STRATEGY)
        pm.load("dup")
        # Plugin registers under its class name "simple_test", so loading same file
        # under a different filename but same class name should raise
        _write_plugin(pm.plugin_dir, "dup2", SIMPLE_STRATEGY)
        with pytest.raises(ValueError, match="already loaded"):
            pm.load("dup2")

    def test_load_missing_raises(self, pm):
        with pytest.raises(FileNotFoundError):
            pm.load("nonexistent")

    def test_load_indicator(self, pm):
        _write_plugin(pm.plugin_dir, "ind", SIMPLE_INDICATOR)
        info = pm.load("ind")
        assert info.plugin_type == "indicator"
        assert "simple_indicator" in pm.indicators

    def test_load_legacy_plugin(self, pm):
        _write_plugin(pm.plugin_dir, "legacy", LEGACY_PLUGIN)
        info = pm.load("legacy")
        assert info.plugin_type == "strategy"
        assert "legacy_test" in pm.strategies

    def test_unload(self, pm):
        _write_plugin(pm.plugin_dir, "unl", SIMPLE_STRATEGY)
        pm.load("unl")
        assert pm.unload("simple_test")
        assert pm.list_plugins() == []

    def test_unload_nonexistent(self, pm):
        assert pm.unload("nope") is False

    def test_load_all(self, pm):
        _write_plugin(pm.plugin_dir, "a", SIMPLE_STRATEGY)
        _write_plugin(pm.plugin_dir, "b", SIMPLE_INDICATOR)
        loaded = pm.load_all()
        assert len(loaded) == 2

    def test_list_plugins(self, pm):
        _write_plugin(pm.plugin_dir, "lp", SIMPLE_STRATEGY)
        pm.load("lp")
        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "simple_test"

    def test_get_plugin(self, pm):
        _write_plugin(pm.plugin_dir, "gp", SIMPLE_STRATEGY)
        pm.load("gp")
        assert pm.get_plugin("simple_test") is not None
        assert pm.get_plugin("nope") is None

    def test_install(self, pm, tmp_path):
        src = _write_plugin(str(tmp_path / "source"), "inst", SIMPLE_STRATEGY)
        info = pm.install(src)
        assert info.name == "simple_test"
        assert os.path.isfile(os.path.join(pm.plugin_dir, "inst.py"))

    def test_install_missing_raises(self, pm):
        with pytest.raises(FileNotFoundError):
            pm.install("/nonexistent/path.py")

    def test_create_strategy(self, pm):
        path = pm.create("my_strat", "strategy")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "StrategyPlugin" in content
        assert "my_strat" in content

    def test_create_indicator(self, pm):
        path = pm.create("my_ind", "indicator")
        with open(path) as f:
            content = f.read()
        assert "IndicatorPlugin" in content

    def test_create_exchange(self, pm):
        path = pm.create("my_ex", "exchange")
        with open(path) as f:
            content = f.read()
        assert "ExchangePlugin" in content

    def test_create_duplicate_raises(self, pm):
        pm.create("dup_create", "strategy")
        with pytest.raises(FileExistsError):
            pm.create("dup_create", "strategy")

    def test_set_context(self, pm):
        pm.set_context({"key": "val"})
        assert pm._context["key"] == "val"

    def test_strategies_accessor(self, pm):
        _write_plugin(pm.plugin_dir, "sa", SIMPLE_STRATEGY)
        pm.load("sa")
        assert "simple_test" in pm.strategies

    def test_exchanges_accessor(self, pm):
        assert isinstance(pm.exchanges, dict)


# ─── Strategy Plugin Tests ───────────────────────────────────────

class TestStrategyPlugin:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            StrategyPlugin()

    def test_generate_signals(self, sample_ohlcv):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        signals = s.generate_signals({"ohlcv": sample_ohlcv, "symbol": "TEST"})
        assert isinstance(signals, list)
        for sig in signals:
            assert sig["action"] in ("buy", "sell", "hold")
            assert "confidence" in sig

    def test_get_parameters(self):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        params = s.get_parameters()
        assert "window" in params
        assert "threshold" in params

    def test_set_parameters(self):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        s.set_parameters({"window": 30})
        assert s.window == 30

    def test_optimize(self, sample_ohlcv):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        result = s.optimize({"ohlcv": sample_ohlcv, "symbol": "TEST"})
        assert "window" in result
        assert "threshold" in result

    def test_backtest(self, sample_ohlcv):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        result = s.backtest({"ohlcv": sample_ohlcv, "symbol": "TEST"})
        assert "signals_count" in result
        assert "buy_count" in result
        assert "sell_count" in result

    def test_rsi_divergence(self, sample_ohlcv):
        from src.plugins.examples.rsi_divergence_plugin import RSIDivergenceStrategy
        s = RSIDivergenceStrategy()
        signals = s.generate_signals({"ohlcv": sample_ohlcv, "symbol": "TEST"})
        assert isinstance(signals, list)

    def test_rsi_get_parameters(self):
        from src.plugins.examples.rsi_divergence_plugin import RSIDivergenceStrategy
        s = RSIDivergenceStrategy()
        p = s.get_parameters()
        assert "rsi_period" in p

    def test_rsi_insufficient_data(self):
        from src.plugins.examples.rsi_divergence_plugin import RSIDivergenceStrategy
        s = RSIDivergenceStrategy()
        signals = s.generate_signals({"ohlcv": [{"close": 100}] * 5, "symbol": "X"})
        assert signals == []

    def test_mean_reversion_insufficient_data(self):
        from src.plugins.examples.mean_reversion_plugin import MeanReversionStrategy
        s = MeanReversionStrategy()
        signals = s.generate_signals({"ohlcv": [{"close": 100}] * 5, "symbol": "X"})
        assert signals == []


# ─── Indicator Plugin Tests ──────────────────────────────────────

class TestIndicatorPlugin:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            IndicatorPlugin()

    def test_validate_params_defaults(self):
        class TestInd(IndicatorPlugin):
            name = "t"
            def calculate(self, data, **p): return []
            def get_params_schema(self):
                return {"period": {"type": "int", "default": 14, "min": 1, "max": 200}}
        ind = TestInd()
        params = ind.validate_params()
        assert params["period"] == 14

    def test_validate_params_custom(self):
        class TestInd(IndicatorPlugin):
            name = "t"
            def calculate(self, data, **p): return []
            def get_params_schema(self):
                return {"period": {"type": "int", "default": 14, "min": 1, "max": 200}}
        ind = TestInd()
        params = ind.validate_params(period=30)
        assert params["period"] == 30

    def test_validate_params_out_of_range(self):
        class TestInd(IndicatorPlugin):
            name = "t"
            def calculate(self, data, **p): return []
            def get_params_schema(self):
                return {"period": {"type": "int", "default": 14, "min": 1, "max": 200}}
        ind = TestInd()
        with pytest.raises(ValueError, match="must be >="):
            ind.validate_params(period=0)
        with pytest.raises(ValueError, match="must be <="):
            ind.validate_params(period=300)


# ─── Exchange Plugin Tests ───────────────────────────────────────

class TestExchangePlugin:
    def test_demo_exchange(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        assert ex.name == "demo_exchange"
        assert ex.exchange_type == "demo"

    def test_demo_get_ticker(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        t = ex.get_ticker("BTCUSDT")
        assert t["symbol"] == "BTCUSDT"
        assert "last" in t

    def test_demo_get_ohlcv(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        candles = ex.get_ohlcv("BTCUSDT", limit=10)
        assert len(candles) == 10
        assert "close" in candles[0]

    def test_demo_orderbook(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        ob = ex.get_orderbook("BTCUSDT", depth=5)
        assert len(ob["bids"]) == 5
        assert len(ob["asks"]) == 5

    def test_demo_place_order(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        order = ex.place_order("BTCUSDT", "buy", "market", 1.0)
        assert order["status"] == "filled"

    def test_demo_balance(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        ex = DemoExchange()
        b = ex.get_balance()
        assert "USDT" in b

    def test_demo_on_load_registers(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        from src.exchanges.registry import ExchangeRegistry
        ex = DemoExchange()
        ex.on_load({})
        assert "demo_exchange" in ExchangeRegistry.list_exchanges()
        # cleanup
        ex.on_unload()

    def test_demo_on_unload_unregisters(self):
        from src.plugins.examples.custom_exchange_plugin import DemoExchange
        from src.exchanges.registry import ExchangeRegistry
        ex = DemoExchange()
        ex.on_load({})
        ex.on_unload()
        assert "demo_exchange" not in ExchangeRegistry.list_exchanges()


# ─── CLI Plugin Tests ────────────────────────────────────────────

class TestPluginCLI:
    def test_plugin_list_empty(self, capsys):
        from src.cli import main
        main(["plugin", "list"])
        out = capsys.readouterr().out
        assert "No plugins" in out or "Plugins" in out

    def test_plugin_create_strategy(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FINCLAW_PLUGIN_DIR", str(tmp_path))
        from src.plugins.plugin_manager import PluginManager
        pm = PluginManager(plugin_dir=str(tmp_path))
        path = pm.create("test_cli_strat", "strategy")
        assert os.path.isfile(path)

    def test_plugin_help(self, capsys):
        from src.cli import main
        main(["plugin"])
        out = capsys.readouterr().out
        assert "Usage" in out or "plugin" in out.lower()
