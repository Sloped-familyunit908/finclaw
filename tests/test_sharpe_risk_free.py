"""Tests for Sharpe ratio with risk-free rate (Fix 7).

Verifies that Sharpe ratio subtracts the risk-free rate from excess returns
instead of using raw returns.
"""

import inspect
import re
import pytest


def test_sharpe_with_risk_free_rate_a_share():
    """A-share backtest Sharpe should subtract risk-free rate from returns."""
    from src.evolution.auto_evolve import AutoEvolver
    source = inspect.getsource(AutoEvolver.evaluate)

    # Should find risk-free rate subtraction in Sharpe calculation
    has_rf = re.search(r'rf_per_period', source)
    assert has_rf, (
        "A-share backtest Sharpe should use rf_per_period "
        "(risk-free rate per period)"
    )

    # Should find mean_r - rf_per_period pattern  
    has_excess_return = re.search(r'mean_r\s*-\s*rf_per_period', source)
    assert has_excess_return, (
        "Sharpe should compute excess return as (mean_r - rf_per_period)"
    )


def test_sharpe_with_risk_free_rate_crypto():
    """Crypto backtest Sharpe should also subtract risk-free rate."""
    from src.evolution.crypto_backtest import CryptoBacktestEngine
    source = inspect.getsource(CryptoBacktestEngine.run_backtest)

    has_rf = re.search(r'rf_per_period', source)
    assert has_rf, (
        "Crypto backtest Sharpe should use rf_per_period"
    )

    has_excess_return = re.search(r'mean_r\s*-\s*rf_per_period', source)
    assert has_excess_return, (
        "Crypto Sharpe should compute excess return as (mean_r - rf_per_period)"
    )


def test_sharpe_risk_free_rate_is_configurable():
    """Risk-free rate should be configurable via FINCLAW_RISK_FREE_RATE env var."""
    from src.evolution.auto_evolve import AutoEvolver
    source = inspect.getsource(AutoEvolver.evaluate)

    has_env_config = re.search(r'FINCLAW_RISK_FREE_RATE', source)
    assert has_env_config, (
        "Risk-free rate should be configurable via FINCLAW_RISK_FREE_RATE env var"
    )


def test_sharpe_default_risk_free_rate():
    """Default risk-free rate should be 4% (0.04) annual."""
    from src.evolution.auto_evolve import AutoEvolver
    source = inspect.getsource(AutoEvolver.evaluate)

    # Should find default of 0.04
    has_default = re.search(r'["\']0\.04["\']', source)
    assert has_default, (
        "Default risk-free rate should be 0.04 (4% annual)"
    )
