"""Tests for FinClaw v3.6.0 — Event-Driven Backtester, Slippage, Commission, Order Router."""

import pytest
import pandas as pd
import numpy as np

from src.backtesting.event_engine import (
    EventDrivenBacktester, EventType, Event,
    MarketEvent, SignalEvent, OrderEvent, FillEvent,
    Portfolio, BacktestResult,
)
from src.backtesting.slippage import SlippageModel
from src.backtesting.commission import CommissionModel
from src.execution.order_router import OrderRouter, Order, OrderResult, OrderStatus, MockVenue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ohlcv(n=50, start_price=100.0, seed=42):
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    prices = start_price + np.cumsum(rng.randn(n) * 2)
    prices = np.maximum(prices, 1.0)
    df = pd.DataFrame({
        "open": prices + rng.uniform(-1, 1, n),
        "high": prices + abs(rng.randn(n)),
        "low": prices - abs(rng.randn(n)),
        "close": prices,
        "volume": rng.randint(1000, 100000, n).astype(float),
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))
    return df


def simple_ma_strategy(event: MarketEvent, portfolio: Portfolio):
    """Buy when we have no position, sell after 5 bars."""
    pos = portfolio.positions.get(event.symbol, 0)
    if pos == 0:
        return [SignalEvent(symbol=event.symbol, signal=1.0)]
    elif len(portfolio.trades) > 0 and len(portfolio.equity_curve) % 5 == 0:
        return [SignalEvent(symbol=event.symbol, signal=-1.0)]
    return None


def buy_and_hold_strategy(event: MarketEvent, portfolio: Portfolio):
    """Buy once and hold."""
    if not portfolio.positions.get(event.symbol, 0):
        return [SignalEvent(symbol=event.symbol, signal=1.0)]
    return None


# ===========================================================================
# EVENT ENGINE TESTS
# ===========================================================================

class TestEventTypes:
    def test_market_event_type(self):
        e = MarketEvent(symbol="AAPL", close=150.0)
        assert e.event_type == EventType.MARKET

    def test_signal_event_type(self):
        e = SignalEvent(symbol="AAPL", signal=1.0)
        assert e.event_type == EventType.SIGNAL

    def test_order_event_type(self):
        e = OrderEvent(symbol="AAPL", quantity=10, side="buy")
        assert e.event_type == EventType.ORDER
        assert len(e.order_id) == 8

    def test_fill_event_type(self):
        e = FillEvent(symbol="AAPL", quantity=10, fill_price=150.0)
        assert e.event_type == EventType.FILL


class TestPortfolio:
    def test_initial_state(self):
        p = Portfolio(initial_cash=50000)
        assert p.cash == 50000
        assert p.positions == {}

    def test_update_fill_buy(self):
        p = Portfolio(initial_cash=100000)
        fill = FillEvent(symbol="AAPL", quantity=10, fill_price=150.0, commission=1.0)
        p.update_fill(fill)
        assert p.positions["AAPL"] == 10
        assert p.cash == 100000 - 1500 - 1.0

    def test_update_fill_sell(self):
        p = Portfolio(initial_cash=100000)
        p.positions["AAPL"] = 10
        fill = FillEvent(symbol="AAPL", quantity=-10, fill_price=160.0, commission=1.0)
        p.update_fill(fill)
        assert p.positions["AAPL"] == 0
        assert p.cash == 100000 + 1600 - 1.0

    def test_mark_to_market(self):
        p = Portfolio(initial_cash=100000)
        p.positions["AAPL"] = 10
        value = p.mark_to_market({"AAPL": 150.0})
        assert value == 100000 + 1500
        assert len(p.equity_curve) == 1


class TestBacktestResult:
    def test_max_drawdown(self):
        curve = [100, 110, 105, 90, 95, 100]
        dd = BacktestResult.compute_max_drawdown(curve)
        assert abs(dd - (110 - 90) / 110) < 1e-10

    def test_max_drawdown_empty(self):
        assert BacktestResult.compute_max_drawdown([]) == 0.0

    def test_sharpe_ratio(self):
        curve = [100, 101, 102, 103, 104, 105]
        sr = BacktestResult.compute_sharpe(curve)
        assert sr > 0  # consistently positive returns

    def test_sharpe_single_point(self):
        assert BacktestResult.compute_sharpe([100]) == 0.0


class TestEventDrivenBacktester:
    def test_basic_run(self):
        data = make_ohlcv(30)
        bt = EventDrivenBacktester(initial_cash=100000)
        result = bt.run(data, buy_and_hold_strategy)
        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) == 30
        assert result.num_trades >= 1

    def test_run_with_slippage(self):
        data = make_ohlcv(30)
        bt = EventDrivenBacktester()
        result = bt.run(data, buy_and_hold_strategy,
                        slippage_fn=SlippageModel.fixed(10))
        assert result.final_equity > 0

    def test_run_with_commission(self):
        data = make_ohlcv(30)
        bt = EventDrivenBacktester()
        result = bt.run(data, buy_and_hold_strategy,
                        commission_fn=CommissionModel.percentage(0.001))
        assert result.final_equity > 0

    def test_run_strategy_with_trades(self):
        data = make_ohlcv(50)
        bt = EventDrivenBacktester()
        result = bt.run(data, simple_ma_strategy)
        assert result.num_trades >= 2  # at least buy and sell

    def test_register_handler(self):
        bt = EventDrivenBacktester()
        calls = []
        bt.register_handler(EventType.MARKET, lambda e: calls.append(e))
        bt.emit(MarketEvent(symbol="X"))
        bt._drain_queue()
        assert len(calls) == 1

    def test_emit_and_drain(self):
        bt = EventDrivenBacktester()
        bt.emit(Event(event_type=EventType.MARKET))
        assert len(bt.event_queue) == 1
        bt._drain_queue()
        assert len(bt.event_queue) == 0


# ===========================================================================
# SLIPPAGE MODEL TESTS
# ===========================================================================

class TestSlippageModel:
    def test_none(self):
        fn = SlippageModel.none()
        assert fn(100.0, 10) == 100.0

    def test_fixed_buy(self):
        fn = SlippageModel.fixed(bps=10)
        result = fn(100.0, 10)
        assert result == pytest.approx(100.1)  # 10bps = 0.1%

    def test_fixed_sell(self):
        fn = SlippageModel.fixed(bps=10)
        result = fn(100.0, -10)
        assert result == pytest.approx(99.9)

    def test_volume_based(self):
        fn = SlippageModel.volume_based(impact_coeff=0.1)
        result = fn(100.0, 100)
        assert result > 100.0  # positive qty → price goes up

    def test_spread_based(self):
        fn = SlippageModel.spread_based(spread_pct=0.05)
        result = fn(100.0, 10)
        assert result == pytest.approx(100.05)

    def test_composite(self):
        fn = SlippageModel.composite([
            SlippageModel.fixed(5),
            SlippageModel.spread_based(0.01),
        ])
        result = fn(100.0, 10)
        # Should be > simple fixed
        assert result > SlippageModel.fixed(5)(100.0, 10)

    def test_composite_empty(self):
        fn = SlippageModel.composite([])
        assert fn(100.0, 10) == 100.0


# ===========================================================================
# COMMISSION MODEL TESTS
# ===========================================================================

class TestCommissionModel:
    def test_zero(self):
        fn = CommissionModel.zero()
        assert fn(100.0, 10) == 0.0

    def test_fixed(self):
        fn = CommissionModel.fixed(5.0)
        assert fn(100.0, 10) == 5.0
        assert fn(200.0, 1) == 5.0

    def test_percentage(self):
        fn = CommissionModel.percentage(0.001)
        assert fn(100.0, 10) == pytest.approx(1.0)

    def test_per_share(self):
        fn = CommissionModel.per_share(rate=0.005, minimum=1.0)
        # 100 * 0.005 = 0.5, but minimum is 1.0
        assert fn(100.0, 100) == pytest.approx(1.0)

    def test_per_share_above_minimum(self):
        fn = CommissionModel.per_share(rate=0.01, minimum=1.0)
        assert fn(100.0, 200) == pytest.approx(2.0)  # 200 * 0.01 = 2.0

    def test_tiered(self):
        tiers = [(10000, 0.002), (50000, 0.0015), (float("inf"), 0.001)]
        fn = CommissionModel.tiered(tiers)
        assert fn(100.0, 10) == pytest.approx(1000 * 0.002)  # value=1000
        assert fn(100.0, 200) == pytest.approx(20000 * 0.0015)  # value=20000

    def test_interactive_brokers(self):
        fn = CommissionModel.interactive_brokers()
        # 100 shares * $0.0035 = $0.35 = minimum
        assert fn(50.0, 100) == pytest.approx(0.35)
        # 10000 shares * $0.0035 = $35
        comm = fn(50.0, 10000)
        assert comm == pytest.approx(35.0)

    def test_ib_max_cap(self):
        fn = CommissionModel.interactive_brokers()
        # 1 share at $1 → raw = $0.0035, min = $0.35, max = 1% of $1 = $0.01
        # min($0.0035, $0.01) = $0.0035, max($0.0035, $0.35) = $0.35
        # Actually max(min(0.0035, 0.01), 0.35) = max(0.0035, 0.35) = 0.35
        assert fn(1.0, 1) == pytest.approx(0.35)


# ===========================================================================
# ORDER ROUTER TESTS
# ===========================================================================

class TestOrderRouter:
    def test_submit_mock(self):
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10, side="buy")
        result = router.submit(order, market_price=150.0)
        assert result.status == OrderStatus.FILLED
        assert result.fill_price == 150.0

    def test_submit_unknown_venue(self):
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10, venue="nonexistent")
        result = router.submit(order)
        assert result.status == OrderStatus.REJECTED

    def test_cancel_pending(self):
        router = OrderRouter()
        # Mock venue auto-fills, so cancel returns False
        order = Order(symbol="AAPL", quantity=10)
        router.submit(order, market_price=100.0)
        assert router.cancel(order.order_id) is False  # already filled

    def test_get_status(self):
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=10)
        router.submit(order, market_price=100.0)
        assert router.get_status(order.order_id) == OrderStatus.FILLED

    def test_get_status_unknown(self):
        router = OrderRouter()
        assert router.get_status("nonexistent") is None

    def test_pending_orders(self):
        router = OrderRouter()
        # All mock orders are filled → no pending
        order = Order(symbol="AAPL", quantity=10)
        router.submit(order, market_price=100.0)
        assert len(router.pending_orders()) == 0

    def test_all_results(self):
        router = OrderRouter()
        o1 = Order(symbol="AAPL", quantity=10)
        o2 = Order(symbol="GOOG", quantity=5)
        router.submit(o1, market_price=150.0)
        router.submit(o2, market_price=2800.0)
        assert len(router.all_results()) == 2

    def test_register_custom_venue(self):
        class AlwaysRejectVenue:
            def execute(self, order, market_price=None):
                return OrderResult(order_id=order.order_id, status=OrderStatus.REJECTED,
                                   message="Rejected by policy")

        router = OrderRouter()
        router.register_venue("reject", AlwaysRejectVenue())
        order = Order(symbol="AAPL", quantity=10, venue="reject")
        result = router.submit(order)
        assert result.status == OrderStatus.REJECTED

    def test_mock_venue_default_price(self):
        venue = MockVenue()
        order = Order(symbol="AAPL", quantity=10)
        result = venue.execute(order)
        assert result.fill_price == 100.0  # default fallback


# ===========================================================================
# INTEGRATION TESTS
# ===========================================================================

class TestIntegration:
    def test_full_backtest_with_all_models(self):
        data = make_ohlcv(40)
        bt = EventDrivenBacktester(initial_cash=100000)
        result = bt.run(
            data,
            simple_ma_strategy,
            slippage_fn=SlippageModel.composite([
                SlippageModel.fixed(5),
                SlippageModel.spread_based(0.01),
            ]),
            commission_fn=CommissionModel.interactive_brokers(),
        )
        assert result.final_equity > 0
        assert len(result.equity_curve) == 40

    def test_backtest_result_fields(self):
        data = make_ohlcv(20)
        bt = EventDrivenBacktester()
        result = bt.run(data, buy_and_hold_strategy)
        assert hasattr(result, "total_return")
        assert hasattr(result, "max_drawdown")
        assert hasattr(result, "sharpe_ratio")
        assert result.max_drawdown >= 0

    def test_order_router_with_backtest(self):
        """Verify OrderRouter works standalone alongside backtester."""
        router = OrderRouter()
        order = Order(symbol="AAPL", quantity=100)
        result = router.submit(order, market_price=150.0)
        assert result.status == OrderStatus.FILLED

        # Now run a backtest
        data = make_ohlcv(10)
        bt = EventDrivenBacktester()
        bt_result = bt.run(data, buy_and_hold_strategy)
        assert bt_result.num_trades >= 1
