"""
Paper Trading Workflow Tests
============================
End-to-end paper trading workflow: start → buy → portfolio → sell → P&L → reset.
Uses price overrides to avoid network calls.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.paper.engine import (
    PaperTradingEngine,
    Order,
    OrderSide,
    OrderStatus,
    Portfolio,
    PnL,
)


class TestPaperTradingWorkflow:
    """End-to-end paper trading workflow test."""

    @pytest.fixture
    def engine(self):
        """Create a fresh paper trading engine with price overrides."""
        eng = PaperTradingEngine(initial_balance=100_000)
        eng.set_price("AAPL", 190.0)
        eng.set_price("MSFT", 420.0)
        eng.set_price("NVDA", 900.0)
        return eng

    def test_full_workflow_buy_check_sell_pnl(self, engine):
        """Complete workflow: buy → check portfolio → sell → check P&L."""
        # Step 1: Buy stock
        buy_order = engine.buy("AAPL", 100)
        assert buy_order.status == OrderStatus.FILLED
        assert buy_order.side == OrderSide.BUY
        assert buy_order.quantity == 100
        assert buy_order.filled_price == 190.0

        # Step 2: Check portfolio
        portfolio = engine.get_portfolio()
        assert "AAPL" in portfolio.positions
        pos = portfolio.positions["AAPL"]
        assert pos.quantity == 100
        assert pos.avg_cost == 190.0
        assert portfolio.cash == 100_000 - (190.0 * 100)  # 81,000

        # Step 3: Price goes up, sell
        engine.set_price("AAPL", 200.0)
        sell_order = engine.sell("AAPL", 100)
        assert sell_order.status == OrderStatus.FILLED
        assert sell_order.side == OrderSide.SELL
        assert sell_order.filled_price == 200.0

        # Step 4: Check P&L
        pnl = engine.get_pnl()
        expected_pnl = (200.0 - 190.0) * 100  # $1,000 profit
        assert pnl.realized == expected_pnl
        assert pnl.total_trades == 1
        assert pnl.win_count == 1
        assert pnl.win_rate == 100.0

        # Step 5: No positions left
        portfolio = engine.get_portfolio()
        assert "AAPL" not in portfolio.positions
        assert portfolio.cash == pytest.approx(100_000 + expected_pnl, abs=0.01)

    def test_full_workflow_with_loss(self, engine):
        """Workflow where trade results in a loss."""
        # Buy
        engine.buy("MSFT", 50)
        assert engine.get_portfolio().positions["MSFT"].quantity == 50

        # Price drops
        engine.set_price("MSFT", 400.0)
        engine.sell("MSFT", 50)

        # P&L should show loss
        pnl = engine.get_pnl()
        expected_loss = (400.0 - 420.0) * 50  # -$1,000
        assert pnl.realized == expected_loss
        assert pnl.loss_count == 1
        assert pnl.win_count == 0

    def test_multiple_stocks_workflow(self, engine):
        """Buy and sell multiple stocks."""
        # Buy AAPL and MSFT
        engine.buy("AAPL", 50)
        engine.buy("MSFT", 20)

        portfolio = engine.get_portfolio()
        assert len(portfolio.positions) == 2
        assert "AAPL" in portfolio.positions
        assert "MSFT" in portfolio.positions

        # Check total value
        expected_invested = 50 * 190.0 + 20 * 420.0  # 9500 + 8400 = 17900
        assert portfolio.cash == pytest.approx(100_000 - expected_invested, abs=0.01)
        assert portfolio.total_value == pytest.approx(100_000, abs=0.01)

        # Prices change
        engine.set_price("AAPL", 200.0)
        engine.set_price("MSFT", 410.0)

        # Sell both
        engine.sell("AAPL", 50)
        engine.sell("MSFT", 20)

        pnl = engine.get_pnl()
        aapl_pnl = (200.0 - 190.0) * 50   # +500
        msft_pnl = (410.0 - 420.0) * 20   # -200
        assert pnl.realized == pytest.approx(aapl_pnl + msft_pnl, abs=0.01)

    def test_partial_sell(self, engine):
        """Sell only part of a position."""
        engine.buy("AAPL", 100)

        # Sell 40 shares
        engine.set_price("AAPL", 195.0)
        engine.sell("AAPL", 40)

        portfolio = engine.get_portfolio()
        assert "AAPL" in portfolio.positions
        assert portfolio.positions["AAPL"].quantity == 60

        # Sell remaining
        engine.sell("AAPL", 60)
        portfolio = engine.get_portfolio()
        assert "AAPL" not in portfolio.positions

    def test_buy_accumulate_position(self, engine):
        """Multiple buys should accumulate the position with averaged cost."""
        engine.buy("AAPL", 50)  # avg_cost = 190
        engine.set_price("AAPL", 200.0)
        engine.buy("AAPL", 50)  # avg_cost = (190*50 + 200*50) / 100 = 195

        portfolio = engine.get_portfolio()
        pos = portfolio.positions["AAPL"]
        assert pos.quantity == 100
        assert pos.avg_cost == pytest.approx(195.0, abs=0.01)

    def test_insufficient_funds_rejected(self, engine):
        """Buying more than available cash should be rejected."""
        # Try to buy something very expensive
        engine.set_price("NVDA", 900.0)
        order = engine.buy("NVDA", 200)  # 200 * 900 = 180,000 > 100,000
        assert order.status == OrderStatus.REJECTED

    def test_insufficient_position_rejected(self, engine):
        """Selling more shares than owned should be rejected."""
        engine.buy("AAPL", 10)
        order = engine.sell("AAPL", 20)
        assert order.status == OrderStatus.REJECTED

    def test_sell_nonexistent_position_rejected(self, engine):
        """Selling a stock not held should be rejected."""
        order = engine.sell("GOOGL", 10)
        assert order.status == OrderStatus.REJECTED

    def test_reset_clears_everything(self, engine):
        """Reset should restore engine to initial state."""
        # Do some trading
        engine.buy("AAPL", 50)
        engine.buy("MSFT", 20)
        engine.set_price("AAPL", 200.0)
        engine.sell("AAPL", 50)

        # Verify state is dirty
        assert len(engine.orders) > 0
        assert len(engine.trade_log) > 0

        # Reset
        engine.reset()

        # Verify clean state
        assert engine.balance == 100_000
        assert len(engine.positions) == 0
        assert len(engine.orders) == 0
        assert len(engine.trade_log) == 0
        pnl = engine.get_pnl()
        assert pnl.realized == 0.0
        assert pnl.total_trades == 0

    def test_portfolio_total_return(self, engine):
        """Portfolio total_return should reflect P&L accurately."""
        engine.buy("AAPL", 100)
        engine.set_price("AAPL", 200.0)

        portfolio = engine.get_portfolio()
        # Unrealized gain: (200-190)*100 = $1000 on 100k = 1%
        expected_return = ((100_000 - 19_000 + 200 * 100) / 100_000 - 1) * 100
        assert portfolio.total_return == pytest.approx(expected_return, abs=0.1)

    def test_trade_history_recorded(self, engine):
        """Trade history should record all trades."""
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 195.0)
        engine.sell("AAPL", 10)

        history = engine.get_trade_history()
        assert len(history) == 2

        buy_trade = history[0]
        assert buy_trade["side"] == "BUY"
        assert buy_trade["symbol"] == "AAPL"
        assert buy_trade["quantity"] == 10

        sell_trade = history[1]
        assert sell_trade["side"] == "SELL"
        assert sell_trade["symbol"] == "AAPL"
        assert sell_trade["quantity"] == 10
        assert "pnl" in sell_trade

    def test_equity_history_tracks_value(self, engine):
        """Equity history should record data points after trades."""
        assert len(engine.get_equity_history()) == 0

        engine.buy("AAPL", 50)
        assert len(engine.get_equity_history()) == 1

        engine.set_price("AAPL", 200.0)
        engine.sell("AAPL", 50)
        assert len(engine.get_equity_history()) == 2

    def test_unrealized_pnl_tracked(self, engine):
        """Unrealized PnL should reflect current market prices.

        Note: get_portfolio() refreshes position prices from overrides,
        while get_pnl() uses the last known current_price on positions.
        We call get_portfolio() first to trigger the price refresh.
        """
        engine.buy("AAPL", 100)  # 100 shares @ 190

        # Price goes up
        engine.set_price("AAPL", 200.0)
        engine.get_portfolio()  # refresh current_price on positions
        pnl = engine.get_pnl()
        assert pnl.unrealized == pytest.approx(1000.0, abs=0.01)  # (200-190)*100

        # Price goes down
        engine.set_price("AAPL", 180.0)
        engine.get_portfolio()  # refresh current_price on positions
        pnl = engine.get_pnl()
        assert pnl.unrealized == pytest.approx(-1000.0, abs=0.01)  # (180-190)*100

    def test_limit_order_buy(self, engine):
        """Limit buy order should be created with PENDING status."""
        order = engine.buy("AAPL", 50, order_type="limit", limit_price=185.0)
        assert order.status == OrderStatus.PENDING
        assert order.limit_price == 185.0

    def test_limit_order_sell(self, engine):
        """Limit sell order should be created with PENDING status."""
        engine.buy("AAPL", 50)
        order = engine.sell("AAPL", 50, order_type="limit", limit_price=200.0)
        assert order.status == OrderStatus.PENDING
        assert order.limit_price == 200.0

    def test_portfolio_to_dict(self, engine):
        """Portfolio.to_dict() should return serializable dict."""
        engine.buy("AAPL", 50)
        portfolio = engine.get_portfolio()
        d = portfolio.to_dict()

        assert "cash" in d
        assert "positions" in d
        assert "total_value" in d
        assert "initial_balance" in d
        assert "total_return" in d
        assert "AAPL" in d["positions"]

    def test_pnl_to_dict(self, engine):
        """PnL.to_dict() should return serializable dict."""
        engine.buy("AAPL", 50)
        engine.set_price("AAPL", 195.0)
        engine.sell("AAPL", 50)

        pnl = engine.get_pnl()
        d = pnl.to_dict()

        assert "realized" in d
        assert "unrealized" in d
        assert "total" in d
        assert "win_rate" in d
        assert "total_trades" in d
