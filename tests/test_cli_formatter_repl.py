"""
Tests for FinClaw CLI v5.7.0
Tests for: OutputFormatter, ConfigManager, SetupWizard, FinClawREPL
35+ tests covering all CLI components.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.formatter import OutputFormatter, SPARKLINE_CHARS, _no_color, BOX
from src.cli.config import ConfigManager, DEFAULT_CONFIG


# ============================================================
# OutputFormatter Tests
# ============================================================

class TestOutputFormatterColor:
    def test_color_applies_code(self):
        result = OutputFormatter.color("hello", "red")
        assert "hello" in result
        assert "\033[31m" in result or result == "hello"  # NO_COLOR might be set

    def test_color_unknown_returns_plain(self):
        assert OutputFormatter.color("x", "nonexistent") == "x"

    def test_bold(self):
        result = OutputFormatter.bold("test")
        assert "test" in result

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_no_color_env(self):
        assert _no_color() is True

    def test_no_color_default(self):
        env = os.environ.copy()
        env.pop("NO_COLOR", None)
        env.pop("FINCLAW_NO_COLOR", None)
        with patch.dict(os.environ, env, clear=True):
            result = _no_color()
            assert isinstance(result, bool), "_no_color() should return a bool"


class TestOutputFormatterPriceColor:
    def test_positive(self):
        result = OutputFormatter.price_color(0.05)
        assert "+" in result or "5" in result

    def test_negative(self):
        result = OutputFormatter.price_color(-0.03)
        assert "-" in result or "3" in result

    def test_zero(self):
        result = OutputFormatter.price_color(0.0)
        assert "0" in result

    def test_custom_text(self):
        result = OutputFormatter.price_color(1.0, "UP")
        assert "UP" in result


class TestOutputFormatterTable:
    def test_empty_headers(self):
        assert OutputFormatter.table([], []) == ""

    def test_simple_style(self):
        t = OutputFormatter.table(["A", "B"], [["1", "2"]], style="simple")
        assert "A" in t and "B" in t
        assert "1" in t and "2" in t
        assert "---" not in t  # dashes but not triple

    def test_compact_style(self):
        t = OutputFormatter.table(["Name", "Value"], [["x", "1"]], style="compact")
        assert "│" in t
        assert "Name" in t

    def test_default_style_box(self):
        t = OutputFormatter.table(["H1", "H2"], [["a", "b"], ["c", "d"]])
        assert "┌" in t
        assert "┘" in t
        assert "H1" in t
        assert "a" in t

    def test_table_uneven_rows(self):
        t = OutputFormatter.table(["A", "B", "C"], [["1"]], style="simple")
        assert "A" in t

    def test_table_multiple_rows(self):
        rows = [[str(i), str(i*2)] for i in range(5)]
        t = OutputFormatter.table(["X", "Y"], rows)
        assert "4" in t and "8" in t


class TestOutputFormatterQuoteCard:
    def test_basic_card(self):
        card = OutputFormatter.quote_card({
            "symbol": "BTCUSDT",
            "price": 67234.50,
            "change_pct": 2.34,
            "volume": 1.2e9,
        })
        assert "BTCUSDT" in card
        assert "67,234.50" in card
        assert "▲" in card
        assert "1.2B" in card

    def test_negative_change(self):
        card = OutputFormatter.quote_card({
            "symbol": "ETH",
            "price": 3200.00,
            "change_pct": -1.5,
        })
        assert "▼" in card
        assert "-1.50" in card

    def test_small_price(self):
        card = OutputFormatter.quote_card({
            "symbol": "SHIB",
            "price": 0.000025,
            "change_pct": 5.0,
        })
        assert "SHIB" in card
        assert "0.000025" in card

    def test_with_high_low(self):
        card = OutputFormatter.quote_card({
            "symbol": "AAPL",
            "price": 175.50,
            "change_pct": 0.8,
            "high": 176.00,
            "low": 174.00,
        })
        assert "H:" in card
        assert "L:" in card

    def test_volume_millions(self):
        card = OutputFormatter.quote_card({
            "symbol": "X",
            "price": 10,
            "change_pct": 0,
            "volume": 5.5e6,
        })
        assert "5.5M" in card

    def test_volume_thousands(self):
        card = OutputFormatter.quote_card({
            "symbol": "X",
            "price": 10,
            "change_pct": 0,
            "volume": 750,
        })
        assert "750" in card


class TestOutputFormatterSparkline:
    def test_empty(self):
        assert OutputFormatter.sparkline([]) == ""

    def test_constant(self):
        result = OutputFormatter.sparkline([5, 5, 5])
        assert len(result) == 3

    def test_ascending(self):
        result = OutputFormatter.sparkline([1, 2, 3, 4, 5])
        assert len(result) == 5
        # First char should be lowest, last should be highest
        assert result[0] <= result[-1]

    def test_with_width(self):
        values = list(range(100))
        result = OutputFormatter.sparkline(values, width=10)
        assert len(result) == 10

    def test_single_value(self):
        result = OutputFormatter.sparkline([42])
        assert len(result) == 1


class TestOutputFormatterProgressBar:
    def test_full(self):
        bar = OutputFormatter.progress_bar(100, 100)
        assert "100%" in bar
        assert "█" in bar
        assert "░" not in bar

    def test_empty(self):
        bar = OutputFormatter.progress_bar(0, 100)
        assert "0%" in bar
        assert "░" in bar

    def test_half(self):
        bar = OutputFormatter.progress_bar(50, 100)
        assert "50%" in bar

    def test_zero_total(self):
        bar = OutputFormatter.progress_bar(5, 0)
        assert "0%" in bar

    def test_with_label(self):
        bar = OutputFormatter.progress_bar(3, 10, label="Loading")
        assert "Loading" in bar

    def test_no_pct(self):
        bar = OutputFormatter.progress_bar(5, 10, show_pct=False)
        assert "%" not in bar


class TestOutputFormatterFormatNumber:
    def test_trillions(self):
        assert "T" in OutputFormatter.format_number(1.5e12)

    def test_billions(self):
        assert "B" in OutputFormatter.format_number(2.3e9)

    def test_millions(self):
        assert "M" in OutputFormatter.format_number(4.5e6)

    def test_thousands(self):
        assert "K" in OutputFormatter.format_number(1234)

    def test_small(self):
        result = OutputFormatter.format_number(42.5)
        assert "42.50" == result


class TestOutputFormatterMisc:
    def test_banner(self):
        b = OutputFormatter.banner("Hello", width=30)
        assert "Hello" in b
        assert "╔" in b

    def test_divider(self):
        d = OutputFormatter.divider(width=20)
        assert len(d) == 20

    def test_key_value(self):
        result = OutputFormatter.key_value({"Name": "BTC", "Price": 67000})
        assert "Name" in result
        assert "67000" in result

    def test_key_value_empty(self):
        assert OutputFormatter.key_value({}) == ""


# ============================================================
# ConfigManager Tests
# ============================================================

class TestConfigManager:
    def test_defaults(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)  # Ensure file doesn't exist
            config = ConfigManager(path)
            assert config.get("mode") == "paper"
            assert config.get("default_exchange") == "binance"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_set(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            config.set("backtest.commission", 0.002)
            assert config.get("backtest.commission") == 0.002
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_default(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            assert config.get("nonexistent.key", "fallback") == "fallback"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_dot_notation_nested(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            assert config.get("backtest.initial_capital") == 100000
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            config = ConfigManager(path)
            config.set("mode", "live")
            config.save()

            config2 = ConfigManager(path)
            assert config2.get("mode") == "live"

    def test_api_key_get_set(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            config.set_api_key("binance", "key123", "secret456")
            assert config.get_api_key("binance") == "key123"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_api_key_missing(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            assert config.get_api_key("nonexistent") is None
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_reset(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            config.set("mode", "live")
            config.reset()
            assert config.get("mode") == "paper"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_to_dict(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            d = config.to_dict()
            assert isinstance(d, dict)
            assert "mode" in d
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_repr(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            assert "ConfigManager" in repr(config)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_set_creates_nested(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            os.unlink(path)
            config = ConfigManager(path)
            config.set("new.deeply.nested.key", "value")
            assert config.get("new.deeply.nested.key") == "value"
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ============================================================
# SetupWizard Tests
# ============================================================

class TestSetupWizard:
    def test_wizard_creates_config(self):
        from src.cli.wizard import SetupWizard
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            wizard = SetupWizard(config_path=path)

            # Simulate user input: select exchange 6 (yfinance), skip keys, strategy 1, mode 1
            inputs = ["6", "", "1", "1"]
            with patch("builtins.input", side_effect=inputs):
                result = wizard.run()

            assert result is True
            assert os.path.exists(path)

    def test_wizard_cancel(self):
        from src.cli.wizard import SetupWizard
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            wizard = SetupWizard(config_path=path)

            with patch("builtins.input", side_effect=KeyboardInterrupt):
                result = wizard.run()

            assert result is False

    def test_wizard_all_exchanges(self):
        from src.cli.wizard import SetupWizard
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yaml")
            wizard = SetupWizard(config_path=path)

            # "all" exchanges, skip all api keys, strategy 2, paper mode
            inputs = ["all"] + [""] * 7 + [""] * 7 + ["2", "1"]
            with patch("builtins.input", side_effect=inputs):
                result = wizard.run()

            assert result is True


# ============================================================
# REPL Tests
# ============================================================

class TestFinClawREPL:
    def test_repl_init(self):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        assert repl.data is None
        assert repl.ticker is None

    def test_repl_handler_lookup(self):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        assert repl._get_handler("help") is not None
        assert repl._get_handler("quote") is not None
        assert repl._get_handler("nonexistent") is None

    def test_repl_help(self, capsys):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        repl._cmd_help([])
        captured = capsys.readouterr()
        assert "Data" in captured.out
        assert "quote" in captured.out

    def test_repl_info_no_data(self, capsys):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        repl._cmd_info([])
        captured = capsys.readouterr()
        assert "No data" in captured.out

    def test_repl_quit(self):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        with pytest.raises(SystemExit):
            repl._cmd_quit([])

    def test_repl_clear(self):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        with patch("os.system") as mock_sys:
            repl._cmd_clear([])
            mock_sys.assert_called_once()

    def test_repl_config_show(self, capsys):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        with patch("src.cli.config.ConfigManager.to_dict", return_value={"mode": "paper"}):
            repl._cmd_config([])
        captured = capsys.readouterr()
        assert "mode" in captured.out

    def test_repl_export_no_args(self, capsys):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        repl._cmd_export([])
        captured = capsys.readouterr()
        assert "Usage" in captured.out

    def test_repl_export_json(self):
        from src.cli.repl import FinClawREPL
        repl = FinClawREPL()
        repl.ticker = "TEST"
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            repl._cmd_export([path])
            with open(path) as f:
                data = json.load(f)
            assert data["ticker"] == "TEST"
        finally:
            os.unlink(path)


# ============================================================
# Completer Tests
# ============================================================

class TestCompleter:
    def test_command_completion(self):
        from src.cli.repl import _Completer
        c = _Completer()
        # First call state=0 should populate options
        result = c.complete("qu", 0)
        assert result is not None and result.startswith("quote")

    def test_no_match(self):
        from src.cli.repl import _Completer
        c = _Completer()
        result = c.complete("zzzzz", 0)
        assert result is None
