"""
FinClaw - Risk Guard
Real-time risk management with pre-trade checks, daily limits,
position limits, and emergency kill switch.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time
from typing import Any

from src.trading.oms import Order

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_position_size: float = 100_000.0       # max $ in single position
    max_daily_loss: float = 5_000.0            # max daily loss before halt
    max_order_value: float = 50_000.0          # max single order value
    max_orders_per_minute: int = 10            # rate limit
    max_open_positions: int = 10               # max concurrent positions
    max_portfolio_exposure: float = 0.95       # max % of capital invested
    allowed_symbols: list[str] = field(default_factory=list)  # empty = all allowed
    trading_hours: tuple[str, str] | None = None  # ("09:30", "16:00") or None for 24/7
    capital: float = 100_000.0                 # total capital for % calculations


@dataclass
class RiskResult:
    """Result of a risk check."""
    approved: bool
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


class RiskGuard:
    """
    Pre-trade risk manager.
    Checks every order against position, loss, rate, and time constraints.
    """

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()
        self._daily_pnl: float = 0.0
        self._daily_date: str = ""
        self._order_timestamps: deque[float] = deque()
        self._emergency_stopped: bool = False
        self._daily_trades: int = 0

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check_order(self, order: Order, portfolio: dict[str, Any]) -> RiskResult:
        """
        Run all risk checks against an order.
        Returns RiskResult with approved=True/False and reason.
        """
        warnings: list[str] = []

        # Emergency stop
        if self._emergency_stopped:
            return RiskResult(False, "Emergency stop active — all trading halted")

        # Daily loss limit
        if not self.check_daily_limit():
            return RiskResult(False, f"Daily loss limit reached: ${self._daily_pnl:.2f} / -${self.config.max_daily_loss:.2f}")

        # Trading hours
        if not self._check_trading_hours():
            return RiskResult(False, "Outside trading hours")

        # Symbol allowed
        if self.config.allowed_symbols and order.ticker not in self.config.allowed_symbols:
            return RiskResult(False, f"Symbol {order.ticker} not in allowed list")

        # Order value
        price = order.limit_price or order.stop_price or 0
        order_value = order.quantity * price
        if order_value > self.config.max_order_value:
            return RiskResult(
                False,
                f"Order value ${order_value:,.2f} exceeds max ${self.config.max_order_value:,.2f}",
            )

        # Position size
        if order.side == "buy":
            positions = portfolio.get("positions", {})
            existing = positions.get(order.ticker, {})
            existing_value = existing.get("quantity", 0) * existing.get("avg_price", 0)
            new_total = existing_value + order_value
            if new_total > self.config.max_position_size:
                return RiskResult(
                    False,
                    f"Position size ${new_total:,.2f} exceeds max ${self.config.max_position_size:,.2f}",
                )

        # Max open positions
        positions = portfolio.get("positions", {})
        open_count = sum(1 for p in positions.values() if isinstance(p, dict) and p.get("quantity", 0) > 0)
        if order.side == "buy" and order.ticker not in positions and open_count >= self.config.max_open_positions:
            return RiskResult(
                False,
                f"Max open positions ({self.config.max_open_positions}) reached",
            )

        # Rate limit
        if not self._check_rate_limit():
            return RiskResult(False, f"Rate limit: max {self.config.max_orders_per_minute} orders/min")

        # Portfolio exposure
        if order.side == "buy" and self.config.capital > 0:
            total_invested = sum(
                p.get("quantity", 0) * p.get("avg_price", 0)
                for p in positions.values()
                if isinstance(p, dict)
            )
            exposure = (total_invested + order_value) / self.config.capital
            if exposure > self.config.max_portfolio_exposure:
                warnings.append(f"High exposure: {exposure:.1%}")
                return RiskResult(False, f"Portfolio exposure {exposure:.1%} exceeds max {self.config.max_portfolio_exposure:.0%}")

        # Record order
        self._order_timestamps.append(time.time())

        return RiskResult(True, "Approved", warnings)

    # ------------------------------------------------------------------
    # Specific checks
    # ------------------------------------------------------------------

    def check_daily_limit(self) -> bool:
        """Check if daily loss limit has been breached."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._daily_date != today:
            self._daily_pnl = 0.0
            self._daily_date = today
            self._daily_trades = 0
        return self._daily_pnl > -self.config.max_daily_loss

    def update_pnl(self, pnl_change: float) -> None:
        """Update daily PnL tracking."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._daily_date != today:
            self._daily_pnl = 0.0
            self._daily_date = today
        self._daily_pnl += pnl_change
        self._daily_trades += 1

    def emergency_stop(self) -> None:
        """Activate emergency kill switch — blocks all new orders."""
        self._emergency_stopped = True
        logger.critical("🚨 EMERGENCY STOP ACTIVATED — all trading halted")

    def reset_emergency(self) -> None:
        """Deactivate emergency stop."""
        self._emergency_stopped = False
        logger.info("Emergency stop deactivated")

    @property
    def is_emergency_stopped(self) -> bool:
        return self._emergency_stopped

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        if self.config.trading_hours is None:
            return True

        start_str, end_str = self.config.trading_hours
        now = datetime.now().time()
        start = dt_time(*map(int, start_str.split(":")))
        end = dt_time(*map(int, end_str.split(":")))

        if start <= end:
            return start <= now <= end
        else:
            # Overnight session (e.g., 22:00 - 06:00)
            return now >= start or now <= end

    def _check_rate_limit(self) -> bool:
        """Check orders-per-minute rate limit."""
        now = time.time()
        cutoff = now - 60.0
        while self._order_timestamps and self._order_timestamps[0] < cutoff:
            self._order_timestamps.popleft()
        return len(self._order_timestamps) < self.config.max_orders_per_minute

    def get_risk_status(self) -> dict[str, Any]:
        """Return current risk state."""
        return {
            "emergency_stopped": self._emergency_stopped,
            "daily_pnl": round(self._daily_pnl, 2),
            "daily_loss_limit": self.config.max_daily_loss,
            "daily_loss_remaining": round(self.config.max_daily_loss + self._daily_pnl, 2),
            "daily_trades": self._daily_trades,
            "orders_last_minute": len(self._order_timestamps),
            "rate_limit": self.config.max_orders_per_minute,
            "within_trading_hours": self._check_trading_hours(),
        }
