"""Tests for BacktesterV7 — full lifecycle backtesting."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from agents.backtester_v7 import BacktesterV7
from tests.conftest import (
    make_bull_prices, make_bear_prices, make_crash_prices,
    make_ranging_prices, make_volatile_prices, make_history,
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def bt():
    return BacktesterV7(initial_capital=100_000)


class TestBacktesterBasics:
    def test_bull_market_profitable(self, bt):
        h = make_history(make_bull_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_return > 0, f"Bull market should be profitable, got {r.total_return}"

    def test_bear_market_limited_loss(self, bt):
        h = make_history(make_bear_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_return > -0.5, f"Bear loss too large: {r.total_return}"

    def test_crash_survival(self, bt):
        h = make_history(make_crash_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_return > -0.6, f"Crash loss too large: {r.total_return}"

    def test_ranging_not_catastrophic(self, bt):
        h = make_history(make_ranging_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_return > -0.3

    def test_volatile_market_survives(self, bt):
        h = make_history(make_volatile_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_return > -0.5


class TestBacktesterMetrics:
    def test_max_drawdown_range(self, bt):
        h = make_history(make_bull_prices(300))
        r = run(bt.run("TEST", "v7", h))
        assert -1.0 <= r.max_drawdown <= 0.0

    def test_win_rate_range(self, bt):
        h = make_history(make_bull_prices(300))
        r = run(bt.run("TEST", "v7", h))
        assert 0.0 <= r.win_rate <= 1.0

    def test_total_trades_positive(self, bt):
        h = make_history(make_bull_prices(500))
        r = run(bt.run("TEST", "v7", h))
        assert r.total_trades >= 0

    def test_result_has_required_fields(self, bt):
        h = make_history(make_bull_prices(200))
        r = run(bt.run("TEST", "v7", h))
        assert hasattr(r, 'total_return')
        assert hasattr(r, 'max_drawdown')
        assert hasattr(r, 'total_trades')
        assert hasattr(r, 'win_rate')


class TestBacktesterConfig:
    def test_different_capital(self):
        bt = BacktesterV7(initial_capital=50_000)
        h = make_history(make_bull_prices(200))
        r = run(bt.run("TEST", "v7", h))
        assert isinstance(r.total_return, float)

    def test_small_capital(self):
        bt = BacktesterV7(initial_capital=1_000)
        h = make_history(make_bull_prices(200))
        r = run(bt.run("TEST", "v7", h))
        assert isinstance(r.total_return, float)

    def test_warmup_no_trades(self):
        """Very short history should produce 0 trades or hold."""
        bt = BacktesterV7(initial_capital=100_000)
        h = make_history([100.0] * 25)
        r = run(bt.run("TEST", "v7", h))
        assert r.total_trades == 0
