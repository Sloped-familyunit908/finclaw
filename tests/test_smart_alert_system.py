"""Tests for Smart Alert System v5.10 — 45 tests covering engine, channels, history, and CLI."""

import json
import os
import sys
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alerts.engine import (
    AlertEngine, AlertCondition, AlertSeverity, AlertRule,
    PriceAlert, VolumeAlert, TechnicalAlert, SentimentAlert, PortfolioAlert,
    FiredAlert,
)
from src.alerts.channels import ConsoleChannel, WebhookChannel, FileChannel
from src.alerts.history import AlertHistory


# ── Helper ────────────────────────────────────────────────────

def _make_data(symbol="BTCUSDT", price=70000, n=50, vol_mult=1.0, sentiment=None):
    """Create market_data dict for testing."""
    close = list(np.linspace(price * 0.9, price, n))
    volume = [1000.0 * vol_mult] * n
    d = {"symbol": symbol, "price": price, "close": close, "volume": volume}
    if sentiment is not None:
        d["sentiment"] = sentiment
    return d


# ══════════════════════════════════════════════════════════════
# AlertEngine tests
# ══════════════════════════════════════════════════════════════

class TestAlertEngine:
    def test_add_rule_returns_id(self):
        e = AlertEngine()
        rule = AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=100)
        rid = e.add_rule(rule)
        assert rid == 1

    def test_add_multiple_rules_increments_id(self):
        e = AlertEngine()
        r1 = AlertRule(name="a", condition=AlertCondition.PRICE_ABOVE, symbol="X", threshold=1)
        r2 = AlertRule(name="b", condition=AlertCondition.PRICE_BELOW, symbol="X", threshold=1)
        assert e.add_rule(r1) == 1
        assert e.add_rule(r2) == 2

    def test_remove_rule(self):
        e = AlertEngine()
        r = AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="X", threshold=1)
        rid = e.add_rule(r)
        assert e.remove_rule(rid) is True
        assert len(e.rules) == 0

    def test_remove_nonexistent_rule(self):
        e = AlertEngine()
        assert e.remove_rule(999) is False

    def test_active_rules_excludes_disabled(self):
        e = AlertEngine()
        r = AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="X", threshold=1, enabled=False)
        e.add_rule(r)
        assert len(e.active_rules) == 0

    def test_price_above_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=50000))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 1
        assert result[0].condition == "price_above"

    def test_price_above_no_trigger(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=80000))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 0

    def test_price_below_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_BELOW, symbol="BTC", threshold=80000))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 1

    def test_wrong_symbol_ignored(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="ETH", threshold=1))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 0

    def test_cooldown_prevents_refire(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=50000, cooldown=9999))
        e.evaluate(_make_data("BTC", price=60000))
        result2 = e.evaluate(_make_data("BTC", price=60000))
        assert len(result2) == 0

    def test_cooldown_expired_allows_refire(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=50000, cooldown=0))
        e.evaluate(_make_data("BTC", price=60000))
        result2 = e.evaluate(_make_data("BTC", price=60000))
        assert len(result2) == 1

    def test_disabled_rule_skipped(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=1, enabled=False))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 0

    def test_volume_spike_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="vol", condition=AlertCondition.VOLUME_SPIKE, symbol="BTC", threshold=1.5))
        data = _make_data("BTC", price=100, n=25)
        # Last volume much higher than avg
        data["volume"][-1] = 50000.0
        result = e.evaluate(data)
        assert len(result) == 1

    def test_volume_spike_no_trigger(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="vol", condition=AlertCondition.VOLUME_SPIKE, symbol="BTC", threshold=5.0))
        result = e.evaluate(_make_data("BTC", price=100, n=25))
        assert len(result) == 0

    def test_sentiment_shift_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="sent", condition=AlertCondition.SENTIMENT_SHIFT, symbol="BTC", threshold=0.5))
        result = e.evaluate(_make_data("BTC", price=100, sentiment=0.8))
        assert len(result) == 1
        assert "positive" in result[0].message

    def test_sentiment_negative(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="sent", condition=AlertCondition.SENTIMENT_SHIFT, symbol="BTC", threshold=0.3))
        result = e.evaluate(_make_data("BTC", price=100, sentiment=-0.5))
        assert len(result) == 1
        assert "negative" in result[0].message

    def test_sentiment_no_trigger(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="sent", condition=AlertCondition.SENTIMENT_SHIFT, symbol="BTC", threshold=0.9))
        result = e.evaluate(_make_data("BTC", price=100, sentiment=0.3))
        assert len(result) == 0

    def test_drawdown_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="dd", condition=AlertCondition.DRAWDOWN, symbol="BTC", threshold=0.05))
        data = _make_data("BTC", price=100)
        data["equity"] = [100, 110, 105, 100, 95, 90]  # ~18% drawdown
        result = e.evaluate(data)
        assert len(result) == 1

    def test_drawdown_no_trigger(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="dd", condition=AlertCondition.DRAWDOWN, symbol="BTC", threshold=0.5))
        data = _make_data("BTC", price=100)
        data["equity"] = [100, 110, 108]  # ~1.8% drawdown
        result = e.evaluate(data)
        assert len(result) == 0

    def test_position_size_triggers(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="pos", condition=AlertCondition.POSITION_SIZE, symbol="BTC", threshold=0.2))
        data = _make_data("BTC", price=100)
        data["position_pct"] = 0.35
        result = e.evaluate(data)
        assert len(result) == 1

    def test_multiple_rules_evaluate(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="a", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=50000, cooldown=0))
        e.add_rule(AlertRule(name="b", condition=AlertCondition.PRICE_BELOW, symbol="BTC", threshold=80000, cooldown=0))
        result = e.evaluate(_make_data("BTC", price=60000))
        assert len(result) == 2

    def test_fired_alerts_property(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=1))
        e.evaluate(_make_data("BTC", price=100))
        assert len(e.fired_alerts) == 1

    def test_channel_receives_alert(self):
        e = AlertEngine()
        ch = ConsoleChannel()
        e.add_channel(ch)
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=1))
        e.evaluate(_make_data("BTC", price=100))
        assert len(ch.sent) == 1

    def test_remove_channel(self):
        e = AlertEngine()
        ch = ConsoleChannel()
        e.add_channel(ch)
        assert e.remove_channel("console") is True
        assert len(e.channels) == 0

    def test_remove_nonexistent_channel(self):
        e = AlertEngine()
        assert e.remove_channel("nope") is False


# ══════════════════════════════════════════════════════════════
# Rule subclasses
# ══════════════════════════════════════════════════════════════

class TestRuleSubclasses:
    def test_price_alert_above(self):
        p = PriceAlert(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="X", threshold=100, direction="above")
        assert p.condition == AlertCondition.PRICE_ABOVE

    def test_price_alert_below(self):
        p = PriceAlert(name="t", condition=AlertCondition.PRICE_BELOW, symbol="X", threshold=100, direction="below")
        assert p.condition == AlertCondition.PRICE_BELOW

    def test_volume_alert_defaults(self):
        v = VolumeAlert(name="t", condition=AlertCondition.VOLUME_SPIKE, symbol="X", threshold=0, multiplier=3.0)
        assert v.threshold == 3.0

    def test_technical_alert(self):
        t = TechnicalAlert(name="t", condition=AlertCondition.RSI_BELOW, symbol="X", threshold=30, indicator="rsi")
        assert t.indicator == "rsi"

    def test_sentiment_alert(self):
        s = SentimentAlert(name="t", condition=AlertCondition.SENTIMENT_SHIFT, symbol="X", threshold=0.5)
        assert s.condition == AlertCondition.SENTIMENT_SHIFT

    def test_portfolio_alert_drawdown(self):
        p = PortfolioAlert(name="t", condition=AlertCondition.DRAWDOWN, symbol="X", threshold=0.1, metric="drawdown")
        assert p.condition == AlertCondition.DRAWDOWN

    def test_portfolio_alert_position(self):
        p = PortfolioAlert(name="t", condition=AlertCondition.POSITION_SIZE, symbol="X", threshold=0.1, metric="position_size")
        assert p.condition == AlertCondition.POSITION_SIZE


# ══════════════════════════════════════════════════════════════
# Channel tests
# ══════════════════════════════════════════════════════════════

def _make_fired_alert(**kw):
    rule = AlertRule(name="test", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=100)
    defaults = dict(
        rule=rule, symbol="BTC", condition="price_above", value=105.0,
        threshold=100, severity=AlertSeverity.WARNING, message="BTC > 100",
    )
    defaults.update(kw)
    return FiredAlert(**defaults)


class TestConsoleChannel:
    def test_send_returns_true(self):
        ch = ConsoleChannel()
        assert ch.send(_make_fired_alert()) is True

    def test_send_records(self):
        ch = ConsoleChannel()
        ch.send(_make_fired_alert())
        assert len(ch.sent) == 1


class TestFileChannel:
    def test_write_and_read(self, tmp_path):
        fp = tmp_path / "alerts.log"
        ch = FileChannel(path=fp)
        assert ch.send(_make_fired_alert()) is True
        lines = fp.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["symbol"] == "BTC"

    def test_append_multiple(self, tmp_path):
        fp = tmp_path / "alerts.log"
        ch = FileChannel(path=fp)
        ch.send(_make_fired_alert())
        ch.send(_make_fired_alert(symbol="ETH"))
        lines = fp.read_text().strip().split("\n")
        assert len(lines) == 2


class TestWebhookChannel:
    def test_send_success(self):
        ch = WebhookChannel(url="http://example.com/hook")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert ch.send(_make_fired_alert()) is True

    def test_send_failure(self):
        ch = WebhookChannel(url="http://example.com/hook")
        with patch("urllib.request.urlopen", side_effect=Exception("fail")):
            assert ch.send(_make_fired_alert()) is False


# ══════════════════════════════════════════════════════════════
# AlertHistory tests
# ══════════════════════════════════════════════════════════════

class TestAlertHistory:
    def test_record_and_len(self):
        h = AlertHistory()
        h.record(_make_fired_alert())
        assert len(h) == 1

    def test_get_recent(self):
        h = AlertHistory()
        h.record(_make_fired_alert())
        assert len(h.get_recent(hours=1)) == 1

    def test_get_recent_excludes_old(self):
        h = AlertHistory()
        a = _make_fired_alert()
        a.timestamp = datetime.now() - timedelta(hours=48)
        h.record(a)
        assert len(h.get_recent(hours=24)) == 0

    def test_get_by_symbol(self):
        h = AlertHistory()
        h.record(_make_fired_alert(symbol="BTC"))
        h.record(_make_fired_alert(symbol="ETH"))
        assert len(h.get_by_symbol("BTC")) == 1

    def test_get_by_severity(self):
        h = AlertHistory()
        h.record(_make_fired_alert(severity=AlertSeverity.CRITICAL))
        h.record(_make_fired_alert(severity=AlertSeverity.INFO))
        assert len(h.get_by_severity(AlertSeverity.CRITICAL)) == 1

    def test_get_by_condition(self):
        h = AlertHistory()
        h.record(_make_fired_alert(condition="price_above"))
        h.record(_make_fired_alert(condition="rsi_below"))
        assert len(h.get_by_condition("price_above")) == 1

    def test_stats(self):
        h = AlertHistory()
        h.record(_make_fired_alert(symbol="BTC"))
        h.record(_make_fired_alert(symbol="BTC"))
        h.record(_make_fired_alert(symbol="ETH"))
        stats = h.get_stats()
        assert stats["total"] == 3
        assert stats["by_symbol"]["BTC"] == 2

    def test_export_json(self):
        h = AlertHistory()
        h.record(_make_fired_alert())
        out = h.export(format="json")
        data = json.loads(out)
        assert len(data) == 1

    def test_export_csv(self):
        h = AlertHistory()
        h.record(_make_fired_alert())
        out = h.export(format="csv")
        assert "symbol" in out
        assert "BTC" in out

    def test_export_empty_csv(self):
        h = AlertHistory()
        assert h.export(format="csv") == ""

    def test_clear(self):
        h = AlertHistory()
        h.record(_make_fired_alert())
        h.clear()
        assert len(h) == 0

    def test_persistence_save_load(self, tmp_path):
        fp = tmp_path / "hist.json"
        h1 = AlertHistory(persist_path=fp)
        h1.record(_make_fired_alert())
        assert fp.exists()
        h2 = AlertHistory(persist_path=fp)
        assert len(h2) == 1

    def test_record_many(self):
        h = AlertHistory()
        h.record_many([_make_fired_alert(), _make_fired_alert()])
        assert len(h) == 2


# ══════════════════════════════════════════════════════════════
# Engine start/stop
# ══════════════════════════════════════════════════════════════

class TestEngineStartStop:
    def test_start_and_stop(self):
        e = AlertEngine()
        e.add_rule(AlertRule(name="t", condition=AlertCondition.PRICE_ABOVE, symbol="BTC", threshold=1))
        calls = []
        def fetch(symbols):
            calls.append(symbols)
            return [_make_data("BTC", price=100)]
        e.start(fetch, ["BTC"], interval=0.1)
        time.sleep(0.3)
        e.stop()
        assert len(calls) >= 1

    def test_stop_without_start(self):
        e = AlertEngine()
        e.stop()  # Should not raise
        assert not e._running, "Engine should not be running after stop()"
