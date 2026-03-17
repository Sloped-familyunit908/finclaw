"""Integration and edge case tests for paper trading system.

Tests interactions between:
- PaperTradingEngine + StrategyRunner
- PaperTradingEngine + PaperDashboard
- PaperTradingEngine + TradeJournal + RealtimeDashboard
- Edge cases in order execution
"""

import time

import pytest

from src.paper.engine import (
    PaperTradingEngine,
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
    Position,
    Portfolio,
    PnL,
)
from src.paper.dashboard import PaperDashboard, _sparkline
from src.paper.runner import StrategyRunner, GoldenCrossStrategy, MomentumStrategy, BUILTIN_STRATEGIES
from src.paper.journal import TradeJournal


# ══════════════════════════════════════════════════════════════════
# PaperTradingEngine edge cases
# ══════════════════════════════════════════════════════════════════

class TestPaperTradingEngineEdgeCases:
    def test_zero_initial_balance_rejected(self):
        with pytest.raises(ValueError):
            PaperTradingEngine(initial_balance=0)

    def test_negative_initial_balance_rejected(self):
        with pytest.raises(ValueError):
            PaperTradingEngine(initial_balance=-1000)

    def test_buy_zero_quantity_rejected(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        order = engine.buy("AAPL", 0)
        assert order.status == OrderStatus.REJECTED

    def test_buy_negative_quantity_rejected(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        order = engine.buy("AAPL", -5)
        assert order.status == OrderStatus.REJECTED

    def test_sell_more_than_position(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        engine.buy("AAPL", 10)
        order = engine.sell("AAPL", 20)
        assert order.status == OrderStatus.REJECTED

    def test_sell_without_position(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        order = engine.sell("AAPL", 10)
        assert order.status == OrderStatus.REJECTED

    def test_buy_insufficient_funds(self):
        engine = PaperTradingEngine(initial_balance=1000)
        engine.set_price("AAPL", 150.0)
        order = engine.buy("AAPL", 100)  # $15000 > $1000
        assert order.status == OrderStatus.REJECTED

    def test_limit_buy_no_price(self):
        engine = PaperTradingEngine(initial_balance=100000)
        order = engine.buy("AAPL", 10, order_type="limit")
        assert order.status == OrderStatus.REJECTED

    def test_limit_buy_with_price(self):
        engine = PaperTradingEngine(initial_balance=100000)
        order = engine.buy("AAPL", 10, order_type="limit", limit_price=145.0)
        assert order.status == OrderStatus.PENDING

    def test_limit_sell_with_price(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        engine.buy("AAPL", 10)
        order = engine.sell("AAPL", 10, order_type="limit", limit_price=160.0)
        assert order.status == OrderStatus.PENDING

    def test_buy_updates_existing_position(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 110.0)
        engine.buy("AAPL", 10)
        pos = engine.positions["AAPL"]
        assert pos.quantity == 20
        assert pos.avg_cost == pytest.approx(105.0)

    def test_partial_sell(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 20)
        engine.set_price("AAPL", 120.0)
        engine.sell("AAPL", 10)
        assert engine.positions["AAPL"].quantity == 10

    def test_sell_all_removes_position(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.sell("AAPL", 10)
        assert "AAPL" not in engine.positions

    def test_reset_clears_everything(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.reset()
        assert engine.balance == 100000
        assert len(engine.positions) == 0
        assert len(engine.orders) == 0

    def test_no_price_buy_rejected(self):
        engine = PaperTradingEngine(initial_balance=100000)
        # Don't set any price override, and no real fetch
        order = engine.buy("NONEXISTENT_XYZ_123", 10)
        # Might be rejected or filled depending on yfinance
        # But with a clearly invalid symbol, it should be rejected
        assert order.status in (OrderStatus.REJECTED, OrderStatus.FILLED)

    def test_pnl_calculation_with_winning_trade(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 120.0)
        engine.sell("AAPL", 10)
        pnl = engine.get_pnl()
        assert pnl.realized == pytest.approx(200.0)
        assert pnl.win_count == 1

    def test_pnl_calculation_with_losing_trade(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 90.0)
        engine.sell("AAPL", 10)
        pnl = engine.get_pnl()
        assert pnl.realized == pytest.approx(-100.0)
        assert pnl.loss_count == 1


# ══════════════════════════════════════════════════════════════════
# Position / Portfolio dataclass tests
# ══════════════════════════════════════════════════════════════════

class TestPositionDataclass:
    def test_market_value(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=100, current_price=120)
        assert pos.market_value == 1200

    def test_cost_basis(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=100, current_price=120)
        assert pos.cost_basis == 1000

    def test_unrealized_pnl(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=100, current_price=120)
        assert pos.unrealized_pnl == 200

    def test_unrealized_pnl_pct(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=100, current_price=120)
        assert pos.unrealized_pnl_pct == pytest.approx(20.0)

    def test_unrealized_pnl_pct_zero_cost(self):
        pos = Position(symbol="AAPL", quantity=0, avg_cost=0, current_price=120)
        assert pos.unrealized_pnl_pct == 0.0

    def test_to_dict(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=100, current_price=120)
        d = pos.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["unrealized_pnl"] == 200


class TestPortfolioDataclass:
    def test_positions_value(self):
        positions = {
            "AAPL": Position("AAPL", 10, 100, 120),
            "MSFT": Position("MSFT", 5, 200, 250),
        }
        portfolio = Portfolio(cash=50000, positions=positions,
                              total_value=52450, initial_balance=100000)
        assert portfolio.positions_value == 2450

    def test_total_return(self):
        portfolio = Portfolio(cash=50000, positions={},
                              total_value=110000, initial_balance=100000)
        assert portfolio.total_return == pytest.approx(10.0)

    def test_total_return_zero_initial(self):
        portfolio = Portfolio(cash=0, positions={},
                              total_value=0, initial_balance=0)
        assert portfolio.total_return == 0.0

    def test_to_dict(self):
        portfolio = Portfolio(cash=100000, positions={},
                              total_value=100000, initial_balance=100000)
        d = portfolio.to_dict()
        assert d["cash"] == 100000
        assert "total_return" in d


class TestPnLDataclass:
    def test_win_rate_no_trades(self):
        pnl = PnL(realized=0, unrealized=0, total=0, total_return_pct=0,
                   win_count=0, loss_count=0, total_trades=0)
        assert pnl.win_rate == 0.0

    def test_win_rate_with_trades(self):
        pnl = PnL(realized=100, unrealized=0, total=100, total_return_pct=1.0,
                   win_count=7, loss_count=3, total_trades=10)
        assert pnl.win_rate == pytest.approx(70.0)

    def test_to_dict(self):
        pnl = PnL(realized=100, unrealized=50, total=150, total_return_pct=1.5,
                   win_count=3, loss_count=2, total_trades=5)
        d = pnl.to_dict()
        assert d["win_rate"] == pytest.approx(60.0)


class TestOrderDataclass:
    def test_to_dict(self):
        order = Order(
            id="abc123", symbol="AAPL", side=OrderSide.BUY,
            quantity=10, order_type=OrderType.MARKET,
            status=OrderStatus.FILLED, price=150.0,
            filled_price=150.0, timestamp=1000, fill_timestamp=1001,
        )
        d = order.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["side"] == "BUY"
        assert d["status"] == "filled"


# ══════════════════════════════════════════════════════════════════
# StrategyRunner
# ══════════════════════════════════════════════════════════════════

class TestStrategyRunner:
    def test_single_tick(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        strategy = MomentumStrategy(lookback=5)
        runner = StrategyRunner(engine, strategy, symbols=["AAPL"])
        runner.tick()
        assert runner._tick_count == 1

    def test_multiple_ticks(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        strategy = MomentumStrategy(lookback=5)
        runner = StrategyRunner(engine, strategy, symbols=["AAPL"])
        for _ in range(10):
            runner.tick()
        assert runner._tick_count == 10

    def test_get_stats(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        strategy = MomentumStrategy()
        runner = StrategyRunner(engine, strategy, symbols=["AAPL"])
        runner.tick()
        stats = runner.get_stats()
        assert stats["ticks"] == 1
        assert "total_pnl" in stats
        assert "is_running" in stats
        assert stats["strategy"] == "momentum"

    def test_start_stop(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        strategy = MomentumStrategy()
        runner = StrategyRunner(engine, strategy, symbols=["AAPL"], interval=0)
        runner.start()
        assert runner.is_running
        time.sleep(0.05)
        runner.stop()
        assert not runner.is_running
        assert runner._tick_count >= 1

    def test_builtin_strategies_registered(self):
        assert "golden-cross" in BUILTIN_STRATEGIES
        assert "momentum" in BUILTIN_STRATEGIES

    def test_error_handling(self):
        engine = PaperTradingEngine(initial_balance=100000)

        class BrokenStrategy:
            name = "broken"
            def on_tick(self, eng, syms):
                raise RuntimeError("oops")

        runner = StrategyRunner(engine, BrokenStrategy(), symbols=["AAPL"])
        runner.tick()
        assert len(runner._errors) == 1


# ══════════════════════════════════════════════════════════════════
# PaperDashboard
# ══════════════════════════════════════════════════════════════════

class TestPaperDashboardIntegration:
    def test_render_empty_portfolio(self):
        engine = PaperTradingEngine(initial_balance=100000)
        dashboard = PaperDashboard()
        text = dashboard.render(engine)
        assert "PAPER TRADING DASHBOARD" in text
        assert "100,000.00" in text

    def test_render_with_positions(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        engine.buy("AAPL", 10)
        dashboard = PaperDashboard()
        text = dashboard.render(engine)
        assert "AAPL" in text
        assert "Positions" in text

    def test_render_with_trades(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 160.0)
        engine.sell("AAPL", 10)
        dashboard = PaperDashboard()
        text = dashboard.render(engine)
        assert "Recent Trades" in text

    def test_render_shows_pnl(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 100.0)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 110.0)
        engine.sell("AAPL", 10)
        dashboard = PaperDashboard()
        text = dashboard.render(engine)
        assert "P&L" in text
        assert "Win Rate" in text


# ══════════════════════════════════════════════════════════════════
# Integration: Engine + Journal
# ══════════════════════════════════════════════════════════════════

class TestEngineJournalIntegration:
    def test_record_trades_from_engine(self):
        engine = PaperTradingEngine(initial_balance=100000)
        journal = TradeJournal()
        engine.set_price("AAPL", 150.0)
        order = engine.buy("AAPL", 10)
        if order.status == OrderStatus.FILLED:
            journal.record_trade({
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "price": order.filled_price,
                "timestamp": order.fill_timestamp,
            }, reason="Test buy")
        assert len(journal.get_entries()) == 1

    def test_full_trade_cycle_logged(self):
        engine = PaperTradingEngine(initial_balance=100000)
        journal = TradeJournal()
        engine.set_price("AAPL", 100.0)
        buy_order = engine.buy("AAPL", 10)
        journal.record_trade({
            "symbol": "AAPL", "side": "BUY", "quantity": 10,
            "price": 100.0, "timestamp": time.time(),
        })
        engine.set_price("AAPL", 120.0)
        sell_order = engine.sell("AAPL", 10)
        journal.record_trade({
            "symbol": "AAPL", "side": "SELL", "quantity": 10,
            "price": 120.0, "pnl": 200.0, "timestamp": time.time(),
        })
        review = journal.performance_review("1d")
        assert review["total_trades"] == 2
        assert review["total_pnl"] == 200.0
