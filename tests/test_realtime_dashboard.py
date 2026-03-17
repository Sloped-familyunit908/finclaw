"""Tests for Issue #2: Real-time paper trading dashboard.

Tests the real-time dashboard features:
- Live position updates with WebSocket-style callbacks
- Auto-refresh dashboard rendering
- Portfolio metrics streaming
- Dashboard state management
- Equity curve tracking in real-time
"""

import time
import threading
from unittest.mock import MagicMock, patch

import pytest

from src.paper.engine import PaperTradingEngine, OrderStatus
from src.paper.dashboard import PaperDashboard, _sparkline
from src.paper.realtime_dashboard import (
    RealtimeDashboard,
    DashboardConfig,
    DashboardEvent,
    DashboardEventType,
)


# ── sparkline helper ────────────────────────────────────────────

class TestSparkline:
    def test_empty_values(self):
        assert _sparkline([]) == ""

    def test_single_value(self):
        result = _sparkline([42.0])
        assert len(result) == 1

    def test_monotonic_increasing(self):
        result = _sparkline([1, 2, 3, 4, 5], width=5)
        assert len(result) == 5
        # First should be lowest block, last should be highest
        assert result[0] < result[-1]

    def test_constant_values(self):
        result = _sparkline([10, 10, 10, 10], width=4)
        assert len(result) == 4

    def test_longer_than_width(self):
        values = list(range(100))
        result = _sparkline(values, width=10)
        assert len(result) == 10


# ── DashboardConfig ─────────────────────────────────────────────

class TestDashboardConfig:
    def test_default_config(self):
        cfg = DashboardConfig()
        assert cfg.refresh_interval > 0
        assert cfg.max_history_points > 0
        assert cfg.show_sparkline is True

    def test_custom_config(self):
        cfg = DashboardConfig(refresh_interval=5.0, max_history_points=500, show_sparkline=False)
        assert cfg.refresh_interval == 5.0
        assert cfg.max_history_points == 500
        assert cfg.show_sparkline is False


# ── DashboardEvent ──────────────────────────────────────────────

class TestDashboardEvent:
    def test_trade_event(self):
        evt = DashboardEvent(
            event_type=DashboardEventType.TRADE,
            data={"symbol": "AAPL", "side": "BUY", "quantity": 10, "price": 150.0},
        )
        assert evt.event_type == DashboardEventType.TRADE
        assert evt.data["symbol"] == "AAPL"
        assert evt.timestamp > 0

    def test_price_update_event(self):
        evt = DashboardEvent(
            event_type=DashboardEventType.PRICE_UPDATE,
            data={"AAPL": 151.0, "MSFT": 401.0},
        )
        assert evt.event_type == DashboardEventType.PRICE_UPDATE

    def test_portfolio_snapshot_event(self):
        evt = DashboardEvent(
            event_type=DashboardEventType.PORTFOLIO_SNAPSHOT,
            data={"total_value": 100500, "cash": 50000},
        )
        assert evt.event_type == DashboardEventType.PORTFOLIO_SNAPSHOT


# ── RealtimeDashboard ──────────────────────────────────────────

class TestRealtimeDashboard:
    def _make_engine(self):
        engine = PaperTradingEngine(initial_balance=100000)
        engine.set_price("AAPL", 150.0)
        engine.set_price("MSFT", 400.0)
        return engine

    def test_create_with_engine(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        assert dashboard.engine is engine
        assert dashboard.is_running is False

    def test_create_with_config(self):
        engine = self._make_engine()
        cfg = DashboardConfig(refresh_interval=2.0)
        dashboard = RealtimeDashboard(engine, config=cfg)
        assert dashboard.config.refresh_interval == 2.0

    def test_subscribe_callback(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        events_received = []
        dashboard.subscribe(lambda evt: events_received.append(evt))
        # Trigger an event by executing a trade
        engine.buy("AAPL", 10)
        dashboard.notify_trade("AAPL", "BUY", 10, 150.0)
        assert len(events_received) == 1
        assert events_received[0].event_type == DashboardEventType.TRADE

    def test_multiple_subscribers(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        cb1_events = []
        cb2_events = []
        dashboard.subscribe(lambda evt: cb1_events.append(evt))
        dashboard.subscribe(lambda evt: cb2_events.append(evt))
        dashboard.notify_trade("AAPL", "BUY", 10, 150.0)
        assert len(cb1_events) == 1
        assert len(cb2_events) == 1

    def test_unsubscribe(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        events = []
        cb = lambda evt: events.append(evt)
        dashboard.subscribe(cb)
        dashboard.unsubscribe(cb)
        dashboard.notify_trade("AAPL", "BUY", 10, 150.0)
        assert len(events) == 0

    def test_get_snapshot(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        engine.buy("AAPL", 10)
        snap = dashboard.get_snapshot()
        assert "portfolio" in snap
        assert "pnl" in snap
        assert "positions" in snap
        assert "recent_trades" in snap
        assert "equity_history" in snap

    def test_get_snapshot_empty_portfolio(self):
        engine = PaperTradingEngine(initial_balance=50000)
        dashboard = RealtimeDashboard(engine)
        snap = dashboard.get_snapshot()
        assert snap["portfolio"]["cash"] == 50000
        assert len(snap["positions"]) == 0

    def test_notify_price_update(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        events = []
        dashboard.subscribe(lambda evt: events.append(evt))
        dashboard.notify_price_update({"AAPL": 155.0, "MSFT": 405.0})
        assert len(events) == 1
        assert events[0].event_type == DashboardEventType.PRICE_UPDATE

    def test_price_update_records_equity(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        engine.buy("AAPL", 10)
        initial_equity_len = len(dashboard.equity_snapshots)
        dashboard.notify_price_update({"AAPL": 160.0})
        assert len(dashboard.equity_snapshots) > initial_equity_len

    def test_render_dashboard_text(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        engine.buy("AAPL", 10)
        text = dashboard.render_text()
        assert "PAPER TRADING" in text
        assert "AAPL" in text

    def test_render_dashboard_json(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        engine.buy("AAPL", 10)
        data = dashboard.render_json()
        assert isinstance(data, dict)
        assert "portfolio" in data
        assert "pnl" in data

    def test_equity_history_max_points(self):
        engine = self._make_engine()
        cfg = DashboardConfig(max_history_points=5)
        dashboard = RealtimeDashboard(engine, config=cfg)
        for i in range(10):
            dashboard.notify_price_update({"AAPL": 150.0 + i})
        assert len(dashboard.equity_snapshots) <= 5

    def test_start_stop(self):
        engine = self._make_engine()
        cfg = DashboardConfig(refresh_interval=0.01)
        dashboard = RealtimeDashboard(engine, config=cfg)
        events = []
        dashboard.subscribe(lambda evt: events.append(evt))
        dashboard.start()
        assert dashboard.is_running is True
        time.sleep(0.05)
        dashboard.stop()
        assert dashboard.is_running is False
        # Should have received at least one portfolio snapshot
        snapshot_events = [e for e in events if e.event_type == DashboardEventType.PORTFOLIO_SNAPSHOT]
        assert len(snapshot_events) >= 1

    def test_metrics_summary(self):
        engine = self._make_engine()
        dashboard = RealtimeDashboard(engine)
        engine.buy("AAPL", 10)
        engine.set_price("AAPL", 160.0)
        engine.sell("AAPL", 10)
        metrics = dashboard.get_metrics()
        assert "total_trades" in metrics
        assert "total_pnl" in metrics
        assert "win_rate" in metrics
        assert "uptime_seconds" in metrics
