"""
UX Bug Fix Tests
================
Tests for the 4 UX issues found during real-user testing:
1. Compare strategy name aliases
2. Unknown backtest strategy warning
3. Paper trading rejection detail messages
4. History timestamp formatting
"""

import io
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.paper.engine import (
    PaperTradingEngine,
    Order,
    OrderSide,
    OrderStatus,
)
from src.cli.main import main, build_parser, _run_strategy_compare


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


# ══════════════════════════════════════════════════════════════════
# Bug 1: Compare strategy names should accept backtest names
# ══════════════════════════════════════════════════════════════════

class TestCompareStrategyAliases:
    """compare command should accept both its own names AND backtest strategy names."""

    @pytest.fixture
    def mock_data(self):
        df = _make_mock_df(days=252)
        close = np.array(df["Close"].tolist(), dtype=np.float64)
        prices = df["Close"].tolist()
        return df, close, prices

    def test_backtest_name_sma_cross_works(self, mock_data):
        """sma_cross (backtest name) should work in compare, mapping to trend_following."""
        df, close, prices = mock_data
        result = _run_strategy_compare("sma_cross", df, close, prices)
        assert result is not None
        assert result["name"] == "sma_cross"
        assert "return" in result
        assert "trades" in result

    def test_backtest_name_rsi_works(self, mock_data):
        """rsi (backtest name) should work in compare, mapping to mean_reversion."""
        df, close, prices = mock_data
        result = _run_strategy_compare("rsi", df, close, prices)
        assert result is not None
        assert result["name"] == "rsi"

    def test_backtest_name_macd_works(self, mock_data):
        """macd (backtest name) should work in compare, mapping to macd_cross."""
        df, close, prices = mock_data
        result = _run_strategy_compare("macd", df, close, prices)
        assert result is not None
        assert result["name"] == "macd"

    def test_backtest_name_bollinger_works(self, mock_data):
        """bollinger (backtest name) should work in compare."""
        df, close, prices = mock_data
        result = _run_strategy_compare("bollinger", df, close, prices)
        assert result is not None
        assert result["name"] == "bollinger"

    def test_original_names_still_work(self, mock_data):
        """Original compare names (momentum, mean_reversion, etc.) should still work."""
        df, close, prices = mock_data
        for name in ["momentum", "mean_reversion", "trend_following", "macd_cross", "buy_hold"]:
            result = _run_strategy_compare(name, df, close, prices)
            assert result is not None, f"Strategy '{name}' returned None"
            assert result["name"] == name

    def test_unknown_strategy_returns_none(self, mock_data):
        """Unknown strategy should return None and print error."""
        df, close, prices = mock_data
        result = _run_strategy_compare("nonexistent_strategy", df, close, prices)
        assert result is None

    @patch("src.cli.main._fetch_data")
    def test_compare_cli_with_backtest_names(self, mock_fetch):
        """CLI compare command should work with backtest strategy names."""
        mock_fetch.return_value = _make_mock_df(days=252)
        rc, out, _ = _run_cli(
            "compare", "--strategies", "sma_cross", "macd", "--data", "AAPL", "--period", "1y"
        )
        # Should not say "Unknown strategy"
        assert "Unknown strategy: sma_cross" not in out
        assert "Unknown strategy: macd" not in out


# ══════════════════════════════════════════════════════════════════
# Bug 2: Nonexistent backtest strategy should warn
# ══════════════════════════════════════════════════════════════════

class TestBacktestUnknownStrategyWarning:
    """backtest with unknown strategy should warn user, not silently use default."""

    @patch("src.cli.main._fetch_data")
    def test_unknown_strategy_prints_warning(self, mock_fetch):
        """Unknown strategy should print WARNING with available strategies."""
        mock_fetch.return_value = _make_mock_df(days=252)
        rc, out, _ = _run_cli(
            "backtest", "--strategy", "nonexistent", "--tickers", "AAPL"
        )
        assert "WARNING" in out
        assert "nonexistent" in out
        assert "Available:" in out

    @patch("src.cli.main._fetch_data")
    def test_unknown_strategy_lists_available(self, mock_fetch):
        """Warning should list available strategy names including aliases."""
        mock_fetch.return_value = _make_mock_df(days=252)
        rc, out, _ = _run_cli(
            "backtest", "--strategy", "foo_bar", "--tickers", "AAPL"
        )
        assert "WARNING" in out
        # Should include both standard (macd, bollinger, momentum) and aliases (sma_cross, rsi)
        assert "macd" in out
        assert "momentum" in out
        assert "sma_cross" in out

    @patch("src.cli.main._fetch_data")
    def test_known_strategy_no_warning(self, mock_fetch):
        """Known strategies should NOT print any warning."""
        mock_fetch.return_value = _make_mock_df(days=252)
        rc, out, _ = _run_cli(
            "backtest", "--strategy", "macd", "--tickers", "AAPL"
        )
        assert "WARNING" not in out

    @patch("src.cli.main._fetch_data")
    def test_alias_strategy_no_warning(self, mock_fetch):
        """Alias strategies (sma_cross, rsi) should NOT print any warning."""
        mock_fetch.return_value = _make_mock_df(days=252)
        rc, out, _ = _run_cli(
            "backtest", "--strategy", "sma_cross", "--tickers", "AAPL"
        )
        assert "WARNING" not in out


# ══════════════════════════════════════════════════════════════════
# Bug 3: Paper trading rejection messages should be detailed
# ══════════════════════════════════════════════════════════════════

class TestPaperTradingRejectionMessages:
    """Paper trading rejections should explain why the order was rejected."""

    @pytest.fixture
    def engine(self):
        eng = PaperTradingEngine(initial_balance=100_000)
        eng.set_price("AAPL", 190.0)
        eng.set_price("GOOGL", 170.0)
        return eng

    def test_sell_no_position_gives_reason(self, engine):
        """Selling a stock you don't hold should say 'No position in SYMBOL'."""
        order = engine.sell("GOOGL", 10)
        assert order.status == OrderStatus.REJECTED
        assert "No position in GOOGL" in order.reject_reason

    def test_buy_negative_quantity_gives_reason(self, engine):
        """Buying negative quantity should say 'must be positive'."""
        order = engine.buy("AAPL", -5)
        assert order.status == OrderStatus.REJECTED
        assert "must be positive" in order.reject_reason
        assert "-5" in order.reject_reason

    def test_sell_negative_quantity_gives_reason(self, engine):
        """Selling negative quantity should say 'must be positive'."""
        order = engine.sell("AAPL", -5)
        assert order.status == OrderStatus.REJECTED
        assert "must be positive" in order.reject_reason

    def test_buy_insufficient_funds_gives_amounts(self, engine):
        """Insufficient funds should show needed vs available amounts."""
        order = engine.buy("AAPL", 1000)  # 1000 * 190 = 190,000 > 100,000
        assert order.status == OrderStatus.REJECTED
        assert "Insufficient funds" in order.reject_reason
        assert "190,000" in order.reject_reason       # need
        assert "100,000" in order.reject_reason       # have

    def test_sell_insufficient_shares_gives_amounts(self, engine):
        """Selling more than held should show how many you have vs want."""
        engine.buy("AAPL", 10)
        order = engine.sell("AAPL", 20)
        assert order.status == OrderStatus.REJECTED
        assert "Insufficient shares" in order.reject_reason
        assert "have 10" in order.reject_reason or "10" in order.reject_reason
        assert "want 20" in order.reject_reason or "20" in order.reject_reason

    def test_order_to_dict_includes_reject_reason(self, engine):
        """Order.to_dict() should include reject_reason field."""
        order = engine.sell("GOOGL", 10)
        d = order.to_dict()
        assert "reject_reason" in d
        assert "No position" in d["reject_reason"]


# ══════════════════════════════════════════════════════════════════
# Bug 4: History should show formatted dates, not raw timestamps
# ══════════════════════════════════════════════════════════════════

class TestHistoryTimestampFormatting:
    """history command should display human-readable dates, not raw timestamps."""

    @patch("src.exchanges.registry.ExchangeRegistry.get")
    def test_history_formats_timestamps(self, mock_get):
        """Timestamps should be formatted as YYYY-MM-DD HH:MM, not raw numbers."""
        adapter = MagicMock()
        # Simulate candles with millisecond timestamps
        adapter.get_ohlcv.return_value = [
            {
                "timestamp": 1771511400000,  # ms timestamp
                "open": 190.0, "high": 195.0, "low": 189.0, "close": 192.0, "volume": 1000000,
            },
            {
                "timestamp": 1771597800000,
                "open": 192.0, "high": 196.0, "low": 191.0, "close": 195.0, "volume": 1100000,
            },
        ]
        mock_get.return_value = adapter

        rc, out, _ = _run_cli("history", "AAPL")

        # Should NOT contain raw timestamps
        assert "1771511400000" not in out
        assert "1771597800000" not in out

        # Should contain formatted dates (YYYY-MM-DD)
        assert "-" in out  # date separator
        assert ":" in out  # time separator

    @patch("src.exchanges.registry.ExchangeRegistry.get")
    def test_history_handles_second_timestamps(self, mock_get):
        """Timestamps already in seconds should also be formatted correctly."""
        adapter = MagicMock()
        adapter.get_ohlcv.return_value = [
            {
                "timestamp": 1700000000,  # seconds timestamp (Nov 2023)
                "open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 500000,
            },
        ]
        mock_get.return_value = adapter

        rc, out, _ = _run_cli("history", "AAPL")

        # Should NOT contain raw timestamp
        assert "1700000000" not in out
        # Should contain a date in 2023
        assert "2023" in out
