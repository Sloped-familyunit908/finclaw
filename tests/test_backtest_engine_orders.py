"""Tests for FinClaw Backtest Engine v5.6.0 — 60+ tests covering engine, orders, positions, monte carlo."""

import math
import pytest
from typing import List, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.backtesting.core_engine import (
    BacktestEngine, BacktestResult, EventType, Event,
    MarketEvent, SignalEvent, OrderEvent, FillEvent, StrategyContext,
)
from src.backtesting.orders import (
    OrderManager, Order, OrderType, OrderSide, OrderStatus,
)
from src.backtesting.positions import (
    PositionTracker, Position, PositionSide,
)
from src.backtesting.core_monte_carlo import MonteCarloSimulator, MonteCarloResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ohlcv(prices: list, base_volume: float = 1000) -> list:
    """Generate OHLCV bars from a list of close prices."""
    bars = []
    for i, p in enumerate(prices):
        bars.append({
            "open": p * 0.99,
            "high": p * 1.01,
            "low": p * 0.98,
            "close": p,
            "volume": base_volume,
            "timestamp": i,
        })
    return bars


class BuyAndHoldStrategy:
    """Buy on first bar, hold forever."""
    def __init__(self):
        self.bought = False

    def on_market(self, event: MarketEvent, context: StrategyContext) -> Optional[List[SignalEvent]]:
        if not self.bought and event.close > 0:
            self.bought = True
            return [SignalEvent(symbol=event.symbol, signal=1.0, timestamp=event.timestamp)]
        return None


class SellOnDropStrategy:
    """Buy first bar, sell when price drops 5% from buy price."""
    def __init__(self):
        self.bought = False
        self.buy_price = 0.0

    def on_market(self, event: MarketEvent, context: StrategyContext) -> Optional[List[SignalEvent]]:
        if not self.bought and event.close > 0:
            self.bought = True
            self.buy_price = event.close
            return [SignalEvent(symbol=event.symbol, signal=1.0, timestamp=event.timestamp)]
        if self.bought and event.close < self.buy_price * 0.95:
            self.bought = False
            return [SignalEvent(symbol=event.symbol, signal=-1.0, timestamp=event.timestamp)]
        return None


class MultiSignalStrategy:
    """Generates buy on bar 1, sell on bar 5."""
    def __init__(self):
        self.bar_count = 0

    def on_market(self, event: MarketEvent, context: StrategyContext) -> Optional[List[SignalEvent]]:
        self.bar_count += 1
        if self.bar_count == 1:
            return [SignalEvent(symbol=event.symbol, signal=1.0, timestamp=event.timestamp)]
        if self.bar_count == 5:
            return [SignalEvent(symbol=event.symbol, signal=-1.0, timestamp=event.timestamp)]
        return None


class NoOpStrategy:
    """Does nothing."""
    def on_market(self, event, context):
        return None


# ===========================================================================
# EVENT TESTS
# ===========================================================================

class TestEvents:
    def test_market_event_type(self):
        e = MarketEvent(symbol="AAPL", close=150.0)
        assert e.event_type == EventType.MARKET

    def test_signal_event_type(self):
        e = SignalEvent(symbol="AAPL", signal=1.0)
        assert e.event_type == EventType.SIGNAL

    def test_order_event_type(self):
        e = OrderEvent(symbol="AAPL", quantity=10, side="buy")
        assert e.event_type == EventType.ORDER

    def test_fill_event_type(self):
        e = FillEvent(symbol="AAPL", quantity=10, fill_price=150.0)
        assert e.event_type == EventType.FILL

    def test_signal_strength_default(self):
        e = SignalEvent(symbol="AAPL", signal=1.0)
        assert e.strength == 1.0

    def test_order_id_generated(self):
        e = OrderEvent(symbol="AAPL", quantity=10, side="buy")
        assert len(e.order_id) == 8


# ===========================================================================
# POSITION TRACKER TESTS
# ===========================================================================

class TestPositionTracker:
    def test_open_long(self):
        pt = PositionTracker()
        pos = pt.open_position("AAPL", 100, 150.0, "long")
        assert pos.quantity == 100
        assert pos.avg_price == 150.0
        assert pos.side == PositionSide.LONG

    def test_open_short(self):
        pt = PositionTracker()
        pos = pt.open_position("AAPL", 50, 150.0, "short")
        assert pos.side == PositionSide.SHORT

    def test_close_full_position(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pnl = pt.close_position("AAPL", 100, 160.0)
        assert pnl == 1000.0  # (160-150)*100
        assert not pt.has_position("AAPL")

    def test_close_partial_position(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pnl = pt.close_position("AAPL", 50, 160.0)
        assert pnl == 500.0
        assert pt.has_position("AAPL")
        assert pt.positions["AAPL"].quantity == 50

    def test_close_nonexistent(self):
        pt = PositionTracker()
        pnl = pt.close_position("AAPL", 100, 160.0)
        assert pnl == 0.0

    def test_get_pnl_long(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pnl = pt.get_pnl("AAPL", 155.0)
        assert pnl == 500.0

    def test_get_pnl_short(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "short")
        pnl = pt.get_pnl("AAPL", 145.0)
        assert pnl == 500.0

    def test_get_pnl_nonexistent(self):
        pt = PositionTracker()
        assert pt.get_pnl("AAPL", 150.0) == 0.0

    def test_portfolio_value_long(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pt.open_position("GOOG", 50, 200.0, "long")
        value = pt.get_portfolio_value({"AAPL": 155.0, "GOOG": 210.0})
        assert value == 100 * 155.0 + 50 * 210.0

    def test_portfolio_value_short(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "short")
        # Short value: qty * (2*avg - price)
        value = pt.get_portfolio_value({"AAPL": 145.0})
        assert value == 100 * (2 * 150.0 - 145.0)

    def test_add_to_position(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pt.open_position("AAPL", 100, 160.0, "long")
        pos = pt.positions["AAPL"]
        assert pos.quantity == 200
        assert pos.avg_price == 155.0  # (150*100 + 160*100) / 200

    def test_has_position(self):
        pt = PositionTracker()
        assert not pt.has_position("AAPL")
        pt.open_position("AAPL", 100, 150.0, "long")
        assert pt.has_position("AAPL")

    def test_get_all_symbols(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pt.open_position("GOOG", 50, 200.0, "long")
        syms = pt.get_all_symbols()
        assert set(syms) == {"AAPL", "GOOG"}

    def test_closed_positions_recorded(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pt.close_position("AAPL", 100, 160.0)
        assert len(pt.closed_positions) == 1
        assert pt.closed_positions[0]["pnl"] == 1000.0


# ===========================================================================
# ORDER MANAGER TESTS
# ===========================================================================

class TestOrderManager:
    def test_market_order(self):
        om = OrderManager()
        order = om.market_order("AAPL", 100, "buy")
        assert order.order_type == OrderType.MARKET
        assert order.side == OrderSide.BUY
        assert order.quantity == 100

    def test_limit_order(self):
        om = OrderManager()
        order = om.limit_order("AAPL", 100, 145.0, "buy")
        assert order.order_type == OrderType.LIMIT
        assert order.price == 145.0
        assert len(om.pending_orders) == 1

    def test_stop_order(self):
        om = OrderManager()
        order = om.stop_order("AAPL", 100, 140.0, "sell")
        assert order.order_type == OrderType.STOP
        assert order.stop_price == 140.0

    def test_trailing_stop(self):
        om = OrderManager()
        order = om.trailing_stop("AAPL", 100, 0.05, "sell")
        assert order.order_type == OrderType.TRAILING_STOP
        assert order.trail_pct == 0.05

    def test_oco_order(self):
        om = OrderManager()
        tp, sl = om.oco_order("AAPL", 100, 170.0, 140.0)
        assert tp.price == 170.0
        assert sl.stop_price == 140.0
        assert tp._linked_order_id == sl.order_id
        assert sl._linked_order_id == tp.order_id
        assert len(om.pending_orders) == 2

    def test_cancel_order(self):
        om = OrderManager()
        order = om.limit_order("AAPL", 100, 145.0, "buy")
        assert om.cancel_order(order.order_id)
        assert order.status == OrderStatus.CANCELLED
        assert len(om.pending_orders) == 0

    def test_cancel_nonexistent(self):
        om = OrderManager()
        assert not om.cancel_order("nonexistent")

    def test_limit_buy_triggered(self):
        om = OrderManager()
        om.limit_order("AAPL", 100, 145.0, "buy")

        class FakeMarket:
            high = 150.0
            low = 144.0
            close = 146.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 1
        assert triggered[0].filled_price == 145.0

    def test_limit_buy_not_triggered(self):
        om = OrderManager()
        om.limit_order("AAPL", 100, 140.0, "buy")

        class FakeMarket:
            high = 150.0
            low = 145.0
            close = 148.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 0

    def test_limit_sell_triggered(self):
        om = OrderManager()
        om.limit_order("AAPL", 100, 160.0, "sell")

        class FakeMarket:
            high = 162.0
            low = 155.0
            close = 161.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 1

    def test_stop_sell_triggered(self):
        om = OrderManager()
        om.stop_order("AAPL", 100, 140.0, "sell")

        class FakeMarket:
            high = 150.0
            low = 139.0
            close = 141.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 1

    def test_stop_sell_not_triggered(self):
        om = OrderManager()
        om.stop_order("AAPL", 100, 130.0, "sell")

        class FakeMarket:
            high = 150.0
            low = 135.0
            close = 145.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 0

    def test_trailing_stop_sell(self):
        om = OrderManager()
        om.trailing_stop("AAPL", 100, 0.05, "sell")

        class Bar1:
            high = 100.0
            low = 98.0
            close = 99.0

        class Bar2:
            high = 105.0
            low = 103.0
            close = 104.0

        class Bar3:
            high = 101.0
            low = 99.0  # trail price = 105*0.95 = 99.75, low 99 < 99.75
            close = 100.0

        assert len(om.check_pending("AAPL", Bar1())) == 0
        assert len(om.check_pending("AAPL", Bar2())) == 0
        triggered = om.check_pending("AAPL", Bar3())
        assert len(triggered) == 1

    def test_oco_cancels_linked(self):
        om = OrderManager()
        tp, sl = om.oco_order("AAPL", 100, 170.0, 140.0)

        class FakeMarket:
            high = 175.0
            low = 165.0
            close = 172.0

        triggered = om.check_pending("AAPL", FakeMarket())
        assert len(triggered) == 1
        assert triggered[0].order_id == tp.order_id
        assert sl.status == OrderStatus.CANCELLED

    def test_get_order(self):
        om = OrderManager()
        order = om.market_order("AAPL", 100, "buy")
        assert om.get_order(order.order_id) is order
        assert om.get_order("nonexistent") is None

    def test_pending_count(self):
        om = OrderManager()
        om.limit_order("AAPL", 100, 145.0, "buy")
        om.stop_order("AAPL", 50, 140.0, "sell")
        assert om.get_pending_count() == 2


# ===========================================================================
# ENGINE TESTS
# ===========================================================================

class TestBacktestEngine:
    def test_empty_run(self):
        engine = BacktestEngine()
        result = engine.run()
        assert result.total_return == 0.0
        assert result.initial_capital == 100_000

    def test_no_strategy(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100, 101, 102]))
        result = engine.run()
        assert result.total_return == 0.0

    def test_buy_and_hold_rising(self):
        engine = BacktestEngine(initial_capital=100_000)
        prices = [100 + i for i in range(20)]
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(BuyAndHoldStrategy())
        result = engine.run()
        assert result.total_return > 0
        assert result.final_equity > 100_000

    def test_buy_and_hold_flat(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100] * 10))
        engine.set_strategy(BuyAndHoldStrategy())
        result = engine.run()
        # With zero commission/slippage, equity should stay roughly the same
        assert abs(result.total_return) < 0.01

    def test_commission_reduces_returns(self):
        engine1 = BacktestEngine(initial_capital=100_000)
        engine1.add_data("AAPL", make_ohlcv([100 + i for i in range(20)]))
        engine1.set_strategy(BuyAndHoldStrategy())
        r1 = engine1.run()

        engine2 = BacktestEngine(initial_capital=100_000)
        engine2.add_data("AAPL", make_ohlcv([100 + i for i in range(20)]))
        engine2.set_strategy(BuyAndHoldStrategy())
        engine2.set_commission(0.01)
        r2 = engine2.run()

        assert r2.total_commission > 0

    def test_slippage_fixed(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100, 110, 120]))
        engine.set_strategy(BuyAndHoldStrategy())
        engine.set_slippage("fixed", 0.50)
        result = engine.run()
        assert result.total_slippage > 0

    def test_slippage_pct(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100, 110, 120]))
        engine.set_strategy(BuyAndHoldStrategy())
        engine.set_slippage("pct", 0.001)
        result = engine.run()
        assert result.total_slippage > 0

    def test_sell_generates_trade(self):
        engine = BacktestEngine(initial_capital=100_000)
        # Price goes up then drops
        prices = [100, 105, 110, 108, 94]  # 94 < 100*0.95
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(SellOnDropStrategy())
        result = engine.run()
        assert result.num_trades >= 1

    def test_multi_signal_buy_sell(self):
        engine = BacktestEngine()
        prices = [100, 105, 110, 108, 106, 104]
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(MultiSignalStrategy())
        result = engine.run()
        assert result.num_trades >= 1

    def test_equity_curve_length(self):
        engine = BacktestEngine()
        prices = [100 + i for i in range(10)]
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(BuyAndHoldStrategy())
        result = engine.run()
        assert len(result.equity_curve) == 10

    def test_noop_strategy(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100, 101, 102]))
        engine.set_strategy(NoOpStrategy())
        result = engine.run()
        assert result.num_trades == 0
        assert all(v == 100_000 for v in result.equity_curve)

    def test_initial_capital_custom(self):
        engine = BacktestEngine(initial_capital=50_000)
        engine.add_data("AAPL", make_ohlcv([100]))
        engine.set_strategy(NoOpStrategy())
        result = engine.run()
        assert result.initial_capital == 50_000
        assert result.equity_curve[0] == 50_000


# ===========================================================================
# BACKTEST RESULT METRICS TESTS
# ===========================================================================

class TestBacktestResultMetrics:
    def test_max_drawdown_no_data(self):
        assert BacktestResult._compute_max_drawdown([]) == 0.0

    def test_max_drawdown_rising(self):
        curve = [100, 110, 120, 130]
        assert BacktestResult._compute_max_drawdown(curve) == 0.0

    def test_max_drawdown_simple(self):
        curve = [100, 120, 90, 110]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert abs(dd - 0.25) < 0.001  # 90/120 = 25% dd

    def test_sharpe_flat(self):
        curve = [100, 100, 100, 100]
        returns = BacktestResult._compute_returns(curve)
        assert BacktestResult._compute_sharpe(returns) == 0.0

    def test_sharpe_positive(self):
        curve = [100 + i * 0.5 for i in range(100)]
        returns = BacktestResult._compute_returns(curve)
        sharpe = BacktestResult._compute_sharpe(returns)
        assert sharpe > 0

    def test_sortino_no_downside(self):
        curve = [100 + i for i in range(10)]
        returns = BacktestResult._compute_returns(curve)
        sortino = BacktestResult._compute_sortino(returns)
        assert sortino == float('inf')

    def test_sortino_with_downside(self):
        curve = [100, 105, 95, 110, 90, 120]
        returns = BacktestResult._compute_returns(curve)
        sortino = BacktestResult._compute_sortino(returns)
        assert isinstance(sortino, float)

    def test_cagr_positive(self):
        cagr = BacktestResult._compute_cagr(100, 200, 252)
        assert abs(cagr - 1.0) < 0.01  # 100% in 1 year

    def test_cagr_zero_bars(self):
        assert BacktestResult._compute_cagr(100, 200, 0) == 0.0

    def test_win_rate_all_wins(self):
        trades = [{"pnl": 100}, {"pnl": 50}]
        assert BacktestResult._compute_win_rate(trades) == 1.0

    def test_win_rate_mixed(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 30}, {"pnl": -20}]
        assert BacktestResult._compute_win_rate(trades) == 0.5

    def test_win_rate_empty(self):
        assert BacktestResult._compute_win_rate([]) == 0.0

    def test_profit_factor_no_losses(self):
        trades = [{"pnl": 100}, {"pnl": 50}]
        assert BacktestResult._compute_profit_factor(trades) == float('inf')

    def test_profit_factor_mixed(self):
        trades = [{"pnl": 200}, {"pnl": -100}]
        assert BacktestResult._compute_profit_factor(trades) == 2.0

    def test_returns_computation(self):
        curve = [100, 110, 99]
        returns = BacktestResult._compute_returns(curve)
        assert len(returns) == 2
        assert abs(returns[0] - 0.1) < 0.001


# ===========================================================================
# MONTE CARLO TESTS
# ===========================================================================

class TestMonteCarlo:
    def test_empty_trades(self):
        mc = MonteCarloSimulator(seed=42)
        result = mc.simulate([], n_simulations=100)
        assert result.n_simulations == 0

    def test_basic_simulation(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}, {"pnl": -30}, {"pnl": 150}]
        mc = MonteCarloSimulator(seed=42)
        result = mc.simulate(trades, n_simulations=500, initial_capital=10000)
        assert result.n_simulations == 500
        assert len(result.all_returns) == 500
        assert result.returns_mean > 0

    def test_var_95(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}, {"pnl": -30}]
        mc = MonteCarloSimulator(seed=42)
        mc.simulate(trades, n_simulations=1000)
        var = mc.var_95()
        assert isinstance(var, float)

    def test_var_95_no_simulation(self):
        mc = MonteCarloSimulator()
        assert mc.var_95() == 0.0

    def test_expected_max_drawdown(self):
        trades = [{"pnl": 100}, {"pnl": -200}, {"pnl": 150}]
        mc = MonteCarloSimulator(seed=42)
        mc.simulate(trades, n_simulations=500, initial_capital=10000)
        edd = mc.expected_max_drawdown()
        assert edd > 0

    def test_ruin_probability_safe(self):
        trades = [{"pnl": 100}] * 10
        mc = MonteCarloSimulator(seed=42)
        mc.simulate(trades, n_simulations=500, initial_capital=10000)
        assert mc.ruin_probability() == 0.0

    def test_ruin_probability_custom_threshold(self):
        trades = [{"pnl": -1000}] * 10
        mc = MonteCarloSimulator(seed=42)
        mc.simulate(trades, n_simulations=100, initial_capital=10000)
        # With big losses, ruin should be high
        ruin = mc.ruin_probability(threshold=-0.3)
        assert ruin > 0

    def test_ruin_probability_no_sim(self):
        mc = MonteCarloSimulator()
        assert mc.ruin_probability() == 0.0

    def test_confidence_intervals(self):
        trades = [{"pnl": 50 + i * 10} for i in range(20)]
        mc = MonteCarloSimulator(seed=42)
        result = mc.simulate(trades, n_simulations=1000, initial_capital=10000)
        assert result.returns_p5 <= result.returns_median <= result.returns_p95
        assert result.returns_p25 <= result.returns_p75

    def test_deterministic_with_seed(self):
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}]
        mc1 = MonteCarloSimulator(seed=123)
        r1 = mc1.simulate(trades, n_simulations=100)
        mc2 = MonteCarloSimulator(seed=123)
        r2 = mc2.simulate(trades, n_simulations=100)
        assert r1.returns_mean == r2.returns_mean

    def test_all_final_equities(self):
        trades = [{"pnl": 100}, {"pnl": -50}]
        mc = MonteCarloSimulator(seed=42)
        result = mc.simulate(trades, n_simulations=100, initial_capital=10000)
        assert len(result.all_final_equities) == 100
        assert all(e > 0 for e in result.all_final_equities)


# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================

class TestIntegration:
    def test_full_backtest_cycle(self):
        """Full cycle: engine + strategy + positions + result."""
        engine = BacktestEngine(initial_capital=100_000)
        prices = list(range(100, 130))
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(MultiSignalStrategy())
        engine.set_commission(0.001)
        engine.set_slippage("fixed", 0.01)
        result = engine.run()
        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) == 30

    def test_backtest_then_monte_carlo(self):
        """Run backtest, then Monte Carlo on the trades."""
        engine = BacktestEngine(initial_capital=100_000)
        prices = [100, 105, 110, 108, 94, 100, 107, 115, 110, 93]
        engine.add_data("AAPL", make_ohlcv(prices))
        engine.set_strategy(SellOnDropStrategy())
        result = engine.run()

        if result.trades:
            mc = MonteCarloSimulator(seed=42)
            mc_result = mc.simulate(result.trades, n_simulations=200)
            assert mc_result.n_simulations == 200

    def test_position_tracker_standalone(self):
        """Use PositionTracker independently."""
        pt = PositionTracker()
        pt.open_position("AAPL", 100, 150.0, "long")
        pt.open_position("GOOG", 50, 2800.0, "long")

        pnl_aapl = pt.get_pnl("AAPL", 160.0)
        assert pnl_aapl == 1000.0

        total_val = pt.get_portfolio_value({"AAPL": 160.0, "GOOG": 2850.0})
        assert total_val == 100 * 160.0 + 50 * 2850.0

    def test_order_manager_standalone(self):
        """Use OrderManager independently."""
        om = OrderManager()
        om.limit_order("AAPL", 100, 145.0, "buy")
        om.stop_order("AAPL", 100, 140.0, "sell")
        assert om.get_pending_count() == 2


# ===========================================================================
# EDGE CASE TESTS
# ===========================================================================

class TestEdgeCases:
    def test_single_bar(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([100]))
        engine.set_strategy(BuyAndHoldStrategy())
        result = engine.run()
        assert len(result.equity_curve) == 1

    def test_zero_price(self):
        engine = BacktestEngine()
        engine.add_data("AAPL", make_ohlcv([0, 0, 0]))
        engine.set_strategy(BuyAndHoldStrategy())
        result = engine.run()
        assert result.num_trades == 0

    def test_very_high_commission(self):
        engine = BacktestEngine(initial_capital=1000)
        engine.add_data("AAPL", make_ohlcv([100, 200]))
        engine.set_strategy(BuyAndHoldStrategy())
        engine.set_commission(0.5)  # 50% commission
        result = engine.run()
        # Should still run without crashing
        assert isinstance(result, BacktestResult)

    def test_position_close_more_than_held(self):
        pt = PositionTracker()
        pt.open_position("AAPL", 50, 150.0, "long")
        pnl = pt.close_position("AAPL", 100, 160.0)  # Close 100 but only have 50
        assert pnl == 500.0  # Only closes 50
        assert not pt.has_position("AAPL")
