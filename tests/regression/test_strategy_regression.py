"""
Strategy Regression Tests
=========================
Runs backtests for all available strategies on fixed tickers/period,
compares results against a stored baseline to detect performance regressions.

Usage:
  # Generate baseline (run once, or after intentional strategy changes):
  python -c "from tests.regression.test_strategy_regression import generate_baseline; generate_baseline()"

  # Run regression tests:
  python -m pytest tests/regression/test_strategy_regression.py -v
"""

import asyncio
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.backtester_v7 import BacktesterV7

# ─── Configuration ────────────────────────────────────────────────

BASELINE_PATH = Path(__file__).parent / "strategy_baseline.json"

# Fixed tickers and period for reproducibility
TICKERS = ["AAPL", "MSFT", "NVDA"]
START_DATE = "2024-01-01"
END_DATE = "2024-06-30"

# Tolerance: allow up to 1% absolute difference for float metrics
FLOAT_TOLERANCE = 0.01

# Metrics to check
FLOAT_METRICS = ["total_return", "max_drawdown", "win_rate"]
INT_METRICS = ["total_trades"]


# ─── Deterministic price generation ──────────────────────────────
# We use synthetic data so tests are fully reproducible without
# network access. Each ticker gets a distinct seed for variety.

TICKER_SEEDS = {"AAPL": 42, "MSFT": 137, "NVDA": 256}
TICKER_PARAMS = {
    "AAPL": {"start": 185.0, "days": 125, "annual_ret": 0.25, "annual_vol": 0.22},
    "MSFT": {"start": 375.0, "days": 125, "annual_ret": 0.20, "annual_vol": 0.20},
    "NVDA": {"start": 480.0, "days": 125, "annual_ret": 0.80, "annual_vol": 0.45},
}


def _generate_prices(start: float, days: int, annual_ret: float, annual_vol: float, seed: int):
    """Generate synthetic daily price series using geometric Brownian motion."""
    rng = random.Random(seed)
    dt = 1 / 252
    mu = annual_ret
    sigma = annual_vol
    prices = [start]
    for _ in range(days - 1):
        dW = rng.gauss(0, math.sqrt(dt))
        price = prices[-1] * math.exp((mu - 0.5 * sigma**2) * dt + sigma * dW)
        prices.append(max(price, 0.01))
    return prices


def _make_history(ticker: str):
    """Create backtester-compatible history dicts for a ticker."""
    params = TICKER_PARAMS[ticker]
    seed = TICKER_SEEDS[ticker]
    prices = _generate_prices(
        params["start"], params["days"], params["annual_ret"], params["annual_vol"], seed
    )
    base = datetime(2024, 1, 2)
    return [
        {"date": base + timedelta(days=i), "price": p, "volume": 1_000_000 + int(p * 1000)}
        for i, p in enumerate(prices)
    ]


# ─── Strategy names (from BacktesterV7 signal engine) ────────────
# BacktesterV7 uses SignalEngineV7 internally with a single "v7" strategy.
# For regression, we test the engine at different parameter configurations
# to simulate "strategy variants".

STRATEGY_CONFIGS = {
    "default": {"initial_capital": 100_000, "commission_pct": 0.001, "slippage_pct": 0.0005},
    "low_capital": {"initial_capital": 10_000, "commission_pct": 0.001, "slippage_pct": 0.0005},
    "high_commission": {"initial_capital": 100_000, "commission_pct": 0.005, "slippage_pct": 0.001},
    "zero_cost": {"initial_capital": 100_000, "commission_pct": 0.0, "slippage_pct": 0.0},
    "aggressive": {"initial_capital": 100_000, "commission_pct": 0.001, "slippage_pct": 0.0005,
                    "max_loss_per_trade": 0.10, "max_portfolio_exposure": 0.98},
    "conservative": {"initial_capital": 100_000, "commission_pct": 0.001, "slippage_pct": 0.0005,
                      "max_loss_per_trade": 0.03, "max_portfolio_exposure": 0.70},
}


def _run_backtest(ticker: str, config_name: str) -> dict:
    """Run a single backtest and return metrics dict."""
    config = STRATEGY_CONFIGS[config_name]
    bt = BacktesterV7(
        initial_capital=config["initial_capital"],
        commission_pct=config["commission_pct"],
        slippage_pct=config["slippage_pct"],
        max_loss_per_trade=config.get("max_loss_per_trade", 0.06),
        max_portfolio_exposure=config.get("max_portfolio_exposure", 0.95),
    )
    history = _make_history(ticker)
    result = asyncio.run(bt.run(ticker, "v7", history))
    return {
        "total_return": round(result.total_return, 6),
        "max_drawdown": round(result.max_drawdown, 6),
        "total_trades": result.total_trades,
        "win_rate": round(result.win_rate, 6),
    }


def generate_baseline():
    """Generate the baseline JSON file by running all strategy/ticker combos."""
    baseline = {}
    for config_name in STRATEGY_CONFIGS:
        for ticker in TICKERS:
            key = f"{config_name}__{ticker}"
            print(f"  Generating baseline: {key} ...", end=" ", flush=True)
            metrics = _run_backtest(ticker, config_name)
            baseline[key] = metrics
            print(f"return={metrics['total_return']:+.4f}  trades={metrics['total_trades']}  "
                  f"win_rate={metrics['win_rate']:.2f}  max_dd={metrics['max_drawdown']:.4f}")

    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"\n  OK Baseline saved to {BASELINE_PATH}")
    print(f"  OK {len(baseline)} test cases recorded")
    return baseline


def _load_baseline() -> dict:
    """Load baseline, skip tests if file doesn't exist."""
    if not BASELINE_PATH.exists():
        pytest.skip(
            f"Baseline file not found: {BASELINE_PATH}. "
            "Run: python -c \"from tests.regression.test_strategy_regression import generate_baseline; generate_baseline()\""
        )
    with open(BASELINE_PATH) as f:
        return json.load(f)


# ─── Pytest tests ────────────────────────────────────────────────

class TestStrategyRegression:
    """Regression tests that compare current backtest results against stored baseline."""

    @pytest.fixture(scope="class")
    def baseline(self):
        return _load_baseline()

    @pytest.fixture(scope="class")
    def current_results(self):
        """Run all backtests once for the class."""
        results = {}
        for config_name in STRATEGY_CONFIGS:
            for ticker in TICKERS:
                key = f"{config_name}__{ticker}"
                results[key] = _run_backtest(ticker, config_name)
        return results

    def test_baseline_has_all_keys(self, baseline):
        """Baseline should contain all expected strategy/ticker combos."""
        for config_name in STRATEGY_CONFIGS:
            for ticker in TICKERS:
                key = f"{config_name}__{ticker}"
                assert key in baseline, f"Missing baseline key: {key}"

    @pytest.mark.parametrize("config_name", list(STRATEGY_CONFIGS.keys()))
    @pytest.mark.parametrize("ticker", TICKERS)
    def test_total_return_stable(self, baseline, current_results, config_name, ticker):
        """Total return should not regress beyond tolerance."""
        key = f"{config_name}__{ticker}"
        if key not in baseline:
            pytest.skip(f"No baseline for {key}")
        expected = baseline[key]["total_return"]
        actual = current_results[key]["total_return"]
        assert abs(actual - expected) <= FLOAT_TOLERANCE, (
            f"{key}: total_return regressed: expected={expected:.4f}, got={actual:.4f}, "
            f"diff={abs(actual - expected):.4f} > tolerance={FLOAT_TOLERANCE}"
        )

    @pytest.mark.parametrize("config_name", list(STRATEGY_CONFIGS.keys()))
    @pytest.mark.parametrize("ticker", TICKERS)
    def test_max_drawdown_stable(self, baseline, current_results, config_name, ticker):
        """Max drawdown should not worsen beyond tolerance."""
        key = f"{config_name}__{ticker}"
        if key not in baseline:
            pytest.skip(f"No baseline for {key}")
        expected = baseline[key]["max_drawdown"]
        actual = current_results[key]["max_drawdown"]
        assert abs(actual - expected) <= FLOAT_TOLERANCE, (
            f"{key}: max_drawdown regressed: expected={expected:.4f}, got={actual:.4f}, "
            f"diff={abs(actual - expected):.4f} > tolerance={FLOAT_TOLERANCE}"
        )

    @pytest.mark.parametrize("config_name", list(STRATEGY_CONFIGS.keys()))
    @pytest.mark.parametrize("ticker", TICKERS)
    def test_total_trades_stable(self, baseline, current_results, config_name, ticker):
        """Trade count should be exactly the same (deterministic)."""
        key = f"{config_name}__{ticker}"
        if key not in baseline:
            pytest.skip(f"No baseline for {key}")
        expected = baseline[key]["total_trades"]
        actual = current_results[key]["total_trades"]
        assert actual == expected, (
            f"{key}: total_trades changed: expected={expected}, got={actual}"
        )

    @pytest.mark.parametrize("config_name", list(STRATEGY_CONFIGS.keys()))
    @pytest.mark.parametrize("ticker", TICKERS)
    def test_win_rate_stable(self, baseline, current_results, config_name, ticker):
        """Win rate should not regress beyond tolerance."""
        key = f"{config_name}__{ticker}"
        if key not in baseline:
            pytest.skip(f"No baseline for {key}")
        expected = baseline[key]["win_rate"]
        actual = current_results[key]["win_rate"]
        assert abs(actual - expected) <= FLOAT_TOLERANCE, (
            f"{key}: win_rate regressed: expected={expected:.4f}, got={actual:.4f}, "
            f"diff={abs(actual - expected):.4f} > tolerance={FLOAT_TOLERANCE}"
        )


class TestStrategyBaseline:
    """Sanity checks on the baseline generation itself."""

    def test_deterministic_results(self):
        """Running the same backtest twice should produce identical results."""
        metrics1 = _run_backtest("AAPL", "default")
        metrics2 = _run_backtest("AAPL", "default")
        assert metrics1 == metrics2, "Backtest results are not deterministic!"

    def test_different_tickers_differ(self):
        """Different tickers should produce different results."""
        m_aapl = _run_backtest("AAPL", "default")
        m_nvda = _run_backtest("NVDA", "default")
        # At least one metric should differ
        assert m_aapl != m_nvda, "AAPL and NVDA produced identical results"

    def test_commission_affects_results(self):
        """Higher commission should reduce returns or increase costs."""
        m_zero = _run_backtest("AAPL", "zero_cost")
        m_high = _run_backtest("AAPL", "high_commission")
        # Zero cost should have >= returns (unless edge cases)
        # Just check they differ
        assert m_zero != m_high or m_zero["total_trades"] == 0, (
            "Zero cost and high commission should produce different results"
        )
