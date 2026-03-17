"""Tests for new features: multi-quote, export, compare, telegram bot framework."""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMultiQuote:
    """Test multi-symbol quote support."""

    def test_quote_parser_accepts_multiple_symbols(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["quote", "AAPL", "TSLA", "MSFT"])
        assert args.symbol == ["AAPL", "TSLA", "MSFT"]
        assert args.command == "quote"

    def test_quote_parser_single_symbol(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["quote", "AAPL"])
        assert args.symbol == ["AAPL"]


class TestExport:
    """Test data export command."""

    def test_export_parser(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["export", "--ticker", "AAPL", "--period", "1y", "--format", "csv"])
        assert args.ticker == "AAPL"
        assert args.period == "1y"
        assert args.format == "csv"

    def test_export_parser_defaults(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["export", "--ticker", "MSFT"])
        assert args.period == "1y"
        assert args.format == "csv"

    def test_exporter_csv(self):
        from src.export.exporter import DataExporter
        exporter = DataExporter()
        data = [
            {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000},
            {"date": "2024-01-02", "open": 103, "high": 107, "low": 102, "close": 106, "volume": 1200},
        ]
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            path = f.name
        try:
            exporter.to_csv(data, path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "date" in content
            assert "2024-01-01" in content
        finally:
            os.unlink(path)

    def test_exporter_json(self):
        from src.export.exporter import DataExporter
        exporter = DataExporter()
        data = [{"a": 1, "b": 2}]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            exporter.to_json(data, path)
            with open(path) as f:
                loaded = json.load(f)
            assert loaded == data
        finally:
            os.unlink(path)


class TestCompare:
    """Test strategy comparison."""

    def test_compare_parser(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["compare", "--strategies", "momentum,mean_reversion", "--data", "AAPL", "--period", "1y"])
        assert args.data == "AAPL"
        assert args.period == "1y"

    def test_run_strategy_compare_buy_hold(self):
        """Test buy_hold strategy comparison helper."""
        import numpy as np
        from src.cli.main import _run_strategy_compare

        # Create mock data
        import pandas as pd
        dates = pd.date_range("2023-01-01", periods=100)
        prices_list = [100 + i * 0.5 for i in range(100)]
        df = pd.DataFrame({"Close": prices_list, "Open": prices_list, "High": prices_list,
                           "Low": prices_list, "Volume": [1000] * 100}, index=dates)
        close = np.array(prices_list, dtype=np.float64)

        result = _run_strategy_compare("buy_hold", df, close, prices_list)
        assert result is not None
        assert result["name"] == "buy_hold"
        assert result["return"] > 0  # trending up data

    def test_run_strategy_unknown(self):
        import numpy as np
        from src.cli.main import _run_strategy_compare
        import pandas as pd

        dates = pd.date_range("2023-01-01", periods=100)
        prices_list = [100.0] * 100
        df = pd.DataFrame({"Close": prices_list}, index=dates)
        close = np.array(prices_list, dtype=np.float64)

        result = _run_strategy_compare("nonexistent", df, close, prices_list)
        assert result is None


class TestTelegramBot:
    """Test telegram bot framework."""

    def test_alert_manager_dataclass(self):
        from src.telegram_bot.alert_manager import PriceAlert
        alert = PriceAlert(id=1, chat_id=123, symbol="AAPL", operator=">", threshold=200.0)
        assert alert.check(201.0) is True
        assert alert.check(199.0) is False

    def test_alert_to_dict_roundtrip(self):
        from src.telegram_bot.alert_manager import PriceAlert
        alert = PriceAlert(id=1, chat_id=123, symbol="TSLA", operator="<", threshold=150.0)
        d = alert.to_dict()
        restored = PriceAlert.from_dict(d)
        assert restored.symbol == "TSLA"
        assert restored.operator == "<"
        assert restored.threshold == 150.0
        assert restored.check(149.0) is True
        assert restored.check(151.0) is False

    def test_alert_operators(self):
        from src.telegram_bot.alert_manager import PriceAlert
        a_gt = PriceAlert(id=1, chat_id=1, symbol="X", operator=">", threshold=100)
        a_lt = PriceAlert(id=2, chat_id=1, symbol="X", operator="<", threshold=100)
        a_gte = PriceAlert(id=3, chat_id=1, symbol="X", operator=">=", threshold=100)
        a_lte = PriceAlert(id=4, chat_id=1, symbol="X", operator="<=", threshold=100)

        assert a_gt.check(100) is False
        assert a_gt.check(101) is True
        assert a_lt.check(100) is False
        assert a_lt.check(99) is True
        assert a_gte.check(100) is True
        assert a_lte.check(100) is True

    def test_bot_init_requires_token(self):
        from src.telegram_bot.bot import TelegramBot
        # No token should raise
        old = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
                TelegramBot(token="")
        finally:
            if old:
                os.environ["TELEGRAM_BOT_TOKEN"] = old

    def test_bot_init_with_token(self):
        from src.telegram_bot.bot import TelegramBot
        bot = TelegramBot(token="test_token_123")
        assert bot.token == "test_token_123"
        assert "/quote" in bot._handlers
        assert "/analyze" in bot._handlers
        assert "/alert" in bot._handlers


class TestCIConfig:
    """Test CI config exists."""

    def test_ci_yml_exists(self):
        ci_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               ".github", "workflows", "ci.yml")
        assert os.path.exists(ci_path)

    def test_ci_yml_valid(self):
        import yaml
        ci_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               ".github", "workflows", "ci.yml")
        with open(ci_path) as f:
            config = yaml.safe_load(f)
        assert "jobs" in config
        assert "test" in config["jobs"]
