"""
Tests for FinClaw v4.2.0 — Live Trading Engine, Risk Guard,
Paper Trading, and Dashboard.
45 tests covering all new components.
"""

import asyncio
import math
import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.trading.oms import Order, OrderManager, OrderResult
from src.trading.risk_guard import RiskGuard, RiskConfig, RiskResult
from src.trading.live_engine import LiveTradingEngine
from src.trading.paper_trading import PaperTradingEngine
from src.trading.dashboard import TradingDashboard
from src.events.event_bus import EventBus


# =====================================================================
# Helpers
# =====================================================================

def run_async(coro):
    """Run async coroutine synchronously."""
    return asyncio.run(coro)


class DummyStrategy:
    def __init__(self, signals=None):
        self._signals = signals or []

    def generate_signals(self, data):
        return self._signals


class FakeExchange:
    exchange_type = "crypto"
    name = "fake"

    def __init__(self, config=None):
        self.config = config or {}
        self._tickers = {}

    def set_ticker(self, symbol, data):
        self._tickers[symbol] = data

    def get_ohlcv(self, symbol, timeframe="1d", limit=100):
        return []

    def get_ticker(self, symbol):
        return self._tickers.get(symbol, {"symbol": symbol, "last": 100.0})

    def get_orderbook(self, symbol, depth=20):
        return {"bids": [], "asks": []}

    def place_order(self, symbol, side, type, amount, price=None):
        return {"id": "fake-001"}

    def cancel_order(self, order_id):
        return True

    def get_balance(self):
        return {"USDT": {"free": 100000, "locked": 0}}

    def get_positions(self):
        return []


@pytest.fixture
def exchange():
    return FakeExchange()


@pytest.fixture
def strategy():
    return DummyStrategy()


@pytest.fixture
def risk_config():
    return RiskConfig(
        max_position_size=50_000,
        max_daily_loss=2_000,
        max_order_value=25_000,
        max_orders_per_minute=5,
        max_open_positions=5,
        capital=100_000,
    )


@pytest.fixture
def risk_guard(risk_config):
    return RiskGuard(risk_config)


@pytest.fixture
def live_engine(exchange, strategy):
    return LiveTradingEngine(
        exchange=exchange,
        strategy=strategy,
        tickers=["BTCUSDT", "ETHUSDT"],
        tick_interval=1.0,
    )


@pytest.fixture
def paper_engine(exchange, strategy):
    return PaperTradingEngine(
        exchange=exchange,
        strategy=strategy,
        tickers=["BTCUSDT"],
        initial_capital=100_000,
        tick_interval=1.0,
    )


# =====================================================================
# Risk Guard Tests (15 tests)
# =====================================================================

class TestRiskGuard:
    def test_approve_valid_order(self, risk_guard):
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        result = risk_guard.check_order(order, {"positions": {}})
        assert result.approved

    def test_reject_emergency_stop(self, risk_guard):
        risk_guard.emergency_stop()
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        result = risk_guard.check_order(order, {"positions": {}})
        assert not result.approved
        assert "Emergency stop" in result.reason

    def test_reset_emergency(self, risk_guard):
        risk_guard.emergency_stop()
        assert risk_guard.is_emergency_stopped
        risk_guard.reset_emergency()
        assert not risk_guard.is_emergency_stopped

    def test_reject_over_order_value(self, risk_guard):
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=100, limit_price=1000)
        result = risk_guard.check_order(order, {"positions": {}})
        assert not result.approved
        assert "Order value" in result.reason

    def test_reject_over_position_size(self, risk_guard):
        # Existing position of $40k + new order of $15k = $55k > $50k limit
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=15_000)
        portfolio = {"positions": {"BTCUSDT": {"quantity": 4, "avg_price": 10_000}}}
        result = risk_guard.check_order(order, portfolio)
        assert not result.approved
        assert "Position size" in result.reason

    def test_reject_max_open_positions(self, risk_guard):
        positions = {f"SYM{i}": {"quantity": 1, "avg_price": 100} for i in range(5)}
        order = Order(ticker="NEWSYM", side="buy", order_type="market", quantity=1, limit_price=100)
        result = risk_guard.check_order(order, {"positions": positions})
        assert not result.approved
        assert "open positions" in result.reason

    def test_allow_sell_with_max_positions(self, risk_guard):
        positions = {f"SYM{i}": {"quantity": 1, "avg_price": 100} for i in range(5)}
        order = Order(ticker="SYM0", side="sell", order_type="market", quantity=1, limit_price=100)
        result = risk_guard.check_order(order, {"positions": positions})
        assert result.approved

    def test_reject_disallowed_symbol(self, risk_config):
        risk_config.allowed_symbols = ["BTCUSDT", "ETHUSDT"]
        guard = RiskGuard(risk_config)
        order = Order(ticker="DOGEUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        result = guard.check_order(order, {"positions": {}})
        assert not result.approved
        assert "not in allowed" in result.reason

    def test_allow_allowed_symbol(self, risk_config):
        risk_config.allowed_symbols = ["BTCUSDT"]
        guard = RiskGuard(risk_config)
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        result = guard.check_order(order, {"positions": {}})
        assert result.approved

    def test_rate_limit(self, risk_config):
        risk_config.max_orders_per_minute = 3
        guard = RiskGuard(risk_config)
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        for _ in range(3):
            guard.check_order(order, {"positions": {}})
        result = guard.check_order(order, {"positions": {}})
        assert not result.approved
        assert "Rate limit" in result.reason

    def test_daily_loss_limit(self, risk_guard):
        risk_guard.update_pnl(-2_100)
        order = Order(ticker="BTCUSDT", side="buy", order_type="market", quantity=1, limit_price=100)
        result = risk_guard.check_order(order, {"positions": {}})
        assert not result.approved
        assert "Daily loss" in result.reason

    def test_daily_limit_resets(self, risk_guard):
        assert risk_guard.check_daily_limit()
        risk_guard._daily_date = "1999-01-01"
        risk_guard._daily_pnl = -99999
        result = risk_guard.check_daily_limit()
        assert result  # Reset to 0 for today

    def test_trading_hours_none(self, risk_config):
        risk_config.trading_hours = None
        guard = RiskGuard(risk_config)
        assert guard._check_trading_hours()

    def test_get_risk_status(self, risk_guard):
        status = risk_guard.get_risk_status()
        assert "daily_pnl" in status
        assert "emergency_stopped" in status
        assert status["emergency_stopped"] is False

    def test_portfolio_exposure_reject(self, risk_config):
        risk_config.max_portfolio_exposure = 0.5
        guard = RiskGuard(risk_config)
        positions = {"BTCUSDT": {"quantity": 100, "avg_price": 400}}
        order = Order(ticker="ETHUSDT", side="buy", order_type="market", quantity=100, limit_price=200)
        result = guard.check_order(order, {"positions": positions})
        assert not result.approved
        assert "exposure" in result.reason.lower()


# =====================================================================
# Live Trading Engine Tests (12 tests)
# =====================================================================

class TestLiveTradingEngine:
    def test_initial_state(self, live_engine):
        assert not live_engine.is_running
        assert live_engine._iteration == 0
        status = live_engine.get_status()
        assert status["is_running"] is False
        assert status["pnl"] == 0

    def test_get_status_keys(self, live_engine):
        status = live_engine.get_status()
        for key in ["is_running", "exchange", "tickers", "pnl", "positions", "open_orders", "total_trades"]:
            assert key in status

    def test_on_tick_no_signals(self, live_engine):
        results = run_async(live_engine.on_tick({"BTCUSDT": {"last": 67000}}))
        assert results == []

    def test_on_tick_with_signal(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 67000}
        ])
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, tickers=["BTCUSDT"])
        results = run_async(engine.on_tick({"BTCUSDT": {"last": 67000}}))
        assert len(results) == 1
        assert results[0].status == "filled"

    def test_on_tick_updates_position(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 2, "price": 50000}
        ])
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, tickers=["BTCUSDT"])
        run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))
        assert "BTCUSDT" in engine._positions
        assert engine._positions["BTCUSDT"]["quantity"] == 2

    def test_on_tick_sell_pnl(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 50000}
        ])
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, tickers=["BTCUSDT"])
        run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))

        strategy._signals = [
            {"ticker": "BTCUSDT", "side": "sell", "quantity": 1, "price": 55000}
        ]
        run_async(engine.on_tick({"BTCUSDT": {"last": 55000}}))
        assert engine._pnl == 5000

    def test_on_tick_with_risk_reject(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 100}
        ])
        risk = RiskGuard()
        risk.emergency_stop()
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, risk_manager=risk)
        results = run_async(engine.on_tick({"BTCUSDT": {"last": 100}}))
        assert results == []

    def test_on_tick_with_risk_approve(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 100}
        ])
        risk = RiskGuard()
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, risk_manager=risk)
        results = run_async(engine.on_tick({"BTCUSDT": {"last": 100}}))
        assert len(results) == 1

    def test_start_stop(self, live_engine):
        async def _test():
            async def stop_after():
                await asyncio.sleep(0.1)
                await live_engine.stop()

            task = asyncio.create_task(stop_after())
            try:
                await asyncio.wait_for(live_engine.start(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            await task
            assert not live_engine.is_running
        run_async(_test())

    def test_signal_to_order_invalid(self, live_engine):
        assert live_engine._signal_to_order({}) is None
        assert live_engine._signal_to_order({"ticker": "BTC", "side": "buy", "quantity": 0}) is None

    def test_extract_prices_dict(self, live_engine):
        prices = live_engine._extract_prices({"BTC": {"last": 67000}, "ETH": 3400})
        assert prices == {"BTC": 67000, "ETH": 3400}

    def test_extract_prices_numeric(self, live_engine):
        prices = live_engine._extract_prices({"BTC": 67000.5})
        assert prices["BTC"] == 67000.5


# =====================================================================
# Paper Trading Engine Tests (10 tests)
# =====================================================================

class TestPaperTradingEngine:
    def test_initial_state(self, paper_engine):
        assert paper_engine.virtual_balance == 100_000
        assert paper_engine.virtual_positions == {}
        assert paper_engine.trade_history == []

    def test_buy_updates_balance(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 50000}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000, slippage_bps=0, commission_rate=0)
        run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))
        assert engine.virtual_balance < 100_000
        assert "BTCUSDT" in engine.virtual_positions

    def test_sell_updates_balance(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 50000}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000, slippage_bps=0, commission_rate=0)
        run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))
        bal_after_buy = engine.virtual_balance

        strategy._signals = [{"ticker": "BTCUSDT", "side": "sell", "quantity": 1, "price": 55000}]
        run_async(engine.on_tick({"BTCUSDT": {"last": 55000}}))
        assert engine.virtual_balance > bal_after_buy
        assert "BTCUSDT" not in engine.virtual_positions

    def test_trade_history_recorded(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 100}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000)
        run_async(engine.on_tick({"BTCUSDT": {"last": 100}}))
        assert len(engine.trade_history) == 1
        assert engine.trade_history[0]["ticker"] == "BTCUSDT"

    def test_equity_curve_tracked(self, exchange):
        strategy = DummyStrategy([])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000)
        run_async(engine.on_tick({"BTCUSDT": {"last": 100}}))
        assert len(engine._equity_curve) == 1

    def test_get_performance_initial(self, paper_engine):
        perf = paper_engine.get_performance()
        assert perf["initial_capital"] == 100_000
        assert perf["total_pnl"] == 0
        assert perf["total_trades"] == 0

    def test_get_status_paper_mode(self, paper_engine):
        status = paper_engine.get_status()
        assert status["mode"] == "paper"
        assert "virtual_balance" in status
        assert "equity" in status

    def test_slippage_applied(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 10000}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000, slippage_bps=100, commission_rate=0)
        run_async(engine.on_tick({"BTCUSDT": {"last": 10000}}))
        # 100 bps = 1% slippage on buy → effective price 10100
        assert engine.virtual_balance == pytest.approx(100_000 - 10100, abs=1)

    def test_commission_applied(self, exchange):
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 10000}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000, slippage_bps=0, commission_rate=0.01)
        run_async(engine.on_tick({"BTCUSDT": {"last": 10000}}))
        # commission = 10000 * 1 * 0.01 = 100
        assert engine.virtual_balance == pytest.approx(100_000 - 10000 - 100, abs=1)

    def test_sharpe_empty(self, paper_engine):
        assert paper_engine._calculate_sharpe() == 0.0


# =====================================================================
# Dashboard Tests (5 tests)
# =====================================================================

class TestDashboard:
    def test_render_stopped(self, exchange, strategy):
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, tickers=["BTCUSDT"])
        dash = TradingDashboard(engine)
        output = dash.render()
        assert "STOPPED" in output
        assert "Dashboard" in output

    def test_render_paper_mode(self, exchange, strategy):
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000)
        dash = TradingDashboard(engine)
        output = dash.render()
        assert "PAPER" in output
        assert "100,000" in output

    def test_render_with_risk(self, exchange, strategy):
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, tickers=["BTCUSDT"])
        risk = RiskGuard()
        dash = TradingDashboard(engine, risk_guard=risk)
        output = dash.render()
        assert "Risk:" in output

    def test_render_emergency(self, exchange, strategy):
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy)
        risk = RiskGuard()
        risk.emergency_stop()
        dash = TradingDashboard(engine, risk_guard=risk)
        output = dash.render()
        assert "EMERGENCY" in output

    def test_format_duration(self):
        assert TradingDashboard._format_duration(30) == "30s"
        assert TradingDashboard._format_duration(120) == "2m"
        assert TradingDashboard._format_duration(3700) == "1h 1m"


# =====================================================================
# Integration Tests (3 tests)
# =====================================================================

class TestIntegration:
    def test_full_paper_trade_cycle(self, exchange):
        """Buy, hold, sell cycle with paper engine."""
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 1, "price": 50000}
        ])
        engine = PaperTradingEngine(
            exchange=exchange, strategy=strategy,
            initial_capital=100_000, slippage_bps=0, commission_rate=0,
        )
        run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))
        assert engine.virtual_balance == pytest.approx(50000, abs=1)

        strategy._signals = [{"ticker": "BTCUSDT", "side": "sell", "quantity": 1, "price": 60000}]
        run_async(engine.on_tick({"BTCUSDT": {"last": 60000}}))
        assert engine.virtual_balance == pytest.approx(110000, abs=1)
        assert engine.get_performance()["total_trades"] == 2

    def test_risk_integrated_with_engine(self, exchange):
        """Risk guard blocks oversized order in live engine."""
        config = RiskConfig(max_order_value=1000)
        risk = RiskGuard(config)
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 100, "price": 50000}
        ])
        engine = LiveTradingEngine(exchange=exchange, strategy=strategy, risk_manager=risk)
        results = run_async(engine.on_tick({"BTCUSDT": {"last": 50000}}))
        assert results == []  # blocked by risk

    def test_dashboard_after_trades(self, exchange):
        """Dashboard renders correctly after trades."""
        strategy = DummyStrategy([
            {"ticker": "BTCUSDT", "side": "buy", "quantity": 0.5, "price": 67000}
        ])
        engine = PaperTradingEngine(exchange=exchange, strategy=strategy, initial_capital=100_000)
        run_async(engine.on_tick({"BTCUSDT": {"last": 67000}}))

        risk = RiskGuard()
        dash = TradingDashboard(engine, risk_guard=risk)
        output = dash.render()
        assert "BTCUSDT" in output
        assert "PAPER" in output
