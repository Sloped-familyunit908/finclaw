"""Tests for FinClaw v1.8.0 — API Layer & Integration."""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
import time
from http.server import HTTPServer
from io import BytesIO
from threading import Thread
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.server import FinClawServer, FinClawHandler, _json_response
from src.api.webhooks import WebhookManager, VALID_EVENTS, VALID_FORMATS
from src.export.exporter import DataExporter
from src.utils.logger import FinClawLogger
from src.plugins.manager import PluginManager, PluginInfo


# ============================================================
# REST API Server Tests
# ============================================================

class TestJsonResponse:
    def test_basic_dict(self):
        result = _json_response({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_handles_non_serializable(self):
        from datetime import datetime
        result = _json_response({"ts": datetime(2024, 1, 1)})
        parsed = json.loads(result)
        assert "2024" in parsed["ts"]


class TestFinClawServer:
    def test_init_defaults(self):
        server = FinClawServer(port=0)
        assert server.port == 0
        assert server.host == "0.0.0.0"

    def test_health_endpoint(self):
        server = FinClawServer()
        result = server._handle_health({})
        assert result["status"] == "ok"
        assert result["version"] == "5.1.0"
        assert "uptime_seconds" in result

    def test_signal_missing_ticker(self):
        server = FinClawServer()
        result = server._handle_signal({})
        assert "error" in result

    def test_signal_with_ticker(self):
        server = FinClawServer()
        result = server._handle_signal({"ticker": "AAPL", "strategy": "momentum"})
        assert result["ticker"] == "AAPL"
        assert result["strategy"] == "momentum"
        assert "signal" in result

    def test_backtest_missing_ticker(self):
        server = FinClawServer()
        result = server._handle_backtest({})
        assert "error" in result

    def test_backtest_with_params(self):
        server = FinClawServer()
        result = server._handle_backtest({"ticker": "MSFT", "strategy": "mean_reversion", "start": "2021-01-01"})
        assert result["ticker"] == "MSFT"
        assert result["start"] == "2021-01-01"

    def test_portfolio_missing_tickers(self):
        server = FinClawServer()
        result = server._handle_portfolio({})
        assert "holdings" in result

    def test_portfolio_equal_weight(self):
        server = FinClawServer()
        result = server._handle_portfolio({"tickers": "AAPL,MSFT,GOOGL"})
        assert len(result["weights"]) == 3
        assert abs(sum(result["weights"].values()) - 1.0) < 0.01

    def test_screen_endpoint(self):
        server = FinClawServer()
        result = server._handle_screen({"rsi_lt": "30", "volume_gt": "1.5"})
        assert result["criteria"]["rsi_lt"] == 30.0

    def test_custom_route(self):
        server = FinClawServer()
        server.route("/api/custom", lambda p: {"custom": True})
        handler_cls = server.create_handler_class()
        assert "/api/custom" in handler_cls._routes

    def test_cors_origin(self):
        server = FinClawServer(cors_origin="https://example.com")
        assert server._cors_origin == "https://example.com"

    def test_create_handler_class(self):
        server = FinClawServer()
        cls = server.create_handler_class()
        assert issubclass(cls, FinClawHandler)
        assert "/api/health" in cls._routes


# ============================================================
# Webhook Tests
# ============================================================

class TestWebhookManager:
    def test_register(self):
        wm = WebhookManager()
        hook = wm.register("signal_change", "https://example.com/hook")
        assert hook.event == "signal_change"
        assert hook.format == "json"

    def test_register_invalid_event(self):
        wm = WebhookManager()
        with pytest.raises(ValueError):
            wm.register("invalid_event", "https://example.com")

    def test_register_invalid_format(self):
        wm = WebhookManager()
        with pytest.raises(ValueError):
            wm.register("signal_change", "https://example.com", format="xml")

    def test_unregister(self):
        wm = WebhookManager()
        wm.register("signal_change", "https://example.com/a")
        wm.register("alert_triggered", "https://example.com/a")
        removed = wm.unregister("https://example.com/a")
        assert removed == 2
        assert len(wm.list_webhooks()) == 0

    def test_unregister_by_event(self):
        wm = WebhookManager()
        wm.register("signal_change", "https://example.com/a")
        wm.register("alert_triggered", "https://example.com/a")
        removed = wm.unregister("https://example.com/a", event="signal_change")
        assert removed == 1
        assert len(wm.list_webhooks()) == 1

    def test_list_webhooks(self):
        wm = WebhookManager()
        wm.register("signal_change", "https://a.com")
        wm.register("trade_executed", "https://b.com")
        assert len(wm.list_webhooks()) == 2

    def test_format_json(self):
        body = WebhookManager._format_payload("json", "signal_change", {"ticker": "AAPL"})
        data = json.loads(body)
        assert data["event"] == "signal_change"
        assert data["data"]["ticker"] == "AAPL"

    def test_format_slack(self):
        body = WebhookManager._format_payload("slack", "trade_executed", {"action": "BUY"})
        data = json.loads(body)
        assert "text" in data
        assert "trade_executed" in data["text"]

    def test_format_discord(self):
        body = WebhookManager._format_payload("discord", "alert_triggered", {"level": "high"})
        data = json.loads(body)
        assert "embeds" in data

    def test_format_teams(self):
        body = WebhookManager._format_payload("teams", "daily_summary", {"pnl": 1500})
        data = json.loads(body)
        assert data["@type"] == "MessageCard"

    def test_dispatch_no_hooks(self):
        wm = WebhookManager()
        results = wm.dispatch("signal_change", {"ticker": "AAPL"})
        assert results == []

    def test_get_history_empty(self):
        wm = WebhookManager()
        assert wm.get_history() == []


# ============================================================
# Data Exporter Tests
# ============================================================

class TestDataExporter:
    def setup_method(self):
        self.exporter = DataExporter()
        self.sample_data = [
            {"ticker": "AAPL", "price": 150.0, "signal": "buy"},
            {"ticker": "MSFT", "price": 380.0, "signal": "hold"},
        ]

    def test_to_csv(self, tmp_path):
        path = str(tmp_path / "test.csv")
        result = self.exporter.to_csv(self.sample_data, path)
        assert os.path.exists(result)
        with open(result) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["ticker"] == "AAPL"

    def test_to_json(self, tmp_path):
        path = str(tmp_path / "test.json")
        result = self.exporter.to_json(self.sample_data, path)
        assert os.path.exists(result)
        with open(result) as f:
            data = json.load(f)
        assert len(data) == 2

    def test_to_csv_empty_raises(self, tmp_path):
        with pytest.raises(ValueError):
            self.exporter.to_csv([], str(tmp_path / "empty.csv"))

    def test_to_string_csv(self):
        result = self.exporter.to_string(self.sample_data, fmt="csv")
        assert "AAPL" in result
        assert "ticker" in result

    def test_to_string_json(self):
        result = self.exporter.to_string(self.sample_data, fmt="json")
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_to_string_empty(self):
        assert self.exporter.to_string([], fmt="csv") == ""

    def test_dict_input(self, tmp_path):
        path = str(tmp_path / "single.json")
        self.exporter.to_json({"ticker": "TSLA"}, path)
        with open(path) as f:
            data = json.load(f)
        assert data[0]["ticker"] == "TSLA"

    def test_to_records_unsupported(self):
        with pytest.raises(TypeError):
            self.exporter._to_records(42)

    def test_parquet_not_available(self, tmp_path):
        exporter = DataExporter()
        with patch("src.export.exporter.HAS_PARQUET", False):
            with pytest.raises(ImportError):
                exporter.to_parquet(self.sample_data, str(tmp_path / "test.parquet"))

    def test_excel_not_available(self, tmp_path):
        exporter = DataExporter()
        with patch("src.export.exporter.HAS_EXCEL", False):
            with pytest.raises(ImportError):
                exporter.to_excel(self.sample_data, str(tmp_path / "test.xlsx"))

    def test_ensure_dir(self, tmp_path):
        path = str(tmp_path / "subdir" / "deep" / "test.csv")
        self.exporter.to_csv(self.sample_data, path)
        assert os.path.exists(path)


# ============================================================
# Logger Tests
# ============================================================

class TestFinClawLogger:
    def test_trade_log(self):
        logger = FinClawLogger("test_trade", json_output=True)
        record = logger.trade("BUY", "AAPL", shares=100, price=150.25)
        assert record["category"] == "trade"
        assert record["action"] == "BUY"
        assert record["ticker"] == "AAPL"

    def test_signal_log(self):
        logger = FinClawLogger("test_signal")
        record = logger.signal("SELL", "MSFT", strength=-0.7, strategy="momentum")
        assert record["category"] == "signal"
        assert record["direction"] == "SELL"

    def test_risk_log(self):
        logger = FinClawLogger("test_risk")
        record = logger.risk("MAX_DRAWDOWN", current=-0.15, limit=-0.20)
        assert record["category"] == "risk"
        assert record["risk_type"] == "MAX_DRAWDOWN"

    def test_performance_log(self):
        logger = FinClawLogger("test_perf")
        record = logger.performance("sharpe", 1.85)
        assert record["metric"] == "sharpe"
        assert record["value"] == 1.85

    def test_error_log(self):
        logger = FinClawLogger("test_err")
        record = logger.error("Connection failed", host="api.example.com")
        assert record["category"] == "error"

    def test_get_records(self):
        logger = FinClawLogger("test_records")
        logger.trade("BUY", "AAPL")
        logger.signal("SELL", "MSFT")
        logger.trade("SELL", "AAPL")
        assert len(logger.get_records()) == 3
        assert len(logger.get_records("trade")) == 2
        assert len(logger.get_records("signal")) == 1

    def test_clear(self):
        logger = FinClawLogger("test_clear")
        logger.trade("BUY", "AAPL")
        logger.clear()
        assert len(logger.get_records()) == 0

    def test_with_log_file(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        logger = FinClawLogger("test_file", log_file=log_file)
        logger.trade("BUY", "TSLA")
        assert os.path.exists(log_file)


# ============================================================
# Plugin Manager Tests
# ============================================================

class TestPluginManager:
    def test_init(self):
        pm = PluginManager()
        assert pm.list_plugins() == []

    def test_load_nonexistent(self):
        pm = PluginManager()
        with pytest.raises(FileNotFoundError):
            pm.load_plugin("/nonexistent/plugin.py")

    def test_load_plugin(self, tmp_path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            'PLUGIN_TYPE = "strategy"\n'
            '__version__ = "1.0.0"\n'
            '__description__ = "Test plugin"\n'
            'def register(manager):\n'
            '    manager.add_strategy("test_strat", lambda: None)\n'
        )
        pm = PluginManager()
        info = pm.load_plugin(str(plugin_file))
        assert info.name == "my_plugin"
        assert info.plugin_type == "strategy"
        assert info.version == "1.0.0"
        assert "test_strat" in pm.strategies

    def test_load_duplicate(self, tmp_path):
        plugin_file = tmp_path / "dup.py"
        plugin_file.write_text("PLUGIN_TYPE = 'indicator'\n")
        pm = PluginManager()
        pm.load_plugin(str(plugin_file))
        with pytest.raises(ValueError):
            pm.load_plugin(str(plugin_file))

    def test_unload(self, tmp_path):
        plugin_file = tmp_path / "unload_me.py"
        plugin_file.write_text("PLUGIN_TYPE = 'strategy'\n")
        pm = PluginManager()
        pm.load_plugin(str(plugin_file))
        assert pm.unload_plugin("unload_me")
        assert pm.list_plugins() == []

    def test_unload_nonexistent(self):
        pm = PluginManager()
        assert not pm.unload_plugin("nope")

    def test_load_directory(self, tmp_path):
        for i in range(3):
            (tmp_path / f"plugin_{i}.py").write_text(f"PLUGIN_TYPE = 'indicator'\n__version__ = '0.{i}.0'\n")
        (tmp_path / "_private.py").write_text("# skip\n")
        pm = PluginManager()
        loaded = pm.load_directory(str(tmp_path))
        assert len(loaded) == 3

    def test_load_directory_nonexistent(self):
        pm = PluginManager()
        assert pm.load_directory("/nonexistent") == []

    def test_get_plugin(self, tmp_path):
        plugin_file = tmp_path / "getter.py"
        plugin_file.write_text("PLUGIN_TYPE = 'exporter'\n")
        pm = PluginManager()
        pm.load_plugin(str(plugin_file))
        assert pm.get_plugin("getter") is not None
        assert pm.get_plugin("nope") is None

    def test_add_indicator(self):
        pm = PluginManager()
        pm.add_indicator("custom_rsi", lambda x: x)
        assert "custom_rsi" in pm.indicators

    def test_add_data_source(self):
        pm = PluginManager()
        pm.add_data_source("yahoo", MagicMock())
        assert "yahoo" in pm.data_sources

    def test_add_exporter(self):
        pm = PluginManager()
        pm.add_exporter("custom_csv", MagicMock())
        assert "custom_csv" in pm.exporters
