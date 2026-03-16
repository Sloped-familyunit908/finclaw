"""
Tests for Paper Trading Simulator v5.14.0
==========================================
45+ tests covering engine, dashboard, runner, journal, and CLI.
"""

import csv
import io
import json
import os
import time
import tempfile
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.paper.engine import (
    PaperTradingEngine, Order, OrderSide, OrderType, OrderStatus,
    Position, Portfolio, PnL,
)
from src.paper.dashboard import PaperDashboard, _sparkline
from src.paper.runner import StrategyRunner, GoldenCrossStrategy, MomentumStrategy, BUILTIN_STRATEGIES
from src.paper.journal import TradeJournal


# ──────────────────────────────────────────────────────────
# Engine Tests
# ──────────────────────────────────────────────────────────

class TestPaperTradingEngine:
    def _engine(self, balance=100000):
        e = PaperTradingEngine(initial_balance=balance)
        e.set_price("AAPL", 150.0)
        e.set_price("MSFT", 400.0)
        e.set_price("GOOGL", 170.0)
        return e

    def test_init_defaults(self):
        e = PaperTradingEngine()
        assert e.balance == 100000
        assert e.exchange == "yahoo"
        assert e.positions == {}
        assert e.orders == []
        assert e.trade_log == []

    def test_init_custom(self):
        e = PaperTradingEngine(initial_balance=50000, exchange="binance")
        assert e.balance == 50000
        assert e.exchange == "binance"

    def test_init_invalid_balance(self):
        with pytest.raises(ValueError):
            PaperTradingEngine(initial_balance=0)
        with pytest.raises(ValueError):
            PaperTradingEngine(initial_balance=-100)

    def test_buy_market_order(self):
        e = self._engine()
        order = e.buy("AAPL", 10)
        assert order.status == OrderStatus.FILLED
        assert order.side == OrderSide.BUY
        assert order.filled_price == 150.0
        assert order.quantity == 10
        assert e.balance == 100000 - 150 * 10
        assert "AAPL" in e.positions
        assert e.positions["AAPL"].quantity == 10

    def test_buy_insufficient_funds(self):
        e = self._engine(balance=1000)
        order = e.buy("MSFT", 10)  # 400 * 10 = 4000 > 1000
        assert order.status == OrderStatus.REJECTED

    def test_buy_zero_quantity(self):
        e = self._engine()
        order = e.buy("AAPL", 0)
        assert order.status == OrderStatus.REJECTED

    def test_buy_negative_quantity(self):
        e = self._engine()
        order = e.buy("AAPL", -5)
        assert order.status == OrderStatus.REJECTED

    def test_buy_unknown_symbol(self):
        e = PaperTradingEngine()
        # No price override, no real fetch in test
        e._price_overrides.clear()
        order = e.buy("NONEXIST_XYZ_999", 1)
        # Should be rejected since price can't be fetched (or may try yfinance)
        # We just check it returns an Order
        assert isinstance(order, Order)

    def test_buy_adds_to_position(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.set_price("AAPL", 160.0)
        e.buy("AAPL", 5)
        pos = e.positions["AAPL"]
        assert pos.quantity == 15
        expected_avg = (150 * 10 + 160 * 5) / 15
        assert abs(pos.avg_cost - expected_avg) < 0.01

    def test_sell_market_order(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.set_price("AAPL", 170.0)
        order = e.sell("AAPL", 10)
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == 170.0
        assert "AAPL" not in e.positions
        # Balance = (100000 - 1500) + 1700 = 100200
        assert abs(e.balance - 100200) < 0.01

    def test_sell_partial(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.sell("AAPL", 3)
        assert e.positions["AAPL"].quantity == 7

    def test_sell_insufficient_position(self):
        e = self._engine()
        order = e.sell("AAPL", 10)
        assert order.status == OrderStatus.REJECTED

    def test_sell_more_than_held(self):
        e = self._engine()
        e.buy("AAPL", 5)
        order = e.sell("AAPL", 10)
        assert order.status == OrderStatus.REJECTED

    def test_sell_zero_quantity(self):
        e = self._engine()
        e.buy("AAPL", 10)
        order = e.sell("AAPL", 0)
        assert order.status == OrderStatus.REJECTED

    def test_buy_limit_order(self):
        e = self._engine()
        order = e.buy("AAPL", 10, order_type="limit", limit_price=145.0)
        assert order.status == OrderStatus.PENDING
        assert order.limit_price == 145.0
        assert order.order_type == OrderType.LIMIT

    def test_sell_limit_order(self):
        e = self._engine()
        e.buy("AAPL", 10)
        order = e.sell("AAPL", 5, order_type="limit", limit_price=160.0)
        assert order.status == OrderStatus.PENDING

    def test_limit_order_no_price_rejected(self):
        e = self._engine()
        order = e.buy("AAPL", 10, order_type="limit")
        assert order.status == OrderStatus.REJECTED

    def test_get_portfolio(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.buy("MSFT", 5)
        portfolio = e.get_portfolio()
        assert isinstance(portfolio, Portfolio)
        assert portfolio.cash == 100000 - 150 * 10 - 400 * 5
        assert len(portfolio.positions) == 2
        assert portfolio.total_value == portfolio.cash + portfolio.positions_value

    def test_portfolio_total_return(self):
        e = self._engine(balance=10000)
        e.set_price("AAPL", 100.0)
        e.buy("AAPL", 10)  # spend 1000
        e.set_price("AAPL", 110.0)
        p = e.get_portfolio()
        # cash=9000, positions=1100, total=10100
        assert abs(p.total_return - 1.0) < 0.1

    def test_get_pnl_no_trades(self):
        e = self._engine()
        pnl = e.get_pnl()
        assert pnl.realized == 0
        assert pnl.unrealized == 0
        assert pnl.total == 0
        assert pnl.total_trades == 0
        assert pnl.win_rate == 0

    def test_get_pnl_with_trades(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.set_price("AAPL", 170.0)
        e.sell("AAPL", 10)
        pnl = e.get_pnl()
        assert pnl.realized == 200.0  # (170-150)*10
        assert pnl.total_trades == 1
        assert pnl.win_count == 1
        assert pnl.loss_count == 0
        assert pnl.win_rate == 100.0

    def test_get_pnl_losing_trade(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.set_price("AAPL", 140.0)
        e.sell("AAPL", 10)
        pnl = e.get_pnl()
        assert pnl.realized == -100.0
        assert pnl.loss_count == 1

    def test_get_trade_history(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.sell("AAPL", 5)
        history = e.get_trade_history()
        assert len(history) == 2
        assert history[0]["side"] == "BUY"
        assert history[1]["side"] == "SELL"

    def test_equity_history(self):
        e = self._engine()
        assert len(e.get_equity_history()) == 0
        e.buy("AAPL", 10)
        assert len(e.get_equity_history()) == 1

    def test_reset(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.reset()
        assert e.balance == e.initial_balance
        assert e.positions == {}
        assert e.orders == []
        assert e.trade_log == []
        assert e._realized_pnl == 0

    def test_set_and_clear_price_overrides(self):
        e = PaperTradingEngine()
        e.set_price("TEST", 42.0)
        assert e._get_price("TEST") == 42.0
        e.clear_price_overrides()
        assert "TEST" not in e._price_overrides

    def test_order_to_dict(self):
        e = self._engine()
        order = e.buy("AAPL", 1)
        d = order.to_dict()
        assert d["symbol"] == "AAPL"
        assert d["side"] == "BUY"
        assert d["status"] == "filled"

    def test_position_properties(self):
        pos = Position(symbol="AAPL", quantity=10, avg_cost=150.0, current_price=170.0)
        assert pos.market_value == 1700.0
        assert pos.cost_basis == 1500.0
        assert pos.unrealized_pnl == 200.0
        assert abs(pos.unrealized_pnl_pct - 13.33) < 0.1

    def test_position_zero_cost(self):
        pos = Position(symbol="X", quantity=0, avg_cost=0, current_price=100)
        assert pos.unrealized_pnl_pct == 0.0

    def test_pnl_to_dict(self):
        pnl = PnL(realized=100, unrealized=50, total=150, total_return_pct=1.5,
                   win_count=3, loss_count=1, total_trades=4)
        d = pnl.to_dict()
        assert d["win_rate"] == 75.0

    def test_portfolio_to_dict(self):
        e = self._engine()
        e.buy("AAPL", 10)
        p = e.get_portfolio()
        d = p.to_dict()
        assert "cash" in d
        assert "positions" in d
        assert "total_value" in d

    def test_multiple_symbols(self):
        e = self._engine()
        e.buy("AAPL", 10)
        e.buy("MSFT", 5)
        e.buy("GOOGL", 20)
        assert len(e.positions) == 3
        e.sell("MSFT", 5)
        assert len(e.positions) == 2


# ──────────────────────────────────────────────────────────
# Dashboard Tests
# ──────────────────────────────────────────────────────────

class TestPaperDashboard:
    def test_render_empty(self):
        e = PaperTradingEngine()
        d = PaperDashboard()
        output = d.render(e)
        assert "PAPER TRADING DASHBOARD" in output
        assert "Cash" in output

    def test_render_with_positions(self):
        e = PaperTradingEngine()
        e.set_price("AAPL", 150.0)
        e.buy("AAPL", 10)
        d = PaperDashboard()
        output = d.render(e)
        assert "AAPL" in output
        assert "Positions" in output

    def test_render_with_trades(self):
        e = PaperTradingEngine()
        e.set_price("AAPL", 150.0)
        e.buy("AAPL", 10)
        e.set_price("AAPL", 160.0)
        e.sell("AAPL", 5)
        d = PaperDashboard()
        output = d.render(e)
        assert "Recent Trades" in output

    def test_sparkline_empty(self):
        assert _sparkline([]) == ""

    def test_sparkline_values(self):
        result = _sparkline([1, 2, 3, 4, 5])
        assert len(result) == 5
        assert result[0] != result[-1]

    def test_sparkline_constant(self):
        result = _sparkline([5, 5, 5, 5])
        assert len(result) == 4

    def test_sparkline_long(self):
        result = _sparkline(list(range(100)), width=20)
        assert len(result) == 20


# ──────────────────────────────────────────────────────────
# Runner Tests
# ──────────────────────────────────────────────────────────

class TestStrategyRunner:
    def test_builtin_strategies(self):
        assert "golden-cross" in BUILTIN_STRATEGIES
        assert "momentum" in BUILTIN_STRATEGIES

    def test_tick(self):
        e = PaperTradingEngine()
        e.set_price("AAPL", 150.0)
        strategy = GoldenCrossStrategy()
        runner = StrategyRunner(e, strategy, symbols=["AAPL"])
        runner.tick()
        assert runner._tick_count == 1

    def test_get_stats(self):
        e = PaperTradingEngine()
        e.set_price("AAPL", 150.0)
        strategy = GoldenCrossStrategy()
        runner = StrategyRunner(e, strategy, symbols=["AAPL"])
        runner.tick()
        stats = runner.get_stats()
        assert stats["ticks"] == 1
        assert "strategy" in stats
        assert stats["is_running"] is False

    def test_start_stop(self):
        e = PaperTradingEngine()
        e.set_price("AAPL", 150.0)
        strategy = GoldenCrossStrategy()
        runner = StrategyRunner(e, strategy, symbols=["AAPL"], interval=100)
        runner.start()
        assert runner.is_running is True
        runner.stop()
        assert runner.is_running is False

    def test_momentum_strategy(self):
        e = PaperTradingEngine()
        strategy = MomentumStrategy(lookback=5)
        runner = StrategyRunner(e, strategy, symbols=["TEST"])
        # Feed increasing prices to trigger buy
        for i in range(10):
            e.set_price("TEST", 100 + i * 10)
            runner.tick()
        # Strategy needs lookback period, then triggers
        assert runner._tick_count == 10

    def test_runner_error_handling(self):
        class BadStrategy:
            name = "bad"
            def on_tick(self, engine, symbols):
                raise RuntimeError("boom")

        e = PaperTradingEngine()
        runner = StrategyRunner(e, BadStrategy(), symbols=["X"])
        runner.tick()
        assert len(runner._errors) == 1
        assert "boom" in runner._errors[0]


# ──────────────────────────────────────────────────────────
# Journal Tests
# ──────────────────────────────────────────────────────────

class TestTradeJournal:
    def test_record_trade(self):
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0, "timestamp": time.time()})
        assert len(j.get_entries()) == 1

    def test_add_note(self):
        j = TradeJournal()
        j.add_note("Market looks bullish today")
        assert len(j.get_notes()) == 1
        assert "bullish" in j.get_notes()[0]["text"]

    def test_daily_summary(self):
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0, "timestamp": time.time()})
        j.add_note("Test note")
        summary = j.daily_summary()
        assert "AAPL" in summary
        assert "Trades: 1" in summary

    def test_daily_summary_no_activity(self):
        j = TradeJournal()
        summary = j.daily_summary("2020-01-01")
        assert "No activity" in summary

    def test_export_csv(self):
        j = TradeJournal()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0, "timestamp": time.time()})
        exported = j.export("csv")
        reader = csv.reader(io.StringIO(exported))
        rows = list(reader)
        assert len(rows) == 2  # header + 1 row
        assert "AAPL" in rows[1][2]

    def test_export_json(self):
        j = TradeJournal()
        j.record_trade({"symbol": "MSFT", "side": "SELL", "quantity": 5, "price": 400.0, "pnl": 50.0, "timestamp": time.time()})
        exported = j.export("json")
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["symbol"] == "MSFT"

    def test_performance_review(self):
        j = TradeJournal()
        now = time.time()
        j.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0, "timestamp": now})
        j.record_trade({"symbol": "AAPL", "side": "SELL", "quantity": 10, "price": 160.0, "pnl": 100.0, "timestamp": now})
        j.record_trade({"symbol": "MSFT", "side": "SELL", "quantity": 5, "price": 390.0, "pnl": -50.0, "timestamp": now})
        review = j.performance_review("1w")
        assert review["total_trades"] == 3
        assert review["win_count"] == 1
        assert review["loss_count"] == 1
        assert review["total_pnl"] == 50.0

    def test_performance_review_empty(self):
        j = TradeJournal()
        review = j.performance_review("1m")
        assert review["total_trades"] == 0
        assert review["win_rate"] == 0.0

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            j1 = TradeJournal(journal_path=path)
            j1.record_trade({"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0, "timestamp": time.time()})
            j1.add_note("persisted note")

            j2 = TradeJournal(journal_path=path)
            assert len(j2.get_entries()) == 1
            assert len(j2.get_notes()) == 1
        finally:
            os.unlink(path)

    def test_export_with_notes(self):
        j = TradeJournal()
        j.add_note("test note")
        exported = j.export("csv")
        assert "note" in exported


# ──────────────────────────────────────────────────────────
# CLI Integration Tests
# ──────────────────────────────────────────────────────────

def _import_main():
    """Import main from src/cli.py (the file, not the cli package)."""
    import importlib.util
    cli_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "cli.py")
    spec = importlib.util.spec_from_file_location("src_cli_main", cli_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


class TestPaperCLI:
    def test_paper_start(self, capsys):
        main = _import_main()
        main(["paper", "start", "--balance", "50000"])
        out = capsys.readouterr().out
        assert "Paper trading started" in out

    def test_paper_portfolio(self, capsys):
        main = _import_main()
        main(["paper", "start"])
        main(["paper", "portfolio"])
        out = capsys.readouterr().out
        assert "Portfolio" in out or "Cash" in out

    def test_paper_reset(self, capsys):
        main = _import_main()
        main(["paper", "start"])
        main(["paper", "reset"])
        out = capsys.readouterr().out
        assert "reset" in out.lower()

    def test_paper_pnl(self, capsys):
        main = _import_main()
        main(["paper", "start"])
        main(["paper", "pnl"])
        out = capsys.readouterr().out
        assert "P&L" in out

    def test_paper_no_subcommand(self, capsys):
        main = _import_main()
        main(["paper"])
        out = capsys.readouterr().out
        assert "Usage" in out
