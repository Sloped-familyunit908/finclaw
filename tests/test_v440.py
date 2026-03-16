"""Tests for FinClaw Notification & Alert System v4.4.0 — 45 tests."""

from __future__ import annotations

import json
import smtplib
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.notifications.base import NotificationChannel, NotificationLevel
from src.notifications.console import ConsoleChannel
from src.notifications.hub import NotificationHub
from src.notifications.telegram import TelegramChannel
from src.notifications.discord import DiscordChannel
from src.notifications.email_channel import EmailChannel
from src.notifications.webhook import WebhookChannel, WebhookNotifier
from src.notifications.smart_alerts import SmartAlertEngine, AlertRule


# =====================================================================
# NotificationLevel
# =====================================================================


class TestNotificationLevel:
    def test_level_values(self):
        assert NotificationLevel.DEBUG == "debug"
        assert NotificationLevel.INFO == "info"
        assert NotificationLevel.WARNING == "warning"
        assert NotificationLevel.CRITICAL == "critical"

    def test_level_from_string(self):
        assert NotificationLevel("info") == NotificationLevel.INFO
        assert NotificationLevel("critical") == NotificationLevel.CRITICAL


# =====================================================================
# ConsoleChannel
# =====================================================================


class TestConsoleChannel:
    def test_name(self):
        ch = ConsoleChannel()
        assert ch.name == "console"

    def test_send_info(self, capsys):
        ch = ConsoleChannel()
        ok = ch.send("hello world", NotificationLevel.INFO)
        assert ok is True
        out = capsys.readouterr().out
        assert "[INFO]" in out
        assert "hello world" in out

    def test_send_critical(self, capsys):
        ch = ConsoleChannel()
        ch.send("fire!", NotificationLevel.CRITICAL)
        out = capsys.readouterr().out
        assert "[CRITICAL]" in out
        assert "🚨" in out

    def test_history_tracking(self, capsys):
        ch = ConsoleChannel()
        ch.send("msg1")
        ch.send("msg2")
        _ = capsys.readouterr()
        assert len(ch.history) == 2
        assert ch.history[0]["message"] == "msg1"

    def test_stderr(self, capsys):
        ch = ConsoleChannel(use_stderr=True)
        ch.send("err msg")
        captured = capsys.readouterr()
        assert "err msg" in captured.err

    def test_test_method(self, capsys):
        ch = ConsoleChannel()
        ok = ch.test()
        assert ok is True
        out = capsys.readouterr().out
        assert "test notification" in out


# =====================================================================
# TelegramChannel
# =====================================================================


class TestTelegramChannel:
    def test_name(self):
        ch = TelegramChannel("token", "chat")
        assert ch.name == "telegram"

    @patch("src.notifications.telegram.requests.post")
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(ok=True)
        ch = TelegramChannel("tok123", "chat456")
        ok = ch.send("price alert!", NotificationLevel.WARNING)
        assert ok is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "tok123" in args[0]
        assert kwargs["json"]["chat_id"] == "chat456"
        assert "⚠️" in kwargs["json"]["text"]

    @patch("src.notifications.telegram.requests.post")
    def test_send_failure(self, mock_post):
        mock_post.return_value = MagicMock(ok=False, status_code=403, text="Forbidden")
        ch = TelegramChannel("tok", "chat")
        ok = ch.send("msg")
        assert ok is False

    @patch("src.notifications.telegram.requests.post", side_effect=Exception("timeout"))
    def test_send_exception(self, mock_post):
        ch = TelegramChannel("tok", "chat")
        ok = ch.send("msg")
        assert ok is False


# =====================================================================
# DiscordChannel
# =====================================================================


class TestDiscordChannel:
    def test_name(self):
        ch = DiscordChannel("https://discord.com/api/webhooks/xxx")
        assert ch.name == "discord"

    @patch("src.notifications.discord.requests.post")
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(ok=True, status_code=204)
        ch = DiscordChannel("https://hook.url")
        ok = ch.send("alert!", NotificationLevel.CRITICAL)
        assert ok is True
        payload = mock_post.call_args[1]["json"]
        assert payload["username"] == "FinClaw"
        assert payload["embeds"][0]["color"] == 0xFF0000

    @patch("src.notifications.discord.requests.post")
    def test_send_failure(self, mock_post):
        mock_post.return_value = MagicMock(ok=False, status_code=500, text="err")
        ch = DiscordChannel("https://hook.url")
        assert ch.send("msg") is False


# =====================================================================
# EmailChannel
# =====================================================================


class TestEmailChannel:
    @patch("src.notifications.email_channel.smtplib.SMTP")
    def test_send_success(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        ch = EmailChannel("smtp.example.com", 587, "user", "pass", "from@ex.com", ["to@ex.com"])
        assert ch.name == "email"
        ok = ch.send("test email", NotificationLevel.WARNING)
        assert ok is True
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch("src.notifications.email_channel.smtplib.SMTP", side_effect=Exception("conn refused"))
    def test_send_failure(self, mock_smtp):
        ch = EmailChannel("bad.host", 587, "u", "p", "f@x.com", ["t@x.com"])
        assert ch.send("msg") is False


# =====================================================================
# WebhookChannel
# =====================================================================


class TestWebhookChannel:
    def test_name(self):
        ch = WebhookChannel("https://hook.example.com")
        assert ch.name == "webhook"

    @patch("src.notifications.webhook.requests.post")
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        ch = WebhookChannel("https://hook.example.com")
        ok = ch.send("payload test")
        assert ok is True
        payload = mock_post.call_args[1]["json"]
        assert payload["text"] == "payload test"
        assert payload["source"] == "finclaw"

    @patch("src.notifications.webhook.requests.post", side_effect=Exception("timeout"))
    def test_send_exception(self, mock_post):
        ch = WebhookChannel("https://hook.example.com")
        assert ch.send("x") is False


# =====================================================================
# WebhookNotifier (legacy)
# =====================================================================


class TestWebhookNotifier:
    @patch("src.notifications.webhook.requests.post")
    def test_notify_slack(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        n = WebhookNotifier({"slack": "https://hooks.slack.com/xxx"})
        results = n.notify("price_alert", {"symbol": "AAPL", "price": 150})
        assert results["slack"] is True
        payload = mock_post.call_args[1]["json"]
        assert "blocks" in payload

    @patch("src.notifications.webhook.requests.post")
    def test_notify_discord(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        n = WebhookNotifier({"discord": "https://discord.com/api/webhooks/xxx"})
        results = n.notify("volume_spike", {"symbol": "BTC"})
        assert results["discord"] is True
        assert "embeds" in mock_post.call_args[1]["json"]


# =====================================================================
# NotificationHub
# =====================================================================


class TestNotificationHub:
    def test_register_and_send(self, capsys):
        hub = NotificationHub()
        hub.register_channel("console", ConsoleChannel())
        result = hub.send("test msg", "info")
        _ = capsys.readouterr()
        assert result["console"] is True

    def test_unregister(self):
        hub = NotificationHub()
        hub.register_channel("x", ConsoleChannel())
        assert hub.unregister_channel("x") is True
        assert hub.unregister_channel("x") is False

    def test_send_to_specific_channels(self, capsys):
        hub = NotificationHub()
        hub.register_channel("a", ConsoleChannel())
        hub.register_channel("b", ConsoleChannel())
        result = hub.send("msg", channels=["a"])
        _ = capsys.readouterr()
        assert "a" in result
        assert "b" not in result

    def test_send_missing_channel(self):
        hub = NotificationHub()
        result = hub.send("msg", channels=["nonexistent"])
        assert result["nonexistent"] is False

    def test_history(self, capsys):
        hub = NotificationHub()
        hub.register_channel("c", ConsoleChannel())
        hub.send("m1")
        hub.send("m2")
        _ = capsys.readouterr()
        assert len(hub.history) == 2
        hub.clear_history()
        assert len(hub.history) == 0

    def test_send_alert_object(self, capsys):
        from src.alerts.alert_manager import Alert as ManagedAlert, AlertSeverity
        hub = NotificationHub()
        hub.register_channel("c", ConsoleChannel())
        alert = ManagedAlert(
            name="Drawdown",
            severity=AlertSeverity.CRITICAL,
            message="Drawdown at 15%",
            value=0.15,
            threshold=0.10,
        )
        result = hub.send_alert(alert)
        _ = capsys.readouterr()
        assert result["c"] is True


# =====================================================================
# SmartAlertEngine — price_cross
# =====================================================================


class TestSmartAlertPriceCross:
    def test_above_triggered(self):
        engine = SmartAlertEngine()
        engine.price_cross("BTCUSDT", 70000, "above")
        alerts = engine.evaluate({"symbol": "BTCUSDT", "price": 71000})
        assert len(alerts) == 1
        assert alerts[0]["direction"] == "above"

    def test_above_not_triggered(self):
        engine = SmartAlertEngine()
        engine.price_cross("BTCUSDT", 70000, "above")
        alerts = engine.evaluate({"symbol": "BTCUSDT", "price": 69000})
        assert len(alerts) == 0

    def test_below_triggered(self):
        engine = SmartAlertEngine()
        engine.price_cross("ETH", 3000, "below")
        alerts = engine.evaluate({"symbol": "ETH", "price": 2900})
        assert len(alerts) == 1
        assert "below" in alerts[0]["message"]

    def test_wrong_symbol_ignored(self):
        engine = SmartAlertEngine()
        engine.price_cross("AAPL", 200, "above")
        alerts = engine.evaluate({"symbol": "GOOG", "price": 300})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — volume_spike
# =====================================================================


class TestSmartAlertVolumeSpike:
    def test_spike_triggered(self):
        engine = SmartAlertEngine()
        engine.volume_spike("AAPL", 2.0)
        vol = [1000] * 20 + [5000]  # 5x average
        alerts = engine.evaluate({"symbol": "AAPL", "volume": vol})
        assert len(alerts) == 1
        assert alerts[0]["ratio"] == 5.0

    def test_no_spike(self):
        engine = SmartAlertEngine()
        engine.volume_spike("AAPL", 3.0)
        vol = [1000] * 21
        alerts = engine.evaluate({"symbol": "AAPL", "volume": vol})
        assert len(alerts) == 0

    def test_insufficient_data(self):
        engine = SmartAlertEngine()
        engine.volume_spike("X", 2.0)
        alerts = engine.evaluate({"symbol": "X", "volume": [100, 200]})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — drawdown
# =====================================================================


class TestSmartAlertDrawdown:
    def test_drawdown_triggered(self):
        engine = SmartAlertEngine()
        engine.drawdown_alert("main_portfolio", 0.10)
        equity = [100, 110, 120, 100]  # 16.7% drawdown
        alerts = engine.evaluate({"portfolio": "main_portfolio", "equity": equity})
        assert len(alerts) == 1
        assert alerts[0]["drawdown"] > 0.10

    def test_no_drawdown(self):
        engine = SmartAlertEngine()
        engine.drawdown_alert("pf", 0.10)
        equity = [100, 105, 110]
        alerts = engine.evaluate({"portfolio": "pf", "equity": equity})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — pnl_target
# =====================================================================


class TestSmartAlertPnlTarget:
    def test_target_reached(self):
        engine = SmartAlertEngine()
        engine.pnl_target(0.20)
        alerts = engine.evaluate({"pnl_pct": 0.25})
        assert len(alerts) == 1
        assert "target reached" in alerts[0]["message"]

    def test_target_not_reached(self):
        engine = SmartAlertEngine()
        engine.pnl_target(0.20)
        alerts = engine.evaluate({"pnl_pct": 0.10})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — risk_breach
# =====================================================================


class TestSmartAlertRiskBreach:
    def test_breach(self):
        engine = SmartAlertEngine()
        engine.risk_breach("var_95", 0.05)
        alerts = engine.evaluate({"var_95": 0.08})
        assert len(alerts) == 1
        assert alerts[0]["metric"] == "var_95"

    def test_no_breach(self):
        engine = SmartAlertEngine()
        engine.risk_breach("var_95", 0.05)
        alerts = engine.evaluate({"var_95": 0.03})
        assert len(alerts) == 0

    def test_missing_metric(self):
        engine = SmartAlertEngine()
        engine.risk_breach("sharpe", 2.0)
        alerts = engine.evaluate({"other_metric": 5.0})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — correlation_break
# =====================================================================


class TestSmartAlertCorrelation:
    def test_break_detected(self):
        import random
        random.seed(42)
        engine = SmartAlertEngine()
        engine.correlation_break(("SPY", "QQQ"), 0.8)
        # Uncorrelated random data → low correlation
        a = [random.gauss(0, 1) for _ in range(30)]
        b = [random.gauss(0, 1) for _ in range(30)]
        alerts = engine.evaluate({"returns_a": a, "returns_b": b})
        assert len(alerts) == 1

    def test_no_break(self):
        engine = SmartAlertEngine()
        engine.correlation_break(("A", "B"), 0.5)
        # Perfectly correlated
        a = list(range(30))
        b = [x * 2 for x in a]
        alerts = engine.evaluate({"returns_a": [float(x) for x in a], "returns_b": [float(x) for x in b]})
        assert len(alerts) == 0


# =====================================================================
# SmartAlertEngine — rule management
# =====================================================================


class TestSmartAlertRuleManagement:
    def test_add_and_remove(self):
        engine = SmartAlertEngine()
        rule = engine.price_cross("X", 100, "above")
        assert len(engine.rules) == 1
        assert engine.remove_rule(rule.name)
        assert len(engine.rules) == 0

    def test_enable_disable(self):
        engine = SmartAlertEngine()
        rule = engine.price_cross("X", 100, "above")
        engine.enable_rule(rule.name, False)
        alerts = engine.evaluate({"symbol": "X", "price": 200})
        assert len(alerts) == 0
        engine.enable_rule(rule.name, True)
        alerts = engine.evaluate({"symbol": "X", "price": 200})
        assert len(alerts) == 1

    def test_history_accumulates(self):
        engine = SmartAlertEngine()
        engine.price_cross("X", 50, "above")
        engine.evaluate({"symbol": "X", "price": 100})
        engine.evaluate({"symbol": "X", "price": 100})
        assert len(engine.history) == 2
        engine.clear_history()
        assert len(engine.history) == 0

    def test_cooldown(self):
        engine = SmartAlertEngine()
        rule = engine.price_cross("X", 50, "above")
        rule.cooldown_seconds = 3600
        engine.evaluate({"symbol": "X", "price": 100})
        # Second eval within cooldown should not fire
        alerts = engine.evaluate({"symbol": "X", "price": 100})
        assert len(alerts) == 0

    def test_remove_nonexistent(self):
        engine = SmartAlertEngine()
        assert engine.remove_rule("nope") is False
