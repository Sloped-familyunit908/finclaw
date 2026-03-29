"""Tests for A-share fee calculation (Fix 1).

Verifies that stamp tax and commission rates match current Chinese
securities regulation (effective 2023-08-28):
  - Stamp tax: 0.05% (sell side only)
  - Commission: ~0.025% (both buy and sell sides)
"""

import re
import pytest


def _read_backtest_source() -> str:
    """Read the _run_backtest method source for fee inspection."""
    import inspect
    from src.evolution.auto_evolve import AutoEvolver
    return inspect.getsource(AutoEvolver.evaluate)


def test_a_share_stamp_tax_rate():
    """Stamp tax should be 0.05% (0.0005) on sell side, not 0.10% (0.001).

    Current regulation: 0.05% since 2023-08-28.
    """
    source = _read_backtest_source()
    # Sell cost should include 0.0005 stamp tax, NOT 0.001
    assert "0.001" not in source or "0.0005 + 0.001" not in source, (
        "Old 0.10% stamp tax rate (0.001) found in source"
    )
    assert "0.0005" in source, "Expected 0.05% stamp tax rate (0.0005) in source"


def test_a_share_commission_rate():
    """Commission should be ~0.025% (0.00025) on both sides, not 0.08%.

    Most brokers now charge 0.025% or lower.
    """
    source = _read_backtest_source()
    assert "0.00025" in source, "Expected 0.025% commission rate (0.00025) in source"
    # Old rates should not appear
    assert "0.0003 + 0.0005" not in source, (
        "Old commission calculation (0.0003 + 0.0005) still present"
    )


def test_a_share_buy_fees():
    """Buy side: commission only (0.025%), no stamp tax."""
    source = _read_backtest_source()
    # Find the buy_cost line
    buy_cost_match = re.search(r'buy_cost\s*=\s*entry_price\s*\*\s*([\d.e-]+)', source)
    assert buy_cost_match is not None, "Could not find buy_cost calculation"
    buy_rate = float(buy_cost_match.group(1))
    # Should be commission only: 0.00025 (0.025%)
    assert abs(buy_rate - 0.00025) < 1e-6, (
        f"Buy fee rate should be 0.00025 (commission only), got {buy_rate}"
    )


def test_a_share_sell_fees():
    """Sell side: commission (0.025%) + stamp tax (0.05%).

    Total sell fee rate should be 0.00025 + 0.0005 = 0.00075.
    """
    source = _read_backtest_source()
    # Find the sell_cost line — should contain 0.00025 + 0.0005
    sell_cost_match = re.search(
        r'sell_cost\s*=\s*exit_price\s*\*\s*\(([\d.e-]+)\s*\+\s*([\d.e-]+)\)',
        source,
    )
    assert sell_cost_match is not None, "Could not find sell_cost calculation"
    rate1 = float(sell_cost_match.group(1))
    rate2 = float(sell_cost_match.group(2))
    total_sell_rate = rate1 + rate2
    expected = 0.00025 + 0.0005  # commission + stamp tax
    assert abs(total_sell_rate - expected) < 1e-6, (
        f"Sell fee rate should be {expected} (commission + stamp tax), got {total_sell_rate}"
    )
