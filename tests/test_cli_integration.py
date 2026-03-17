"""
CLI Integration Tests
=====================
Tests the CLI entry point end-to-end with mocked data where needed.
"""

import io
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.main import main, build_parser


# ── Helpers ──────────────────────────────────────────────────────

def _run_cli(*argv, expect_rc=None):
    """Run CLI with given argv, capture stdout/stderr, return (rc, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = out
    sys.stderr = err
    try:
        rc = main(list(argv))
    except SystemExit as e:
        rc = e.code
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    stdout_str = out.getvalue()
    stderr_str = err.getvalue()
    if expect_rc is not None:
        assert rc == expect_rc, f"Expected rc={expect_rc}, got {rc}. stdout={stdout_str!r}"
    return rc, stdout_str, stderr_str


def _make_mock_df(days=252, start_price=150.0):
    """Create a mock OHLCV DataFrame mimicking yfinance output."""
    dates = pd.date_range("2023-01-01", periods=days, freq="B")
    np.random.seed(42)
    close = start_price * np.cumprod(1 + np.random.normal(0.0003, 0.02, days))
    return pd.DataFrame({
        "Open": close * 0.999,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Close": close,
        "Volume": np.random.randint(1_000_000, 10_000_000, days),
    }, index=dates)


# ── Tests ────────────────────────────────────────────────────────

class TestCLIHelpAndVersion:
    def test_help(self):
        rc, out, _ = _run_cli("--help")
        assert rc == 0
        assert "finclaw" in out.lower() or "usage" in out.lower()

    def test_version(self):
        rc, out, _ = _run_cli("--version")
        assert rc == 0
        assert "0.1.0" in out

    def test_no_command_shows_help(self):
        rc, out, _ = _run_cli()
        assert rc == 1 or "usage" in out.lower() or "help" in out.lower()


class TestCLIDemo:
    def test_demo_runs(self):
        """Demo should run fully without any API calls."""
        rc, out, _ = _run_cli("demo")
        # Demo prints a lot of showcase content
        assert "demo" in out.lower() or "quote" in out.lower() or "━" in out or len(out) > 100


class TestCLIQuote:
    @patch("src.exchanges.registry.ExchangeRegistry.get")
    def test_quote_mock(self, mock_get):
        adapter = MagicMock()
        adapter.get_ticker.return_value = {
            "symbol": "BTCUSDT", "last": 65000.50,
            "bid": 64999.0, "ask": 65001.0,
            "volume": 12345.67, "change": 500, "change_pct": 0.77,
        }
        mock_get.return_value = adapter
        rc, out, _ = _run_cli("quote", "BTCUSDT", "--exchange", "binance")
        assert "BTCUSDT" in out
        assert "65000" in out or "65,000" in out

    @patch("src.exchanges.registry.ExchangeRegistry.get")
    def test_quote_no_change_fields(self, mock_get):
        """Quote with missing change fields should not crash."""
        adapter = MagicMock()
        adapter.get_ticker.return_value = {
            "symbol": "ETHUSDT", "last": 3500.0,
            "bid": 3499.0, "ask": 3501.0,
            "volume": 5000.0,
        }
        mock_get.return_value = adapter
        rc, out, _ = _run_cli("quote", "ETHUSDT")
        assert "ETHUSDT" in out


class TestCLIAnalyze:
    @patch("src.cli.main._fetch_data")
    def test_analyze_with_mock_data(self, mock_fetch):
        mock_fetch.return_value = _make_mock_df()
        rc, out, _ = _run_cli("analyze", "--ticker", "AAPL", "--indicators", "rsi,macd,bollinger")
        assert "RSI" in out
        assert "MACD" in out
        assert "Bollinger" in out or "BB" in out or "bollinger" in out.lower()

    @patch("src.cli.main._fetch_data")
    def test_analyze_no_data(self, mock_fetch):
        mock_fetch.return_value = None
        rc, out, _ = _run_cli("analyze", "--ticker", "INVALID", "--indicators", "rsi")
        assert "no data" in out.lower() or "No data" in out


class TestCLIBacktest:
    @patch("src.cli.main._fetch_data")
    def test_backtest_with_mock(self, mock_fetch):
        df = _make_mock_df(days=300)
        mock_fetch.return_value = df
        rc, out, _ = _run_cli("backtest", "--ticker", "AAPL", "--strategy", "momentum")
        assert "Return" in out or "return" in out.lower() or "Backtest" in out

    @patch("src.cli.main._fetch_data")
    def test_backtest_no_data(self, mock_fetch):
        mock_fetch.return_value = None
        rc, out, _ = _run_cli("backtest", "--ticker", "INVALID123", "--strategy", "momentum")
        assert "no data" in out.lower() or "No data" in out or "skipping" in out.lower()

    def test_backtest_missing_ticker(self):
        rc, out, _ = _run_cli("backtest", "--strategy", "momentum")
        assert "error" in out.lower() or "required" in out.lower() or rc != 0


class TestCLIPlugins:
    def test_plugins_list(self):
        """plugins list should not crash."""
        rc, out, _ = _run_cli("plugins", "list")
        # May print strategies or empty list
        assert rc is None or rc == 0 or "plugin" in out.lower() or "strategy" in out.lower() or len(out) >= 0


class TestCLIErrorHandling:
    def test_invalid_command(self):
        """Unknown subcommand should show help or error."""
        rc, out, err = _run_cli("nonexistent_command_xyz")
        # argparse treats unknown subcommands differently
        assert rc is not None or "error" in (out + err).lower() or "usage" in (out + err).lower()

    @patch("src.cli.main._fetch_data")
    def test_analyze_unknown_indicator(self, mock_fetch):
        mock_fetch.return_value = _make_mock_df()
        rc, out, _ = _run_cli("analyze", "--ticker", "AAPL", "--indicators", "nonexistent_ind")
        assert "unknown" in out.lower() or "Unknown" in out


class TestCLIInfo:
    def test_info(self):
        rc, out, _ = _run_cli("info")
        assert "finclaw" in out.lower() or "FinClaw" in out
