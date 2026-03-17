"""Tests for FinClaw v2.4.0 — Paper Trading & Live Integration."""

import asyncio
import math
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.trading.paper_trader import PaperTrader, PaperTradeConfig
from src.trading.oms import Order, OrderManager
from src.sandbox.strategy_sandbox import StrategySandbox, BacktestResult
from src.dashboard.risk_dashboard import RiskDashboard
from src.ml.factor_model import FactorModel, FactorResult
from src.portfolio.tracker import PortfolioTracker


# =====================================================================
# Paper Trader Tests
# =====================================================================

class DummyStrategy:
    def __init__(self, signals=None):
        self._signals = signals or []
    def generate_signals(self, data):
        return self._signals


class TestPaperTrader:
    def test_init_default(self):
        pt = PaperTrader(100000, DummyStrategy())
        assert pt.initial_capital == 100000
        assert pt.running is False

    def test_init_with_config(self):
        pt = PaperTrader(50000, DummyStrategy(), config={"max_position_pct": 0.20, "slippage_bps": 10})
        assert pt.config.max_position_pct == 0.20
        assert pt.config.slippage_bps == 10.0

    def test_stop(self):
        pt = PaperTrader(100000, DummyStrategy())
        pt.running = True
        pt.stop()
        assert pt.running is False

    def test_set_prices(self):
        pt = PaperTrader(100000, DummyStrategy())
        pt.set_prices({"AAPL": 150.0, "MSFT": 300.0})
        assert pt._latest_prices["AAPL"] == 150.0

    def test_risk_check_filters_empty_signals(self):
        pt = PaperTrader(100000, DummyStrategy())
        orders = pt.risk_check([{"ticker": "", "side": "buy", "quantity": 10}])
        assert len(orders) == 0

    def test_risk_check_limits_position_size(self):
        pt = PaperTrader(100000, DummyStrategy())
        pt.set_prices({"AAPL": 150.0})
        # Try to buy $50k worth (50%) — should be capped to 10%
        orders = pt.risk_check([{"ticker": "AAPL", "side": "buy", "quantity": 333, "price": 150.0}])
        if orders:
            assert orders[0].quantity <= 100000 * 0.10 / 150.0 + 1

    def test_execute_buy(self):
        pt = PaperTrader(100000, DummyStrategy())
        pt.set_prices({"AAPL": 150.0})
        order = Order(ticker="AAPL", side="buy", order_type="market", quantity=10, limit_price=150.0)
        result = pt.execute(order)
        assert result.status == "filled"
        assert "AAPL" in pt._positions

    def test_execute_sell(self):
        pt = PaperTrader(100000, DummyStrategy())
        pt.set_prices({"AAPL": 150.0})
        # Buy first
        pt.execute(Order(ticker="AAPL", side="buy", order_type="market", quantity=10, limit_price=150.0))
        # Then sell
        result = pt.execute(Order(ticker="AAPL", side="sell", order_type="market", quantity=10, limit_price=155.0))
        assert result.status == "filled"

    def test_get_performance(self):
        pt = PaperTrader(100000, DummyStrategy())
        perf = pt.get_performance()
        assert "total_trades" in perf
        assert "iterations" in perf

    def test_get_trade_log_empty(self):
        pt = PaperTrader(100000, DummyStrategy())
        assert pt.get_trade_log() == []

    def test_async_start_stop(self):
        """Test that start loop runs and can be stopped."""
        pt = PaperTrader(100000, DummyStrategy(), config={"log_interval": 1})
        pt.set_prices({"AAPL": 150.0})

        async def run():
            task = asyncio.create_task(pt.start(["AAPL"], interval_sec=0))
            await asyncio.sleep(0.05)
            pt.stop()
            await task
            return pt._iteration

        iters = asyncio.run(run())
        assert iters >= 1

    def test_fetch_latest_with_custom_fetcher(self):
        def fetcher(tickers):
            return {t: 100.0 + i for i, t in enumerate(tickers)}

        pt = PaperTrader(100000, DummyStrategy(), price_fetcher=fetcher)

        async def run():
            data = await pt.fetch_latest(["AAPL", "MSFT"])
            return data

        data = asyncio.run(run())
        assert data["AAPL"] == 100.0
        assert data["MSFT"] == 101.0


# =====================================================================
# Strategy Sandbox Tests
# =====================================================================

GOOD_STRATEGY = """
def generate_signals(data):
    price = data.get('close', 0)
    if price < 100:
        return [{'side': 'buy', 'quantity': 10}]
    elif price > 150:
        return [{'side': 'sell', 'quantity': 10}]
    return []
"""

BAD_STRATEGY_IMPORT = """
import os
def generate_signals(data):
    return []
"""

BAD_STRATEGY_EVAL = """
def generate_signals(data):
    eval("1+1")
    return []
"""

NO_SIGNALS_FUNC = """
def my_func(data):
    return []
"""


class TestStrategySandbox:
    def test_validate_good_strategy(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        warnings = sb.validate()
        assert len(warnings) == 0

    def test_validate_import_blocked(self):
        sb = StrategySandbox(BAD_STRATEGY_IMPORT)
        warnings = sb.validate()
        assert any("Forbidden" in w for w in warnings)

    def test_validate_eval_blocked(self):
        sb = StrategySandbox(BAD_STRATEGY_EVAL)
        warnings = sb.validate()
        assert any("eval" in w for w in warnings)

    def test_validate_missing_function(self):
        sb = StrategySandbox(NO_SIGNALS_FUNC)
        warnings = sb.validate()
        assert any("generate_signals" in w for w in warnings)

    def test_compile_good(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        assert sb.compile() is True

    def test_compile_bad(self):
        sb = StrategySandbox(BAD_STRATEGY_IMPORT)
        assert sb.compile() is False

    def test_backtest_basic(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = [{"date": f"2024-01-{i:02d}", "close": 80 + i * 5} for i in range(1, 20)]
        result = sb.backtest(data)
        assert isinstance(result, BacktestResult)
        assert result.num_trades >= 0
        assert len(result.equity_curve) > 0

    def test_backtest_returns(self):
        sb = StrategySandbox(GOOD_STRATEGY)
        data = (
            [{"date": f"d{i}", "close": 90} for i in range(5)] +
            [{"date": f"d{i}", "close": 160} for i in range(5, 10)]
        )
        result = sb.backtest(data)
        assert result.num_trades >= 1

    def test_syntax_error(self):
        sb = StrategySandbox("def foo(:\n  pass")
        warnings = sb.validate()
        assert any("Syntax" in w for w in warnings)


# =====================================================================
# Risk Dashboard Tests
# =====================================================================

class TestRiskDashboard:
    def _make_portfolio(self):
        import tempfile, os
        storage = os.path.join(tempfile.mkdtemp(), "portfolio.json")
        p = PortfolioTracker(storage_path=storage, price_fetcher=lambda s: 160.0)
        p.add("AAPL", 100, 150)
        p.add("MSFT", 50, 300)
        return p

    def test_current_risk_basic(self):
        dashboard = RiskDashboard()
        p = self._make_portfolio()
        risk = dashboard.current_risk(p, {"AAPL": 160, "MSFT": 320})
        assert "var_95" in risk
        assert "sector_exposure" in risk
        assert risk["num_positions"] == 2

    def test_current_risk_empty_portfolio(self):
        import tempfile, os
        storage = os.path.join(tempfile.mkdtemp(), "portfolio.json")
        dashboard = RiskDashboard()
        p = PortfolioTracker(storage_path=storage, price_fetcher=lambda s: None)
        risk = dashboard.current_risk(p)
        assert risk["total_value"] == 0.0 or risk["num_positions"] == 0

    def test_sector_exposure(self):
        dashboard = RiskDashboard()
        p = self._make_portfolio()
        risk = dashboard.current_risk(p, {"AAPL": 160, "MSFT": 320})
        assert "Technology" in risk["sector_exposure"]

    def test_render_html(self, tmp_path):
        dashboard = RiskDashboard()
        p = self._make_portfolio()
        out = tmp_path / "risk.html"
        html = dashboard.render_html(p, {"AAPL": 160, "MSFT": 320}, str(out))
        assert "FinClaw" in html
        assert out.exists()

    def test_concentration_risk(self):
        import tempfile, os
        storage = os.path.join(tempfile.mkdtemp(), "portfolio.json")
        dashboard = RiskDashboard()
        p = PortfolioTracker(storage_path=storage, price_fetcher=lambda s: 150.0)
        p.add("AAPL", 600, 150)  # all in one stock
        risk = dashboard.current_risk(p, {"AAPL": 150})
        assert risk["concentration_risk"] >= 0.9  # ~1.0 for single stock


# =====================================================================
# Factor Model Tests
# =====================================================================

class TestFactorModel:
    def _sample_data(self, n=100):
        """Generate synthetic factor returns and asset returns."""
        import random
        random.seed(42)
        market = [random.gauss(0.0005, 0.01) for _ in range(n)]
        size = [random.gauss(0.0002, 0.005) for _ in range(n)]
        value = [random.gauss(0.0001, 0.005) for _ in range(n)]
        # Asset return = 0.001 + 1.2*mkt + 0.3*size - 0.2*value + noise
        returns = [
            0.001 + 1.2 * market[i] + 0.3 * size[i] - 0.2 * value[i] + random.gauss(0, 0.002)
            for i in range(n)
        ]
        factor_returns = {"market": market, "size": size, "value": value}
        return returns, factor_returns

    def test_fit_basic(self):
        fm = FactorModel(["market", "size", "value"])
        returns, factors = self._sample_data()
        result = fm.fit(returns, factors)
        assert isinstance(result, FactorResult)
        assert result.r_squared > 0.5
        assert abs(result.betas["market"] - 1.2) < 0.3

    def test_predict(self):
        fm = FactorModel(["market", "size", "value"])
        returns, factors = self._sample_data()
        fm.fit(returns, factors)
        pred = fm.predict({"market": 0.01, "size": 0.005, "value": -0.003})
        assert isinstance(pred, float)
        assert pred != 0

    def test_decompose(self):
        fm = FactorModel(["market", "size", "value"])
        returns, factors = self._sample_data()
        result = fm.decompose(returns, factors)
        assert "contributions" in result
        assert "pct_attribution" in result
        assert "market" in result["contributions"]

    def test_fit_insufficient_data(self):
        fm = FactorModel()
        result = fm.fit([0.01, 0.02], {"market": [0.01, 0.02]})
        assert result.r_squared == 0.0

    def test_fit_no_matching_factors(self):
        fm = FactorModel(["market"])
        result = fm.fit([0.01] * 20, {"other": [0.01] * 20})
        # Should still compute alpha
        assert isinstance(result, FactorResult)

    def test_predict_unfitted(self):
        fm = FactorModel()
        assert fm.predict({"market": 0.01}) == 0.0

    def test_alpha_significance(self):
        fm = FactorModel(["market", "size", "value"])
        returns, factors = self._sample_data(200)
        result = fm.fit(returns, factors)
        assert "alpha" in result.t_stats


# =====================================================================
# OMS Additional Tests (round out coverage)
# =====================================================================

class TestOMSExtended:
    def test_cancel_nonexistent(self):
        oms = OrderManager()
        assert oms.cancel_order("fake-id") is False

    def test_stop_limit_order(self):
        oms = OrderManager()
        order = Order(ticker="AAPL", side="sell", order_type="stop_limit",
                      quantity=10, stop_price=140, limit_price=138)
        result = oms.submit_order(order)
        assert result.status == "open"
        fills = oms.check_stops_and_limits({"AAPL": 139})
        assert len(fills) == 1

    def test_limit_buy_triggered(self):
        oms = OrderManager()
        order = Order(ticker="MSFT", side="buy", order_type="limit",
                      quantity=5, limit_price=300)
        oms.submit_order(order)
        fills = oms.check_stops_and_limits({"MSFT": 295})
        assert len(fills) == 1
        assert fills[0].status == "filled"

    def test_order_history(self):
        oms = OrderManager()
        oms.submit_order(Order(ticker="A", side="buy", order_type="market", quantity=1, limit_price=10))
        oms.submit_order(Order(ticker="B", side="buy", order_type="market", quantity=1, limit_price=20))
        history = oms.get_order_history()
        assert len(history) == 2
