"""Tests for paper trading fee deduction (Fix 3).

Verifies that CryptoLiveRunner.execute_buy and execute_sell
deduct taker fees (0.04% = 0.0004), consistent with crypto_backtest engine.
"""

import pytest

from src.crypto.live_runner import CryptoLiveRunner


def _make_runner(balance: float = 10_000.0) -> CryptoLiveRunner:
    """Create a runner in dry_run mode for testing."""
    runner = CryptoLiveRunner(
        exchange="binance",
        mode="dry_run",
        initial_balance=balance,
        symbols=["BTC/USDT"],
    )
    runner.dna = runner._default_dna()
    runner.dna["max_positions"] = 5
    runner._cycle_prices = {}
    return runner


def test_paper_trade_buy_deducts_fee():
    """Buy order should deduct 0.04% taker fee from cash.

    cost_with_fee = qty * price * (1 + 0.0004)
    """
    runner = _make_runner(10_000.0)
    price = 50_000.0
    initial_cash = runner.cash

    trade = runner.execute_buy("BTC/USDT", price, score=7.0)
    assert trade is not None, "Buy should succeed"

    qty = trade["qty"]
    expected_cost = qty * price
    expected_fee = expected_cost * 0.0004
    expected_total = expected_cost + expected_fee

    # Cash should be reduced by cost + fee
    actual_spent = initial_cash - runner.cash
    assert abs(actual_spent - expected_total) < 0.01, (
        f"Expected to spend ${expected_total:.2f} (incl fee ${expected_fee:.2f}), "
        f"actually spent ${actual_spent:.2f}"
    )

    # Trade record should include fee
    assert "fee" in trade, "Trade record should include 'fee' field"
    assert abs(trade["fee"] - expected_fee) < 0.01, (
        f"Trade fee should be ${expected_fee:.2f}, got ${trade['fee']:.2f}"
    )


def test_paper_trade_sell_deducts_fee():
    """Sell order should deduct 0.04% taker fee from revenue.

    net_revenue = qty * price * (1 - 0.0004)
    """
    runner = _make_runner(10_000.0)
    buy_price = 50_000.0
    sell_price = 51_000.0

    # First buy
    runner.execute_buy("BTC/USDT", buy_price, score=7.0)
    cash_after_buy = runner.cash
    pos = runner.positions["BTC/USDT"]
    qty = pos.qty

    # Then sell at higher price
    trade = runner.execute_sell("BTC/USDT", sell_price, score=3.0)
    assert trade is not None, "Sell should succeed"

    gross_revenue = qty * sell_price
    expected_fee = gross_revenue * 0.0004
    expected_net_revenue = gross_revenue - expected_fee

    # Cash increase should be net revenue (after fee)
    actual_received = runner.cash - cash_after_buy
    assert abs(actual_received - expected_net_revenue) < 0.01, (
        f"Expected to receive ${expected_net_revenue:.2f} (net of fee ${expected_fee:.2f}), "
        f"actually received ${actual_received:.2f}"
    )

    # Trade record should include fee  
    assert "fee" in trade, "Trade record should include 'fee' field"
    assert abs(trade["fee"] - expected_fee) < 0.01, (
        f"Trade fee should be ${expected_fee:.2f}, got ${trade['fee']:.2f}"
    )
