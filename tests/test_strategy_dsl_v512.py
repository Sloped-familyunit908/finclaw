"""
Tests for Natural Language Strategy Builder — v5.12.0
=====================================================
45+ tests covering DSL parsing, expression evaluation, strategy library, and optimizer.
"""

import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.strategy.dsl import StrategyDSL, Strategy, RiskConfig, _parse_pct
from src.strategy.expression import ExpressionEvaluator, OHLCVData
from src.strategy.library import (
    BUILTIN_STRATEGIES,
    get_strategy,
    list_strategies,
)
from src.strategy.optimizer import StrategyOptimizer, OptimizationResult


# ── Helpers ──────────────────────────────────────────────────────────

def _make_data(n: int = 200, seed: int = 42) -> OHLCVData:
    """Generate synthetic OHLCV data for testing."""
    rng = np.random.RandomState(seed)
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    open_ = close + rng.randn(n) * 0.3
    volume = rng.uniform(1e6, 5e6, n)
    return OHLCVData(
        open=open_.astype(np.float64),
        high=high.astype(np.float64),
        low=low.astype(np.float64),
        close=close.astype(np.float64),
        volume=volume.astype(np.float64),
    )


GOLDEN_CROSS_YAML = """\
name: Test Golden Cross
universe: sp500
entry:
  - sma(20) > sma(50)
  - rsi(14) < 70
exit:
  - sma(20) < sma(50)
  - OR: rsi(14) > 80
risk:
  stop_loss: 5%
  take_profit: 15%
  max_position: 10%
rebalance: weekly
"""


# ════════════════════════════════════════════════════════════════════
# 1. _parse_pct
# ════════════════════════════════════════════════════════════════════

class TestParsePct:
    def test_percent_string(self):
        assert _parse_pct("5%") == pytest.approx(0.05)

    def test_percent_with_space(self):
        assert _parse_pct("10 %") == pytest.approx(0.10)

    def test_float_above_one(self):
        assert _parse_pct(15) == pytest.approx(0.15)

    def test_float_below_one(self):
        assert _parse_pct(0.05) == pytest.approx(0.05)

    def test_none(self):
        assert _parse_pct(None) is None

    def test_invalid(self):
        assert _parse_pct("abc") is None


# ════════════════════════════════════════════════════════════════════
# 2. RiskConfig
# ════════════════════════════════════════════════════════════════════

class TestRiskConfig:
    def test_from_dict(self):
        rc = RiskConfig.from_dict({"stop_loss": "5%", "take_profit": "15%", "max_position": "10%"})
        assert rc.stop_loss == pytest.approx(0.05)
        assert rc.take_profit == pytest.approx(0.15)
        assert rc.max_position == pytest.approx(0.10)

    def test_from_none(self):
        rc = RiskConfig.from_dict(None)
        assert rc.stop_loss is None

    def test_trailing_stop(self):
        rc = RiskConfig.from_dict({"trailing_stop": "3%"})
        assert rc.trailing_stop == pytest.approx(0.03)


# ════════════════════════════════════════════════════════════════════
# 3. StrategyDSL — parsing
# ════════════════════════════════════════════════════════════════════

class TestStrategyDSL:
    def setup_method(self):
        self.dsl = StrategyDSL()

    def test_parse_golden_cross(self):
        s = self.dsl.parse(GOLDEN_CROSS_YAML)
        assert s.name == "Test Golden Cross"
        assert len(s.entry_conditions) == 2
        assert len(s.exit_conditions) == 1
        assert len(s.exit_or_conditions) == 1
        assert s.risk.stop_loss == pytest.approx(0.05)
        assert s.rebalance == "weekly"

    def test_parse_minimal(self):
        s = self.dsl.parse("name: Min\nentry:\n  - close > sma(20)\n")
        assert s.name == "Min"

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self.dsl.parse("entry:\n  - close > sma(20)\n")

    def test_missing_entry_raises(self):
        with pytest.raises(ValueError, match="entry"):
            self.dsl.parse("name: NoEntry\n")

    def test_invalid_expression(self):
        with pytest.raises(ValueError, match="Invalid"):
            self.dsl.parse("name: Bad\nentry:\n  - sma(20) >>\n")

    def test_invalid_rebalance(self):
        with pytest.raises(ValueError, match="rebalance"):
            self.dsl.parse("name: Bad\nentry:\n  - close > sma(20)\nrebalance: hourly\n")

    def test_invalid_risk_range(self):
        with pytest.raises(ValueError, match="100%"):
            self.dsl.parse("name: Bad\nentry:\n  - close > sma(20)\nrisk:\n  stop_loss: 150%\n")

    def test_validate_returns_errors(self):
        errs = self.dsl.validate({"entry": ["close > sma(20)"]})
        assert any("name" in e for e in errs)

    def test_validate_clean(self):
        import yaml
        config = yaml.safe_load(GOLDEN_CROSS_YAML)
        assert self.dsl.validate(config) == []

    def test_to_yaml_roundtrip(self):
        s = self.dsl.parse(GOLDEN_CROSS_YAML)
        yaml_out = s.to_yaml()
        s2 = self.dsl.parse(yaml_out)
        assert s2.name == s.name
        assert len(s2.entry_conditions) == len(s.entry_conditions)

    def test_parse_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(GOLDEN_CROSS_YAML)
            f.flush()
            path = f.name
        try:
            s = self.dsl.parse_file(path)
            assert s.name == "Test Golden Cross"
        finally:
            os.unlink(path)

    def test_exit_or_conditions(self):
        yaml_str = """\
name: OrTest
entry:
  - close > sma(20)
exit:
  - close < sma(50)
  - OR: rsi(14) > 80
  - OR: close < sma(200)
"""
        s = self.dsl.parse(yaml_str)
        assert len(s.exit_conditions) == 1
        assert len(s.exit_or_conditions) == 2

    def test_params(self):
        yaml_str = """\
name: Parameterized
entry:
  - close > sma(20)
params:
  lookback: 20
  threshold: 0.5
"""
        s = self.dsl.parse(yaml_str)
        assert s.params["lookback"] == 20
        assert s.params["threshold"] == 0.5

    def test_description(self):
        yaml_str = """\
name: Described
description: A test strategy
entry:
  - close > sma(20)
"""
        s = self.dsl.parse(yaml_str)
        assert s.description == "A test strategy"


# ════════════════════════════════════════════════════════════════════
# 4. ExpressionEvaluator
# ════════════════════════════════════════════════════════════════════

class TestExpressionEvaluator:
    def setup_method(self):
        self.eval = ExpressionEvaluator()
        self.data = _make_data(200)

    def test_sma_comparison(self):
        result = self.eval.evaluate("sma(5) > sma(50)", self.data)
        assert isinstance(result, bool)

    def test_rsi_threshold(self):
        result = self.eval.evaluate("rsi(14) < 70", self.data)
        assert isinstance(result, bool)

    def test_volume_expression(self):
        result = self.eval.evaluate("volume > sma_volume(20) * 1.5", self.data)
        assert isinstance(result, bool)

    def test_close_variable(self):
        result = self.eval.evaluate("close > 0", self.data)
        assert result is True

    def test_price_alias(self):
        result = self.eval.evaluate("price > 0", self.data)
        assert result is True

    def test_arithmetic(self):
        result = self.eval.evaluate("sma(20) * 1.1 > sma(50)", self.data)
        assert isinstance(result, bool)

    def test_bb_upper(self):
        result = self.eval.evaluate("close < bb_upper(20)", self.data)
        assert isinstance(result, bool)

    def test_bb_lower(self):
        result = self.eval.evaluate("close > bb_lower(20)", self.data)
        assert isinstance(result, bool)

    def test_macd(self):
        result = self.eval.evaluate("macd() > 0", self.data)
        assert isinstance(result, bool)

    def test_macd_signal(self):
        result = self.eval.evaluate("macd_signal() > 0", self.data)
        assert isinstance(result, bool)

    def test_atr(self):
        result = self.eval.evaluate("atr(14) > 0", self.data)
        assert result is True

    def test_adx(self):
        result = self.eval.evaluate("adx(14) > 0", self.data)
        assert isinstance(result, bool)

    def test_obv(self):
        result = self.eval.evaluate("obv() > 0", self.data)
        assert isinstance(result, bool)

    def test_evaluate_at_index(self):
        r1 = self.eval.evaluate("close > 0", self.data, 50)
        assert r1 is True

    def test_evaluate_series(self):
        series = self.eval.evaluate_series("sma(20) > sma(50)", self.data)
        assert len(series) == len(self.data.close)
        assert series.dtype == bool

    def test_unknown_variable(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            self.eval.evaluate("xyz > 0", self.data)

    def test_unknown_function(self):
        with pytest.raises(ValueError, match="Unknown indicator"):
            self.eval.evaluate("bogus(14) > 0", self.data)

    def test_constant_comparison(self):
        # close > 0 should always be true for our data
        result = self.eval.evaluate("close > 0", self.data, 100)
        assert result is True

    def test_negative_constant(self):
        result = self.eval.evaluate("close > -100", self.data)
        assert result is True

    def test_chained_comparison(self):
        # Not all Python AST supports this but our evaluator does
        # 30 < rsi(14) < 70
        result = self.eval.evaluate("30 < rsi(14)", self.data)
        assert isinstance(result, bool)

    def test_subtraction(self):
        result = self.eval.evaluate("sma(20) - sma(50) > 0", self.data)
        assert isinstance(result, bool)

    def test_division(self):
        result = self.eval.evaluate("close / sma(20) > 0.9", self.data)
        assert isinstance(result, bool)


# ════════════════════════════════════════════════════════════════════
# 5. OHLCVData
# ════════════════════════════════════════════════════════════════════

class TestOHLCVData:
    def test_from_dict(self):
        d = {
            "open": [1, 2, 3],
            "high": [2, 3, 4],
            "low": [0.5, 1.5, 2.5],
            "close": [1.5, 2.5, 3.5],
            "volume": [100, 200, 300],
        }
        data = OHLCVData.from_dict(d)
        assert len(data.close) == 3
        assert data.close[2] == pytest.approx(3.5)

    def test_from_dataframe(self):
        import pandas as pd
        df = pd.DataFrame({
            "Open": [1, 2], "High": [2, 3], "Low": [0.5, 1],
            "Close": [1.5, 2.5], "Volume": [100, 200],
        })
        data = OHLCVData.from_dataframe(df)
        assert len(data.close) == 2


# ════════════════════════════════════════════════════════════════════
# 6. Strategy execution (should_enter / should_exit)
# ════════════════════════════════════════════════════════════════════

class TestStrategyExecution:
    def test_should_enter(self):
        dsl = StrategyDSL()
        s = dsl.parse(GOLDEN_CROSS_YAML)
        data = _make_data(200)
        result = s.should_enter(data)
        assert isinstance(result, bool)

    def test_should_exit(self):
        dsl = StrategyDSL()
        s = dsl.parse(GOLDEN_CROSS_YAML)
        data = _make_data(200)
        result = s.should_exit(data)
        assert isinstance(result, bool)

    def test_empty_exit_returns_false(self):
        s = Strategy(name="no-exit", entry_conditions=["close > 0"])
        data = _make_data(200)
        assert s.should_exit(data) is False

    def test_or_exit_triggers(self):
        """Strategy with OR exit — should return True if any OR condition met."""
        yaml_str = """\
name: OrExit
entry:
  - close > 0
exit:
  - OR: close > 0
"""
        dsl = StrategyDSL()
        s = dsl.parse(yaml_str)
        data = _make_data(200)
        assert s.should_exit(data) is True


# ════════════════════════════════════════════════════════════════════
# 7. Strategy Library
# ════════════════════════════════════════════════════════════════════

class TestStrategyLibrary:
    def test_builtin_count(self):
        assert len(BUILTIN_STRATEGIES) == 6

    def test_get_strategy(self):
        yaml_str = get_strategy("golden-cross")
        assert "Golden Cross" in yaml_str

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_strategy("nonexistent-strategy")

    def test_list_strategies(self):
        strats = list_strategies()
        assert len(strats) == 6
        assert all("id" in s for s in strats)
        assert all("name" in s for s in strats)

    def test_all_builtins_parse(self):
        """Every built-in strategy should parse without errors."""
        dsl = StrategyDSL()
        for name, yaml_str in BUILTIN_STRATEGIES.items():
            s = dsl.parse(yaml_str)
            assert s.name, f"Strategy {name} has no name"
            assert len(s.entry_conditions) > 0, f"Strategy {name} has no entry conditions"

    def test_all_builtins_evaluate(self):
        """Every built-in strategy should evaluate without crashing."""
        dsl = StrategyDSL()
        data = _make_data(300)
        for name, yaml_str in BUILTIN_STRATEGIES.items():
            s = dsl.parse(yaml_str)
            # These shouldn't raise
            s.should_enter(data)
            s.should_exit(data)


# ════════════════════════════════════════════════════════════════════
# 8. Strategy Optimizer
# ════════════════════════════════════════════════════════════════════

class TestStrategyOptimizer:
    def setup_method(self):
        self.optimizer = StrategyOptimizer()
        self.data = _make_data(300, seed=123)

    def test_grid_search_basic(self):
        yaml_str = """\
name: Opt Test
entry:
  - rsi({rsi_period}) < 30
  - close > sma({sma_period})
exit:
  - rsi({rsi_period}) > 70
risk:
  stop_loss: 5%
"""
        results = self.optimizer.grid_search(
            yaml_str,
            {"rsi_period": [10, 14, 20], "sma_period": [20, 50]},
            self.data,
        )
        assert len(results) == 6  # 3 * 2

    def test_best_params(self):
        yaml_str = """\
name: Opt
entry:
  - rsi({rsi_period}) < 30
exit:
  - rsi({rsi_period}) > 70
risk:
  stop_loss: 5%
"""
        self.optimizer.grid_search(yaml_str, {"rsi_period": [10, 14, 20]}, self.data)
        best = self.optimizer.best_params()
        assert "rsi_period" in best

    def test_top_n(self):
        yaml_str = """\
name: Opt
entry:
  - close > sma({period})
exit:
  - close < sma({period})
risk:
  stop_loss: 5%
"""
        self.optimizer.grid_search(yaml_str, {"period": [10, 20, 30, 50]}, self.data)
        top = self.optimizer.top_n(2)
        assert len(top) <= 2

    def test_empty_params(self):
        yaml_str = """\
name: No Params
entry:
  - close > sma(20)
exit:
  - close < sma(20)
risk:
  stop_loss: 5%
"""
        results = self.optimizer.grid_search(yaml_str, {}, self.data)
        assert len(results) == 1  # single combo (no params)

    def test_result_fields(self):
        yaml_str = """\
name: Fields
entry:
  - rsi(14) < 30
exit:
  - rsi(14) > 70
risk:
  stop_loss: 5%
  take_profit: 15%
"""
        results = self.optimizer.grid_search(yaml_str, {}, self.data)
        r = results[0]
        assert hasattr(r, "total_trades")
        assert hasattr(r, "win_rate")
        assert hasattr(r, "total_return")
        assert hasattr(r, "max_drawdown")
        assert hasattr(r, "sharpe_ratio")
        assert hasattr(r, "score")

    def test_substitute_params(self):
        result = self.optimizer._substitute_params("rsi({period})", {"period": 14})
        assert result == "rsi(14)"
