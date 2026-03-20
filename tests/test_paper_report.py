"""
Tests for Paper Trading Report Framework

Tests the PortfolioManager, daily report generation, summary generation,
and CLI integration with mock data (no live market data required).
"""

import json
import os
import shutil
import tempfile
from datetime import date

import pytest

from src.paper_report.portfolio_manager import PortfolioManager


@pytest.fixture
def tmp_data_dir():
    """Create a temporary data directory for testing."""
    d = tempfile.mkdtemp(prefix="finclaw_paper_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def manager(tmp_data_dir):
    """Create a PortfolioManager with temp directory."""
    return PortfolioManager(data_dir=tmp_data_dir)


class TestPortfolioInit:
    """Tests for portfolio initialization."""

    def test_init_creates_us_portfolio(self, manager, tmp_data_dir):
        result = manager.init_portfolios()
        assert "us" in result
        assert result["us"]["initial_capital"] == 100_000.0
        assert result["us"]["cash"] == 100_000.0
        assert result["us"]["market"] == "US"
        assert result["us"]["currency"] == "USD"
        assert os.path.exists(os.path.join(tmp_data_dir, "us-portfolio.json"))

    def test_init_creates_cn_portfolio(self, manager, tmp_data_dir):
        result = manager.init_portfolios()
        assert "cn" in result
        assert result["cn"]["initial_capital"] == 1_000_000.0
        assert result["cn"]["cash"] == 1_000_000.0
        assert result["cn"]["market"] == "CN"
        assert result["cn"]["currency"] == "CNY"
        assert os.path.exists(os.path.join(tmp_data_dir, "cn-portfolio.json"))

    def test_init_custom_capital(self, manager):
        result = manager.init_portfolios(us_capital=50_000, cn_capital=500_000)
        assert result["us"]["initial_capital"] == 50_000.0
        assert result["cn"]["initial_capital"] == 500_000.0

    def test_init_custom_start_date(self, manager):
        result = manager.init_portfolios(start_date="2026-01-15")
        assert result["us"]["start_date"] == "2026-01-15"
        assert result["cn"]["start_date"] == "2026-01-15"

    def test_init_creates_directories(self, manager, tmp_data_dir):
        manager.init_portfolios()
        assert os.path.isdir(tmp_data_dir)
        assert os.path.isdir(os.path.join(tmp_data_dir, "reports"))

    def test_init_creates_summary(self, manager, tmp_data_dir):
        manager.init_portfolios()
        summary_path = os.path.join(tmp_data_dir, "summary.md")
        assert os.path.exists(summary_path)
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "FinClaw Paper Trading Performance" in content

    def test_init_with_initial_snapshot(self, manager):
        result = manager.init_portfolios(start_date="2026-03-20")
        assert len(result["us"]["daily_snapshots"]) == 1
        snap = result["us"]["daily_snapshots"][0]
        assert snap["date"] == "2026-03-20"
        assert snap["total_value"] == 100_000.0
        assert snap["positions_value"] == 0.0

    def test_init_empty_positions(self, manager):
        result = manager.init_portfolios()
        assert result["us"]["positions"] == []
        assert result["cn"]["positions"] == []
        assert result["us"]["trade_history"] == []
        assert result["cn"]["trade_history"] == []


class TestPortfolioLoad:
    """Tests for loading and saving portfolios."""

    def test_load_us_portfolio(self, manager):
        manager.init_portfolios()
        loaded = manager.load_portfolio("US")
        assert loaded is not None
        assert loaded["market"] == "US"
        assert loaded["initial_capital"] == 100_000.0

    def test_load_cn_portfolio(self, manager):
        manager.init_portfolios()
        loaded = manager.load_portfolio("CN")
        assert loaded is not None
        assert loaded["market"] == "CN"
        assert loaded["initial_capital"] == 1_000_000.0

    def test_load_nonexistent_returns_none(self, manager):
        assert manager.load_portfolio("US") is None
        assert manager.load_portfolio("CN") is None

    def test_load_case_insensitive(self, manager):
        manager.init_portfolios()
        assert manager.load_portfolio("us") is not None
        assert manager.load_portfolio("Us") is not None

    def test_save_and_reload(self, manager):
        manager.init_portfolios()
        portfolio = manager.load_portfolio("US")
        portfolio["cash"] = 95_000.0
        portfolio["positions"].append({
            "ticker": "AAPL",
            "shares": 50,
            "avg_cost": 100.0,
            "current_price": 105.0,
        })
        manager.save_portfolio("US", portfolio)

        reloaded = manager.load_portfolio("US")
        assert reloaded["cash"] == 95_000.0
        assert len(reloaded["positions"]) == 1
        assert reloaded["positions"][0]["ticker"] == "AAPL"


class TestPortfolioValue:
    """Tests for portfolio value calculations."""

    def test_value_cash_only(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        assert manager.get_portfolio_value(us) == 100_000.0

    def test_value_with_positions(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["cash"] = 90_000.0
        us["positions"] = [
            {"ticker": "AAPL", "shares": 100, "avg_cost": 100.0, "current_price": 105.0},
        ]
        assert manager.get_portfolio_value(us) == 90_000.0 + 100 * 105.0

    def test_value_with_multiple_positions(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["cash"] = 50_000.0
        us["positions"] = [
            {"ticker": "AAPL", "shares": 100, "avg_cost": 100.0, "current_price": 110.0},
            {"ticker": "MSFT", "shares": 50, "avg_cost": 200.0, "current_price": 220.0},
        ]
        expected = 50_000 + 100 * 110 + 50 * 220
        assert manager.get_portfolio_value(us) == expected

    def test_return_zero_at_init(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        assert manager.get_portfolio_return(us) == 0.0

    def test_return_positive(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["cash"] = 105_000.0  # 5% gain all in cash
        ret = manager.get_portfolio_return(us)
        assert abs(ret - 5.0) < 0.01

    def test_return_negative(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["cash"] = 95_000.0  # 5% loss
        ret = manager.get_portfolio_return(us)
        assert abs(ret - (-5.0)) < 0.01


class TestDailySnapshot:
    """Tests for daily snapshot functionality."""

    def test_add_snapshot(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        snap = manager.add_daily_snapshot(us, "2026-03-21")
        assert snap["date"] == "2026-03-21"
        assert snap["total_value"] == 100_000.0
        assert len(us["daily_snapshots"]) == 2  # init + new

    def test_snapshot_with_positions(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["cash"] = 90_000.0
        us["positions"] = [
            {"ticker": "AAPL", "shares": 100, "current_price": 105.0},
        ]
        snap = manager.add_daily_snapshot(us, "2026-03-21")
        assert snap["total_value"] == 90_000.0 + 100 * 105.0
        assert snap["positions_value"] == 100 * 105.0
        assert snap["cash"] == 90_000.0


class TestDailyReport:
    """Tests for daily report generation."""

    def test_generate_report_with_init(self, manager, tmp_data_dir):
        manager.init_portfolios(start_date="2026-03-20")
        report = manager.generate_daily_report("2026-03-20")
        assert "Paper Trading Daily Report" in report
        assert "2026-03-20" in report
        assert "US Stocks" in report
        assert "A-Shares" in report

    def test_report_file_created(self, manager, tmp_data_dir):
        manager.init_portfolios()
        manager.generate_daily_report("2026-03-20")
        report_path = os.path.join(tmp_data_dir, "reports", "2026-03-20.md")
        assert os.path.exists(report_path)

    def test_report_no_positions_disclosure(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        us["positions"] = [
            {"ticker": "AAPL", "shares": 100, "avg_cost": 100.0, "current_price": 105.0},
        ]
        manager.save_portfolio("US", us)
        report = manager.generate_daily_report("2026-03-20")
        # Should NOT contain specific ticker names in the report
        assert "AAPL" not in report

    def test_report_without_portfolios(self, manager):
        report = manager.generate_daily_report("2026-03-20")
        assert "Error" in report
        assert "No portfolios found" in report

    def test_report_contains_strategy_info(self, manager):
        manager.init_portfolios()
        report = manager.generate_daily_report("2026-03-20")
        assert "momentum" in report.lower() or "RSI" in report


class TestSummary:
    """Tests for summary.md generation."""

    def test_summary_contains_performance_table(self, manager):
        manager.init_portfolios(start_date="2026-03-20")
        summary = manager.generate_summary()
        assert "Current Performance" in summary
        assert "US Stocks" in summary
        assert "A-Shares" in summary
        assert "$100,000" in summary
        assert "¥1,000,000" in summary

    def test_summary_contains_strategy(self, manager):
        manager.init_portfolios()
        summary = manager.generate_summary()
        assert "Multi-factor momentum" in summary
        assert "FinClaw AI Scanner" in summary

    def test_summary_contains_weekly_returns_header(self, manager):
        manager.init_portfolios()
        summary = manager.generate_summary()
        assert "Weekly Returns" in summary

    def test_summary_contains_disclaimer(self, manager):
        manager.init_portfolios()
        summary = manager.generate_summary()
        assert "Past performance does not guarantee" in summary
        assert "Individual positions are not disclosed" in summary

    def test_summary_file_written(self, manager, tmp_data_dir):
        manager.init_portfolios()
        manager.generate_summary()
        summary_path = os.path.join(tmp_data_dir, "summary.md")
        assert os.path.exists(summary_path)

    def test_summary_initial_return_zero(self, manager):
        manager.init_portfolios()
        summary = manager.generate_summary()
        assert "+0.0%" in summary


class TestWeeklyReturns:
    """Tests for weekly return calculation."""

    def test_no_weeks_with_few_snapshots(self, manager):
        manager.init_portfolios()
        us = manager.load_portfolio("US")
        weeks = manager._calculate_weekly_returns(us, None)
        assert len(weeks) == 0 or all(w["us"] == "-" or "%" in w["us"] for w in weeks)

    def test_group_snapshots_by_week(self, manager):
        snapshots = [
            {"date": "2026-03-16", "total_value": 100_000},
            {"date": "2026-03-17", "total_value": 100_500},
            {"date": "2026-03-18", "total_value": 101_000},
        ]
        result = manager._group_snapshots_by_week(snapshots, 100_000)
        assert isinstance(result, dict)

    def test_empty_snapshots(self, manager):
        result = manager._group_snapshots_by_week([], 100_000)
        assert result == {}


class TestCLIIntegration:
    """Tests for CLI paper-report command integration."""

    def test_parser_has_paper_report(self):
        from src.cli.main import build_parser
        parser = build_parser()
        # Verify paper-report is a valid subcommand
        args = parser.parse_args(["paper-report", "--init"])
        assert args.command == "paper-report"
        assert args.init is True

    def test_parser_paper_report_date(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["paper-report", "--date", "2026-03-20"])
        assert args.date == "2026-03-20"

    def test_parser_paper_report_skip_fetch(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["paper-report", "--skip-fetch"])
        assert args.skip_fetch is True

    def test_parser_paper_report_data_dir(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["paper-report", "--data-dir", "/tmp/test"])
        assert args.data_dir == "/tmp/test"


class TestDailyScript:
    """Tests for the daily script (scripts/paper_trading_daily.py)."""

    def test_daily_run_without_init(self, manager, capsys):
        from scripts.paper_trading_daily import daily_run
        result = daily_run(manager, report_date="2026-03-20", skip_fetch=True)
        assert result == ""  # no portfolios

    def test_daily_run_with_init(self, manager, tmp_data_dir):
        from scripts.paper_trading_daily import daily_run
        manager.init_portfolios(start_date="2026-03-20")
        report = daily_run(manager, report_date="2026-03-20", skip_fetch=True)
        assert "Paper Trading Daily Report" in report
        # Check files were created
        assert os.path.exists(os.path.join(tmp_data_dir, "reports", "2026-03-20.md"))
        assert os.path.exists(os.path.join(tmp_data_dir, "summary.md"))

    def test_daily_run_updates_snapshots(self, manager):
        manager.init_portfolios(start_date="2026-03-20")
        from scripts.paper_trading_daily import daily_run
        daily_run(manager, report_date="2026-03-21", skip_fetch=True)

        us = manager.load_portfolio("US")
        # Should have 2 snapshots: init + daily run
        assert len(us["daily_snapshots"]) == 2
        assert us["daily_snapshots"][-1]["date"] == "2026-03-21"

    def test_fetch_us_prices_graceful_failure(self):
        """fetch_us_prices should return empty dict if yfinance unavailable or fails."""
        from scripts.paper_trading_daily import fetch_us_prices
        # Even if yfinance is installed, requesting garbage ticker should be graceful
        result = fetch_us_prices(["ZZZZNOTREAL12345"])
        assert isinstance(result, dict)

    def test_fetch_cn_signals_graceful_failure(self):
        """fetch_cn_signals should return empty list on failure."""
        from scripts.paper_trading_daily import fetch_cn_signals
        # This should not crash even if cn_scanner can't fetch data
        result = fetch_cn_signals()
        assert isinstance(result, list)


class TestPortfolioJsonFormat:
    """Tests that verify the JSON format of portfolio files."""

    def test_us_json_has_required_fields(self, manager, tmp_data_dir):
        manager.init_portfolios()
        with open(os.path.join(tmp_data_dir, "us-portfolio.json"), "r") as f:
            data = json.load(f)
        required = ["market", "currency", "currency_symbol", "start_date",
                     "initial_capital", "cash", "positions", "trade_history",
                     "daily_snapshots"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_cn_json_has_required_fields(self, manager, tmp_data_dir):
        manager.init_portfolios()
        with open(os.path.join(tmp_data_dir, "cn-portfolio.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["currency_symbol"] == "\u00a5"  # ¥
        assert data["currency"] == "CNY"

    def test_json_is_valid_utf8(self, manager, tmp_data_dir):
        manager.init_portfolios()
        for fname in ["us-portfolio.json", "cn-portfolio.json"]:
            path = os.path.join(tmp_data_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)  # should not raise
            assert isinstance(data, dict)
