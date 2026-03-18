"""
Tests for v5.1 bug fixes:
  Bug 1: quote Change shows +0.00
  Bug 2: sentiment timezone error
  Bug 3: watchlist quotes shows None
  Bug 4: Version mismatch
  Bug 5: Argument inconsistency (predict --ticker, info positional)
"""

import io
import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Helpers ──────────────────────────────────────────────────────

def _run_cli(*argv, expect_rc=None):
    """Run CLI with given argv, capture stdout/stderr, return (rc, stdout, stderr)."""
    from src.cli.main import main
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
        assert rc == expect_rc, f"Expected rc={expect_rc}, got {rc}. stdout={stdout_str!r}, stderr={stderr_str!r}"
    return rc, stdout_str, stderr_str


# ── Bug 1: quote Change should include real change values ────────

class TestBug1QuoteChange:
    """Yahoo adapter get_ticker must return change and change_pct keys."""

    def test_get_ticker_returns_change_keys(self):
        """get_ticker dict must contain 'change' and 'change_pct' keys."""
        from src.exchanges.yahoo_finance import YahooFinanceAdapter
        adapter = YahooFinanceAdapter()

        # Mock the HTTP client response with realistic Yahoo chart API data
        mock_response = {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "AAPL",
                        "regularMarketPrice": 195.50,
                        "chartPreviousClose": 192.00,
                        "regularMarketVolume": 50000000,
                        "regularMarketTime": 1700000000,
                    },
                    "timestamp": [1700000000],
                    "indicators": {"quote": [{"open": [195.0], "high": [196.0], "low": [194.0], "close": [195.5], "volume": [50000000]}]},
                }]
            }
        }
        with patch.object(adapter.client, "get", return_value=mock_response):
            result = adapter.get_ticker("AAPL")

        assert "change" in result, "get_ticker must return 'change' key"
        assert "change_pct" in result, "get_ticker must return 'change_pct' key"
        assert abs(result["change"] - 3.50) < 0.01, f"Expected change ~3.50, got {result['change']}"
        expected_pct = 3.50 / 192.00 * 100
        assert abs(result["change_pct"] - expected_pct) < 0.01, f"Expected change_pct ~{expected_pct:.4f}, got {result['change_pct']}"

    def test_get_ticker_change_not_zero(self):
        """When price differs from previous close, change must not be zero."""
        from src.exchanges.yahoo_finance import YahooFinanceAdapter
        adapter = YahooFinanceAdapter()

        mock_response = {
            "chart": {
                "result": [{
                    "meta": {
                        "symbol": "MSFT",
                        "regularMarketPrice": 410.00,
                        "chartPreviousClose": 405.00,
                        "regularMarketVolume": 30000000,
                        "regularMarketTime": 1700000000,
                    },
                    "timestamp": [1700000000],
                    "indicators": {"quote": [{"open": [406.0], "high": [411.0], "low": [405.0], "close": [410.0], "volume": [30000000]}]},
                }]
            }
        }
        with patch.object(adapter.client, "get", return_value=mock_response):
            result = adapter.get_ticker("MSFT")

        assert result["change"] != 0, "Change should not be zero when price differs from prev close"
        assert result["change_pct"] != 0, "Change pct should not be zero when price differs"


# ── Bug 2: sentiment timezone error ─────────────────────────────

class TestBug2SentimentTimezone:
    """_parse_date must return timezone-aware datetimes to prevent comparison errors."""

    def test_parse_date_always_returns_aware(self):
        """All parsed dates must be timezone-aware (not naive)."""
        from src.sentiment.news import _parse_date

        # Format with explicit timezone
        dt1 = _parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert dt1 is not None
        assert dt1.tzinfo is not None, "Date with %z should be tz-aware"

        # Format with "GMT" (no %z) — was previously naive
        dt2 = _parse_date("Mon, 01 Jan 2024 12:00:00 GMT")
        assert dt2 is not None
        assert dt2.tzinfo is not None, "Date with GMT should be tz-aware"

        # ISO format without timezone — was previously naive
        dt3 = _parse_date("2024-01-01 12:00:00")
        assert dt3 is not None
        assert dt3.tzinfo is not None, "Naive date should be promoted to tz-aware"

        # ISO with Z — was previously naive
        dt4 = _parse_date("2024-01-01T12:00:00Z")
        assert dt4 is not None
        assert dt4.tzinfo is not None, "ISO Z date should be tz-aware"

    def test_mixed_dates_sortable(self):
        """Sorting a mix of date formats must not raise TypeError."""
        from src.sentiment.news import _parse_date

        dates = [
            "Mon, 01 Jan 2024 12:00:00 +0000",  # tz-aware via %z
            "Tue, 02 Jan 2024 10:00:00 GMT",     # was naive
            "2024-01-03 08:00:00",                # was naive
            "2024-01-04T06:00:00Z",               # was naive
        ]
        parsed = [_parse_date(d) for d in dates]
        # This must not raise: can't compare offset-naive and offset-aware datetimes
        sorted_dates = sorted(parsed, reverse=True)
        assert len(sorted_dates) == 4

    def test_none_date_returns_none(self):
        """Empty or None input should return None."""
        from src.sentiment.news import _parse_date
        assert _parse_date("") is None
        assert _parse_date(None) is None

    def test_sort_key_with_fallback(self):
        """The sort_key fallback (datetime.min with utc) must be comparable with parsed dates."""
        from src.sentiment.news import _parse_date

        dt = _parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        fallback = datetime.min.replace(tzinfo=timezone.utc)
        # Must not raise
        assert dt > fallback


# ── Bug 3: watchlist quotes shows None ──────────────────────────

class TestBug3WatchlistQuotes:
    """WatchlistManager must use exchange registry to fetch real prices."""

    def test_watchlist_quotes_with_registry(self, tmp_path):
        """When exchange_registry is provided, quotes should have real prices."""
        from src.screener.watchlist import WatchlistManager

        # Create a mock registry
        mock_registry = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.get_ticker.return_value = {
            "symbol": "AAPL",
            "last": 195.50,
            "bid": 195.40,
            "ask": 195.60,
            "volume": 50000000,
        }
        mock_registry.get.return_value = mock_adapter

        wm = WatchlistManager(path=str(tmp_path / "wl.json"), exchange_registry=mock_registry)
        wm.create("test", ["AAPL"])
        quotes = wm.get_quotes("test")

        assert len(quotes) == 1
        assert quotes[0].get("last") == 195.50, f"Expected price 195.50, got {quotes[0].get('last')}"
        assert quotes[0].get("last") is not None, "Price should not be None"

    def test_watchlist_quotes_without_registry(self, tmp_path):
        """Without registry, quotes should still return symbol but last=None."""
        from src.screener.watchlist import WatchlistManager

        wm = WatchlistManager(path=str(tmp_path / "wl.json"))
        wm.create("test", ["AAPL"])
        quotes = wm.get_quotes("test")

        assert len(quotes) == 1
        assert quotes[0]["symbol"] == "AAPL"
        # Without registry, still returns dict but with None last
        assert quotes[0].get("last") is None

    def test_cmd_watchlist_uses_registry(self):
        """The CLI cmd_watchlist function should pass ExchangeRegistry."""
        import inspect
        from src.cli.main import cmd_watchlist
        source = inspect.getsource(cmd_watchlist)
        assert "exchange_registry" in source, "cmd_watchlist must pass exchange_registry to WatchlistManager"


# ── Bug 4: Version mismatch ─────────────────────────────────────

class TestBug4Version:
    """CLI --version must show pyproject.toml version, not hardcoded 0.1.0."""

    def test_version_not_0_1_0(self):
        """CLI version must not be the old hardcoded 0.1.0."""
        rc, stdout, stderr = _run_cli("--version")
        output = stdout + stderr
        assert "0.1.0" not in output, f"Version should not be 0.1.0, got: {output}"

    def test_version_matches_pyproject(self):
        """CLI version must match pyproject.toml."""
        import re
        from pathlib import Path

        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        assert m, "Could not find version in pyproject.toml"
        expected_version = m.group(1)

        rc, stdout, stderr = _run_cli("--version")
        output = stdout + stderr
        assert expected_version in output, f"Expected version {expected_version} in output, got: {output}"

    def test_get_version_function(self):
        """_get_version must return a semver-like string."""
        from src.cli.main import _get_version
        version = _get_version()
        assert version != "0.0.0", "Version should be resolved"
        parts = version.split(".")
        assert len(parts) >= 2, f"Version should be semver-like, got: {version}"


# ── Bug 5: Argument inconsistency ───────────────────────────────

class TestBug5ArgumentConsistency:
    """predict run --ticker and info <ticker> must work."""

    def test_predict_run_accepts_ticker(self):
        """finclaw predict run --ticker AAPL should work (alias for --symbol)."""
        rc, stdout, stderr = _run_cli("predict", "run", "--ticker", "AAPL")
        output = stdout + stderr
        assert "AAPL" in output, f"Expected AAPL in output, got: {output}"
        assert "ERROR" not in output, f"Should not error with --ticker, got: {output}"

    def test_predict_run_still_accepts_symbol(self):
        """finclaw predict run --symbol AAPL should still work."""
        rc, stdout, stderr = _run_cli("predict", "run", "--symbol", "AAPL")
        output = stdout + stderr
        assert "AAPL" in output, f"Expected AAPL in output, got: {output}"

    def test_predict_run_no_symbol_errors(self):
        """finclaw predict run without symbol or ticker should show error."""
        rc, stdout, stderr = _run_cli("predict", "run")
        output = stdout + stderr
        assert "ERROR" in output or "required" in output.lower(), f"Should error without symbol/ticker, got: {output}"

    def test_info_accepts_positional_ticker(self):
        """finclaw info AAPL should work with a positional ticker."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["info", "AAPL"])
        assert args.ticker == "AAPL", f"Expected ticker='AAPL', got {args.ticker}"

    def test_info_without_ticker_shows_system_info(self):
        """finclaw info (no ticker) should show system info."""
        rc, stdout, stderr = _run_cli("info")
        output = stdout + stderr
        assert "FinClaw" in output, f"Expected FinClaw in output, got: {output}"

    def test_info_with_ticker_shows_price(self):
        """finclaw info AAPL should show price info."""
        import numpy as np

        mock_df = pd.DataFrame({
            "Open": [148.0, 149.0, 150.0],
            "High": [149.0, 150.0, 151.0],
            "Low": [147.0, 148.0, 149.0],
            "Close": [149.0, 150.0, 150.5],
            "Volume": [1000000, 1100000, 1200000],
        }, index=pd.date_range("2024-01-01", periods=3, freq="B"))

        with patch("src.cli.main._fetch_data", return_value=mock_df):
            rc, stdout, stderr = _run_cli("info", "AAPL")
        output = stdout + stderr
        assert "AAPL" in output, f"Expected AAPL in output, got: {output}"
        assert "Price" in output, f"Expected Price in output, got: {output}"
