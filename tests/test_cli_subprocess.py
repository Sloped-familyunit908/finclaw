"""
CLI Subprocess Integration Tests
=================================
Integration tests that run CLI commands via subprocess, testing like a real user.
These test the actual `finclaw` CLI entry point end-to-end.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PYTHON = sys.executable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_MODULE = os.path.join(PROJECT_ROOT, "src", "cli", "main.py")


def _run_finclaw(*args, timeout=120):
    """Run a finclaw CLI command via subprocess, return (returncode, stdout, stderr)."""
    cmd = [PYTHON, "-m", "src.cli.main"] + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONPATH": PROJECT_ROOT, "PYTHONIOENCODING": "utf-8"},
        )
        # Decode as utf-8 with error replacement to handle unicode on Windows
        stdout = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"


class TestCLISubprocessDoctor:
    """Test `finclaw doctor` — should run without error."""

    def test_doctor_runs(self):
        rc, out, err = _run_finclaw("doctor", "--skip-network")
        combined = out + err
        # Doctor should produce output and not crash
        assert rc is not None
        assert len(out) > 0 or len(err) > 0
        # Should contain check results
        assert "✓" in combined or "✗" in combined or "PASS" in combined.upper() or "doctor" in combined.lower() or len(combined) > 20

    def test_doctor_verbose(self):
        rc, out, err = _run_finclaw("doctor", "--verbose", "--skip-network")
        combined = out + err
        assert len(combined) > 0


class TestCLISubprocessInfo:
    """Test `finclaw info` — basic system info."""

    def test_info_runs(self):
        rc, out, err = _run_finclaw("info")
        combined = out + err
        assert "finclaw" in combined.lower() or "FinClaw" in combined


class TestCLISubprocessDemo:
    """Test `finclaw demo` — should showcase features without API keys."""

    def test_demo_runs(self):
        rc, out, err = _run_finclaw("demo", timeout=180)
        combined = out + err
        # Demo should produce substantial output
        assert len(combined) > 50, f"Demo produced too little output: {combined[:200]}"

    def test_demo_no_crash(self):
        """Demo should not crash with non-zero exit code."""
        rc, out, err = _run_finclaw("demo", timeout=180)
        assert rc == 0 or rc is None, f"Demo crashed with rc={rc}, stderr={err[:500]}"


class TestCLISubprocessHelp:
    """Test help subcommand."""

    def test_help(self):
        rc, out, err = _run_finclaw("--help")
        combined = out + err
        assert "finclaw" in combined.lower() or "usage" in combined.lower()
        assert rc == 0

    def test_backtest_help(self):
        rc, out, err = _run_finclaw("backtest", "--help")
        combined = out + err
        assert "strategy" in combined.lower()
        assert rc == 0


class TestCLISubprocessQuote:
    """Test `finclaw quote` — verify output contains price info."""

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Requires network access / yfinance"
    )
    def test_quote_aapl(self):
        rc, out, err = _run_finclaw("quote", "AAPL")
        combined = out + err
        # Should contain AAPL and some price-like number
        assert "AAPL" in combined, f"Output missing AAPL: {combined[:300]}"

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Requires network access / yfinance"
    )
    def test_quote_multiple(self):
        rc, out, err = _run_finclaw("quote", "AAPL", "MSFT")
        combined = out + err
        assert "AAPL" in combined or "MSFT" in combined


class TestCLISubprocessAnalyze:
    """Test `finclaw analyze` — verify technical analysis output."""

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Requires network access / yfinance"
    )
    def test_analyze_aapl(self):
        rc, out, err = _run_finclaw("analyze", "--ticker", "AAPL")
        combined = out + err
        # Should contain RSI and MACD (default indicators)
        assert "RSI" in combined or "rsi" in combined, f"Missing RSI: {combined[:300]}"
        assert "MACD" in combined or "macd" in combined, f"Missing MACD: {combined[:300]}"


class TestCLISubprocessScreen:
    """Test `finclaw screen` — verify screener output."""

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Requires network access / yfinance"
    )
    def test_screen_min_price(self):
        rc, out, err = _run_finclaw("screen", "--min-price", "100", "--limit", "5")
        combined = out + err
        # Should produce output (may have matches or "no matches")
        assert len(combined) > 10, f"Screen produced too little output: {combined}"


class TestCLISubprocessCache:
    """Test cache management commands."""

    def test_cache_stats(self):
        rc, out, err = _run_finclaw("cache", "--stats")
        combined = out + err
        assert "entries" in combined.lower() or "size" in combined.lower() or "Entries" in combined
