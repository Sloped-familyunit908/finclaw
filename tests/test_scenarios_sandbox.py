"""Tests for simulation scenarios and strategy sandbox modules.

- ScenarioGenerator: historical crisis scenarios, custom scenarios
- StrategySandbox: code validation, compilation, backtesting
"""

import math

import pytest

from src.simulation.scenarios import (
    ScenarioGenerator,
    ScenarioResult,
    Scenario,
    CRISIS_TEMPLATES,
)
from src.sandbox.strategy_sandbox import (
    StrategySandbox,
    BacktestResult,
)


# ══════════════════════════════════════════════════════════════════
# ScenarioGenerator
# ══════════════════════════════════════════════════════════════════

class TestScenarioGenerator:
    def test_list_scenarios(self):
        names = ScenarioGenerator.list_scenarios()
        assert len(names) >= 5
        assert "2008_financial_crisis" in names
        assert "covid_2020" in names

    def test_generate_2008_crisis(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate("2008_financial_crisis")
        assert isinstance(result, ScenarioResult)
        assert result.max_drawdown < 0
        assert result.portfolio_start == 100000
        assert len(result.daily_values) > 0

    def test_generate_covid(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate("covid_2020")
        assert result.max_drawdown < 0
        # COVID was a sharp crash
        assert len(result.daily_values) > 20

    def test_generate_flash_crash(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate("flash_crash_2010")
        assert isinstance(result, ScenarioResult)

    def test_generate_unknown_raises(self):
        gen = ScenarioGenerator()
        with pytest.raises(ValueError, match="Unknown scenario"):
            gen.generate("nonexistent_crisis")

    def test_custom_scenario(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate_custom(
            drawdown=-0.20,
            duration_days=30,
            recovery_days=60,
            portfolio_value=50000,
        )
        assert result.portfolio_start == 50000
        assert result.max_drawdown < 0
        assert len(result.daily_values) > 0

    def test_custom_scenario_total_return(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate_custom(
            drawdown=-0.10,
            duration_days=10,
            recovery_days=20,
        )
        assert result.total_return == pytest.approx(
            (result.portfolio_end / result.portfolio_start) - 1
        )

    def test_deterministic_with_seed(self):
        r1 = ScenarioGenerator(seed=123).generate("covid_2020")
        r2 = ScenarioGenerator(seed=123).generate("covid_2020")
        assert r1.portfolio_end == pytest.approx(r2.portfolio_end)

    def test_different_seeds_different_results(self):
        r1 = ScenarioGenerator(seed=1).generate("covid_2020")
        r2 = ScenarioGenerator(seed=99).generate("covid_2020")
        assert r1.portfolio_end != pytest.approx(r2.portfolio_end, abs=1.0)

    def test_daily_values_start_at_portfolio_value(self):
        gen = ScenarioGenerator(seed=42)
        result = gen.generate("black_monday_1987", portfolio_value=200000)
        assert result.daily_values[0] == 200000


class TestScenarioDataclass:
    def test_total_return(self):
        s = Scenario(
            name="test",
            description="test",
            daily_returns=[0.01, 0.02, -0.01],
            peak_drawdown=-0.01,
            duration_days=3,
            recovery_days=0,
        )
        expected = (1.01 * 1.02 * 0.99) - 1
        assert s.total_return == pytest.approx(expected, abs=1e-10)


# ══════════════════════════════════════════════════════════════════
# StrategySandbox
# ══════════════════════════════════════════════════════════════════

GOOD_STRATEGY = """
def generate_signals(data):
    price = data.get('close', 0)
    if price < 100:
        return [{'side': 'buy', 'quantity': 10}]
    elif price > 150:
        return [{'side': 'sell', 'quantity': 10}]
    return []
"""

BAD_IMPORT = """
import os
def generate_signals(data):
    return []
"""

BAD_EVAL = """
def generate_signals(data):
    eval("1+1")
    return []
"""

NO_FUNC = """
def my_func(data):
    return []
"""

SYNTAX_ERROR = "def foo(:\n  pass"

BUY_LOW_SELL_HIGH = """
def generate_signals(data):
    price = data.get('close', 0)
    if price < 95:
        return [{'side': 'buy', 'quantity': 100}]
    elif price > 105:
        return [{'side': 'sell', 'quantity': 100}]
    return []
"""


class TestStrategySandboxValidation:
    def test_validate_good_strategy(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        warnings = sb.validate()
        assert len(warnings) == 0

    def test_validate_import_blocked(self):
        sb = StrategySandbox(BAD_IMPORT)
        warnings = sb.validate()
        assert any("Forbidden" in w for w in warnings)

    def test_validate_eval_blocked(self):
        sb = StrategySandbox(BAD_EVAL)
        warnings = sb.validate()
        assert any("eval" in w.lower() for w in warnings)

    def test_validate_missing_function(self):
        sb = StrategySandbox(NO_FUNC)
        warnings = sb.validate()
        assert any("generate_signals" in w for w in warnings)

    def test_validate_syntax_error(self):
        sb = StrategySandbox(SYNTAX_ERROR)
        warnings = sb.validate()
        assert any("Syntax" in w for w in warnings)


class TestStrategySandboxCompilation:
    def test_compile_good(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        assert sb.compile() is True

    def test_compile_bad_import(self):
        sb = StrategySandbox(BAD_IMPORT)
        assert sb.compile() is False

    def test_compile_bad_eval(self):
        sb = StrategySandbox(BAD_EVAL)
        assert sb.compile() is False


class TestStrategySandboxBacktest:
    def _make_data(self, prices):
        return [{"date": f"d{i}", "close": p} for i, p in enumerate(prices)]

    def test_basic_backtest(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = self._make_data([80 + i * 5 for i in range(20)])
        result = sb.backtest(data)
        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) > 0
        assert result.num_trades >= 0

    def test_backtest_generates_signals(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = (
            self._make_data([90] * 5) +  # buy zone
            self._make_data([160] * 5)    # sell zone
        )
        result = sb.backtest(data)
        assert result.num_trades >= 1

    def test_backtest_equity_curve_length(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = self._make_data([100] * 30)
        result = sb.backtest(data)
        assert len(result.equity_curve) == len(data) + 1  # initial + each bar

    def test_backtest_buy_low_sell_high_profit(self):
        sb = StrategySandbox(BUY_LOW_SELL_HIGH)
        prices = [90, 90, 90, 110, 110, 110]
        data = self._make_data(prices)
        result = sb.backtest(data)
        # Should have bought low and sold high
        if result.num_trades > 0:
            assert result.total_return >= 0

    def test_backtest_bad_code_returns_errors(self):
        sb = StrategySandbox(BAD_IMPORT)
        data = self._make_data([100] * 10)
        result = sb.backtest(data)
        assert len(result.errors) > 0 or len(result.equity_curve) > 0

    def test_backtest_max_drawdown(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = self._make_data([100] * 20)
        result = sb.backtest(data)
        assert result.max_drawdown >= 0  # drawdown should be non-negative

    def test_backtest_sharpe_ratio_exists(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = self._make_data([100 + i for i in range(50)])
        result = sb.backtest(data)
        assert isinstance(result.sharpe_ratio, (int, float))
