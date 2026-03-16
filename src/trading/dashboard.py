"""
FinClaw - Trading Dashboard
Text-based real-time trading dashboard for terminal output.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.trading.live_engine import LiveTradingEngine
    from src.trading.paper_trading import PaperTradingEngine
    from src.trading.risk_guard import RiskGuard

logger = logging.getLogger(__name__)


class TradingDashboard:
    """
    Text-based trading dashboard.
    Renders engine status, positions, orders, and risk as formatted text.
    """

    def __init__(
        self,
        engine: LiveTradingEngine | PaperTradingEngine,
        risk_guard: RiskGuard | None = None,
    ):
        self.engine = engine
        self.risk_guard = risk_guard

    def render(self) -> str:
        """Render the full dashboard as a string."""
        status = self.engine.get_status()
        lines: list[str] = []

        # Header
        mode = status.get("mode", "live").upper()
        exchange = status.get("exchange", "?")
        running = "🟢 RUNNING" if status.get("is_running") else "🔴 STOPPED"
        lines.append(f"📊 {mode} Trading Dashboard — {exchange} {running}")
        lines.append("═" * 60)

        # Balance / Equity
        if "virtual_balance" in status:
            equity = status.get("equity", 0)
            initial = status.get("initial_capital", 100_000)
            pnl = equity - initial
            pnl_pct = (pnl / initial * 100) if initial else 0
            sign = "+" if pnl >= 0 else ""
            lines.append(
                f"Balance: ${status['virtual_balance']:,.2f} | "
                f"Equity: ${equity:,.2f} | "
                f"PnL: {sign}${pnl:,.2f} ({sign}{pnl_pct:.1f}%)"
            )
        else:
            pnl = status.get("pnl", 0)
            sign = "+" if pnl >= 0 else ""
            lines.append(f"PnL: {sign}${pnl:,.2f}")

        # Positions
        positions = status.get("positions", {})
        if positions:
            pos_parts = []
            for ticker, info in positions.items():
                qty = info.get("quantity", info.get("qty", 0))
                price = info.get("avg_price", 0)
                pos_parts.append(f"{ticker} {qty} @ ${price:,.2f}")
            lines.append(f"Positions: {' | '.join(pos_parts)}")
        else:
            lines.append("Positions: (none)")

        # Orders
        open_orders = status.get("open_orders", 0)
        total_trades = status.get("total_trades", 0)
        lines.append(f"Orders: {open_orders} open | {total_trades} filled total")

        # Risk
        if self.risk_guard:
            risk = self.risk_guard.get_risk_status()
            daily_pnl = risk.get("daily_pnl", 0)
            daily_limit = risk.get("daily_loss_limit", 0)
            lines.append(
                f"Risk: Daily loss ${daily_pnl:,.2f} / -${daily_limit:,.2f} max | "
                f"Orders/min: {risk.get('orders_last_minute', 0)}/{risk.get('rate_limit', 0)}"
            )
            if risk.get("emergency_stopped"):
                lines.append("🚨 EMERGENCY STOP ACTIVE")

        # Uptime & errors
        uptime = status.get("uptime_seconds", 0)
        iterations = status.get("iterations", 0)
        errors = status.get("errors", 0)
        lines.append(f"Uptime: {self._format_duration(uptime)} | Ticks: {iterations} | Errors: {errors}")

        # Drawdown
        if "max_drawdown_pct" in status:
            lines.append(f"Max Drawdown: {status['max_drawdown_pct']:.1f}%")

        lines.append("═" * 60)
        return "\n".join(lines)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds into human-readable duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h {m}m"

    def print_dashboard(self) -> None:
        """Print dashboard to stdout."""
        print(self.render())
