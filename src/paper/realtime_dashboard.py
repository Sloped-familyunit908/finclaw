"""
RealtimeDashboard — live-updating paper trading dashboard.

Provides event-based notifications, periodic portfolio snapshots,
and rendering in both text and JSON formats for integration with
web UIs or terminal displays.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.paper.engine import PaperTradingEngine
from src.paper.dashboard import PaperDashboard


class DashboardEventType(str, Enum):
    """Types of events the dashboard can emit."""
    TRADE = "trade"
    PRICE_UPDATE = "price_update"
    PORTFOLIO_SNAPSHOT = "portfolio_snapshot"
    ALERT = "alert"


@dataclass
class DashboardEvent:
    """An event emitted by the real-time dashboard."""
    event_type: DashboardEventType
    data: dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class DashboardConfig:
    """Configuration for the real-time dashboard."""
    refresh_interval: float = 10.0  # seconds between auto-refresh
    max_history_points: int = 1000  # max equity snapshots to retain
    show_sparkline: bool = True
    show_recent_trades: int = 10


class RealtimeDashboard:
    """Live-updating paper trading dashboard with event subscriptions.

    Usage:
        engine = PaperTradingEngine(initial_balance=100000)
        dashboard = RealtimeDashboard(engine)
        dashboard.subscribe(my_callback)
        dashboard.start()
        # ... trade ...
        dashboard.stop()
    """

    def __init__(
        self,
        engine: PaperTradingEngine,
        config: DashboardConfig | None = None,
    ) -> None:
        self.engine = engine
        self.config = config or DashboardConfig()
        self._subscribers: list[Callable[[DashboardEvent], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._text_dashboard = PaperDashboard()
        self.equity_snapshots: list[tuple[float, float]] = []  # (timestamp, value)
        self._start_time = time.time()

    # ── subscriptions ───────────────────────────────────────────

    def subscribe(self, callback: Callable[[DashboardEvent], None]) -> None:
        """Register a callback for dashboard events."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[DashboardEvent], None]) -> None:
        """Remove a callback."""
        self._subscribers = [cb for cb in self._subscribers if cb is not callback]

    def _emit(self, event: DashboardEvent) -> None:
        """Emit an event to all subscribers."""
        for cb in self._subscribers:
            try:
                cb(event)
            except Exception:
                pass  # Don't let subscriber errors crash the dashboard

    # ── notifications ───────────────────────────────────────────

    def notify_trade(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> None:
        """Notify subscribers of a trade execution."""
        event = DashboardEvent(
            event_type=DashboardEventType.TRADE,
            data={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
            },
        )
        self._emit(event)

    def notify_price_update(self, prices: dict[str, float]) -> None:
        """Notify subscribers of price updates and record equity snapshot."""
        # Update engine price overrides
        for symbol, price in prices.items():
            self.engine.set_price(symbol, price)

        # Record equity
        self._record_equity()

        event = DashboardEvent(
            event_type=DashboardEventType.PRICE_UPDATE,
            data=prices,
        )
        self._emit(event)

    def _record_equity(self) -> None:
        """Record current portfolio value as an equity snapshot."""
        portfolio = self.engine.get_portfolio()
        self.equity_snapshots.append((time.time(), portfolio.total_value))
        # Trim to max
        if len(self.equity_snapshots) > self.config.max_history_points:
            self.equity_snapshots = self.equity_snapshots[-self.config.max_history_points:]

    # ── snapshots / rendering ───────────────────────────────────

    def get_snapshot(self) -> dict[str, Any]:
        """Get current dashboard state as a dict."""
        portfolio = self.engine.get_portfolio()
        pnl = self.engine.get_pnl()
        trades = self.engine.get_trade_history()

        positions = {}
        for sym, pos in portfolio.positions.items():
            positions[sym] = pos.to_dict()

        return {
            "portfolio": portfolio.to_dict(),
            "pnl": pnl.to_dict(),
            "positions": positions,
            "recent_trades": trades[-self.config.show_recent_trades:],
            "equity_history": list(self.equity_snapshots),
        }

    def render_text(self) -> str:
        """Render dashboard as formatted text."""
        return self._text_dashboard.render(self.engine)

    def render_json(self) -> dict[str, Any]:
        """Render dashboard as JSON-serializable dict."""
        return self.get_snapshot()

    def get_metrics(self) -> dict[str, Any]:
        """Get summary metrics for the trading session."""
        pnl = self.engine.get_pnl()
        return {
            "total_trades": pnl.total_trades,
            "total_pnl": pnl.total,
            "realized_pnl": pnl.realized,
            "unrealized_pnl": pnl.unrealized,
            "win_rate": pnl.win_rate,
            "win_count": pnl.win_count,
            "loss_count": pnl.loss_count,
            "uptime_seconds": time.time() - self._start_time,
        }

    # ── auto-refresh loop ──────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """Whether the auto-refresh loop is active."""
        return self._running

    def start(self) -> None:
        """Start the auto-refresh loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the auto-refresh loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _refresh_loop(self) -> None:
        """Periodically emit portfolio snapshot events."""
        while self._running:
            self._record_equity()
            snapshot = self.get_snapshot()
            event = DashboardEvent(
                event_type=DashboardEventType.PORTFOLIO_SNAPSHOT,
                data=snapshot,
            )
            self._emit(event)
            time.sleep(self.config.refresh_interval)
