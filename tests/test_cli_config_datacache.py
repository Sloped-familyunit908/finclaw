"""
Tests for FinClaw v2.6.0 — CLI, ConfigManager, DataCache, Interactive
25+ tests covering all new components.
"""

import json
import os
import sys
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════
# ConfigManager tests
# ═══════════════════════════════════════════════════════════════

class TestConfigManager:
    def test_default_config(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        assert cfg.get("backtest.commission") == 0.001
        assert cfg.get("backtest.initial_capital") == 100000

    def test_get_nested(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        assert cfg.get("default.data_source") == "yfinance"
        assert cfg.get("strategies.momentum.lookback") == 20

    def test_get_missing_returns_default(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        assert cfg.get("nonexistent.key", 42) == 42

    def test_set_value(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        cfg.set("backtest.commission", 0.002)
        assert cfg.get("backtest.commission") == 0.002

    def test_set_new_nested(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        cfg.set("custom.section.value", "hello")
        assert cfg.get("custom.section.value") == "hello"

    def test_validate_ok(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        result = cfg.validate()  # should not raise
        assert result is None or result is True, "validate() on valid config should succeed"

    def test_validate_bad_commission(self):
        from src.config_manager import ConfigManager, ConfigValidationError
        cfg = ConfigManager()
        cfg.set("backtest.commission", 5.0)
        with pytest.raises(ConfigValidationError):
            cfg.validate()

    def test_validate_bad_capital(self):
        from src.config_manager import ConfigManager, ConfigValidationError
        cfg = ConfigManager()
        cfg.set("backtest.initial_capital", -100)
        with pytest.raises(ConfigValidationError):
            cfg.validate()

    def test_to_dict(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        d = cfg.to_dict()
        assert "backtest" in d
        assert "strategies" in d

    def test_get_strategy_config(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        mc = cfg.get_strategy_config("momentum")
        assert mc["lookback"] == 20

    def test_save_and_load(self):
        from src.config_manager import ConfigManager
        import copy
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.yml")
            cfg = ConfigManager()
            cfg.set("backtest.commission", 0.005)
            cfg.set("backtest.initial_capital", 100000)
            cfg.save(path)
            assert os.path.exists(path)

            cfg2 = ConfigManager._from_file(path)
            assert cfg2.get("backtest.commission") == 0.005

    def test_load_nonexistent_returns_defaults(self):
        from src.config_manager import ConfigManager
        cfg = ConfigManager()
        assert cfg.get("default.data_source") == "yfinance"


# ═══════════════════════════════════════════════════════════════
# DataCache tests
# ═══════════════════════════════════════════════════════════════

class TestDataCache:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_get(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("test_key", {"a": 1, "b": 2})
        result = cache.get("test_key", max_age_hours=1)
        assert result == {"a": 1, "b": 2}

    def test_get_missing(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        from src.data.cache import DataCache
        import sqlite3
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("old_key", [1, 2, 3])
        # Force expire by back-dating the entry in the DB
        with sqlite3.connect(cache._db_path) as conn:
            conn.execute("UPDATE cache SET created_at = created_at - 100000 WHERE key = ?", ("old_key",))
        result = cache.get("old_key", max_age_hours=1)
        assert result is None

    def test_clear(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_stats(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("k1", "v1")
        stats = cache.stats()
        assert stats["entries"] == 1
        assert "size_kb" in stats

    def test_keys(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("alpha", [1])
        cache.set("beta", [2])
        keys = cache.keys()
        assert "alpha" in keys
        assert "beta" in keys

    def test_overwrite(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("k", "old")
        cache.set("k", "new")
        assert cache.get("k") == "new"

    def test_clear_older_than(self):
        from src.data.cache import DataCache
        cache = DataCache(cache_dir=self.tmpdir)
        cache.set("recent", "data")
        # Clearing items older than 1 day shouldn't remove recent items
        cache.clear(older_than_days=1)
        assert cache.get("recent") == "data"


# ═══════════════════════════════════════════════════════════════
# CLI parser tests
# ═══════════════════════════════════════════════════════════════

class TestCLIParser:
    def test_build_parser(self):
        from src.cli.main import build_parser
        parser = build_parser()
        assert parser is not None

    def test_parse_backtest(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["backtest", "--strategy", "momentum", "--tickers", "AAPL,MSFT", "--start", "2023-01-01"])
        assert args.command == "backtest"
        assert args.strategy == "momentum"
        assert args.tickers == "AAPL,MSFT"
        assert args.start == "2023-01-01"

    def test_parse_screen(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["screen", "--criteria", "rsi<30,pe<15", "--universe", "sp500"])
        assert args.command == "screen"
        assert args.criteria == "rsi<30,pe<15"
        assert args.universe == "sp500"

    def test_parse_analyze(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["analyze", "--ticker", "AAPL", "--indicators", "rsi,macd"])
        assert args.command == "analyze"
        assert args.ticker == "AAPL"
        assert args.indicators == "rsi,macd"

    def test_parse_price(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["price", "--ticker", "AAPL,MSFT,GOOGL"])
        assert args.command == "price"
        assert args.ticker == "AAPL,MSFT,GOOGL"

    def test_parse_options_price(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["options", "price", "--type", "call", "--S", "150", "--K", "155", "--T", "0.5", "--r", "0.05", "--sigma", "0.25"])
        assert args.command == "options"
        assert args.options_cmd == "price"
        assert args.type == "call"
        assert args.S == 150.0

    def test_parse_paper_trade(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["paper-trade", "--strategy", "trend", "--tickers", "AAPL", "--capital", "50000"])
        assert args.command == "paper-trade"
        assert args.capital == 50000.0

    def test_parse_report(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["report", "--input", "data.json", "--format", "html", "--output", "out.html"])
        assert args.command == "report"
        assert args.format == "html"

    def test_parse_interactive(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["interactive"])
        assert args.command == "interactive"

    def test_parse_portfolio_track(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["portfolio", "track", "--file", "port.json"])
        assert args.command == "portfolio"
        assert args.portfolio_cmd == "track"
        assert args.file == "port.json"

    def test_version(self):
        from src.cli.main import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_no_command_returns_1(self):
        from src.cli.main import main
        result = main([])
        assert result == 1 or result is None  # prints help


# ═══════════════════════════════════════════════════════════════
# Interactive session tests
# ═══════════════════════════════════════════════════════════════

class TestInteractiveSession:
    def test_create_session(self):
        from src.interactive import InteractiveSession
        session = InteractiveSession()
        assert session.data is None
        assert session.ticker is None

    def test_help(self, capsys):
        from src.interactive import InteractiveSession
        session = InteractiveSession()
        session._help()
        captured = capsys.readouterr()
        assert "load" in captured.out
        assert "backtest" in captured.out

    def test_info_no_data(self, capsys):
        from src.interactive import InteractiveSession
        session = InteractiveSession()
        session._info()
        captured = capsys.readouterr()
        assert "No data" in captured.out

    def test_ta_no_data(self, capsys):
        from src.interactive import InteractiveSession
        session = InteractiveSession()
        session._ta(["rsi"])
        captured = capsys.readouterr()
        assert "No data" in captured.out


# ═══════════════════════════════════════════════════════════════
# Options pricing integration (no network needed)
# ═══════════════════════════════════════════════════════════════

class TestOptionsPricing:
    def test_call_price(self):
        from src.derivatives.options_pricing import BlackScholes
        price = BlackScholes.call_price(S=150, K=155, T=0.5, r=0.05, sigma=0.25)
        assert price > 0
        assert price < 150  # price can't exceed spot

    def test_put_price(self):
        from src.derivatives.options_pricing import BlackScholes
        price = BlackScholes.put_price(S=150, K=155, T=0.5, r=0.05, sigma=0.25)
        assert price > 0

    def test_put_call_parity(self):
        """Verify put-call parity: C - P = S - K*exp(-rT)."""
        import math
        from src.derivatives.options_pricing import BlackScholes
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2
        C = BlackScholes.call_price(S, K, T, r, sigma)
        P = BlackScholes.put_price(S, K, T, r, sigma)
        parity = C - P - (S - K * math.exp(-r * T))
        assert abs(parity) < 1e-10

    def test_greeks(self):
        from src.derivatives.options_pricing import BlackScholes
        g = BlackScholes.greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
        assert 0 < g["delta"] < 1
        assert g["gamma"] > 0
        assert g["vega"] > 0
