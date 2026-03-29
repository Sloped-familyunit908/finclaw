"""Tests for no look-ahead bias (Fix 6).

Verifies that backtests score stocks using data available BEFORE the
entry period, preventing look-ahead bias.
"""

import inspect
import re
import pytest


def test_crypto_backtest_no_lookahead():
    """Verify score_stock is called with period-1 (previous candle), not period.

    In crypto_backtest.py, when scoring at 'period', we should use
    indicators from period-1 to avoid look-ahead.
    """
    from src.evolution.crypto_backtest import CryptoBacktestEngine
    source = inspect.getsource(CryptoBacktestEngine.run_backtest)

    # Should find score_stock(period - 1, ...) — using previous candle
    # Common patterns: "score_stock(period - 1, ind, dna)" or similar
    has_period_minus_1 = re.search(
        r'score_stock\s*\(\s*period\s*-\s*1\s*,', source
    )
    assert has_period_minus_1, (
        "crypto_backtest should call score_stock(period - 1, ...) "
        "to avoid look-ahead bias"
    )

    # Should NOT find score_stock(period, ...) without the -1
    # (Check that there's no call using current period for scoring)
    direct_period_calls = re.findall(
        r'score_stock\s*\(\s*period\s*,', source
    )
    assert len(direct_period_calls) == 0, (
        f"Found {len(direct_period_calls)} calls to score_stock(period, ...) "
        "without look-ahead protection. Should use period-1."
    )


def test_a_share_backtest_no_lookahead():
    """Verify A-share backtest scores at day d, enters at d+1.

    The evaluate() method in AutoEvolver should:
    1. Score stocks at day 'day' (using indicators[day])
    2. Enter positions at day+1 open price (T+1)
    """
    from src.evolution.auto_evolve import AutoEvolver
    source = inspect.getsource(AutoEvolver.evaluate)

    # Should score at 'day' and enter at 'day + 1'
    # Check entry_day = day + 1 pattern
    has_t_plus_1_entry = re.search(
        r'entry_day\s*=\s*day\s*\+\s*1', source
    )
    assert has_t_plus_1_entry, (
        "A-share backtest should have entry_day = day + 1 (T+1 rule)"
    )

    # Entry price should use open price of entry_day
    has_open_entry = re.search(
        r'entry_price\s*=\s*sd\[.open.\]\[entry_day\]', source
    )
    assert has_open_entry, (
        "A-share backtest should enter at open price of entry_day"
    )
