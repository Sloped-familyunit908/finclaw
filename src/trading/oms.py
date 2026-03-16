"""
FinClaw - Order Management System (OMS)
Manages order lifecycle: submission, validation, fill simulation, cancellation.
Integrates with EventBus for trade notifications.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.events.event_bus import EventBus, TRADE_EXECUTED


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"       # good til cancelled
    IOC = "ioc"       # immediate or cancel
    FOK = "fok"       # fill or kill


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    ticker: str
    side: str          # "buy" / "sell"
    order_type: str    # "market" / "limit" / "stop" / "stop_limit"
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    # Managed fields
    order_id: str = field(default_factory=lambda: f"ORD-{uuid.uuid4().hex[:8]}")
    status: str = "pending"
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    reject_reason: str = ""

    @property
    def is_active(self) -> bool:
        return self.status in ("pending", "open", "partially_filled")


@dataclass
class OrderResult:
    order_id: str
    status: str
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    message: str = ""


class OrderManager:
    """
    Order Management System.
    Validates, tracks, and simulates fills for paper trading orders.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._orders: dict[str, Order] = {}
        self._event_bus = event_bus

    def submit_order(self, order: Order) -> OrderResult:
        """Validate and submit an order. Market orders fill immediately at limit_price."""
        # Basic validation
        if order.quantity <= 0:
            order.status = "rejected"
            order.reject_reason = "Quantity must be positive"
            self._orders[order.order_id] = order
            return OrderResult(order.order_id, "rejected", message=order.reject_reason)

        if order.order_type == "limit" and order.limit_price is None:
            order.status = "rejected"
            order.reject_reason = "Limit order requires limit_price"
            self._orders[order.order_id] = order
            return OrderResult(order.order_id, "rejected", message=order.reject_reason)

        if order.order_type in ("stop", "stop_limit") and order.stop_price is None:
            order.status = "rejected"
            order.reject_reason = "Stop order requires stop_price"
            self._orders[order.order_id] = order
            return OrderResult(order.order_id, "rejected", message=order.reject_reason)

        # Market orders fill immediately (paper trading)
        if order.order_type == "market":
            return self._fill_order(order, order.limit_price or 0.0)

        # Non-market orders go to open state
        order.status = "open"
        order.updated_at = time.time()
        self._orders[order.order_id] = order
        return OrderResult(order.order_id, "open", message="Order placed")

    def _fill_order(self, order: Order, price: float) -> OrderResult:
        """Fill an order at the given price."""
        order.status = "filled"
        order.filled_quantity = order.quantity
        order.filled_price = price
        order.updated_at = time.time()
        self._orders[order.order_id] = order

        if self._event_bus:
            self._event_bus.publish(TRADE_EXECUTED, {
                "order_id": order.order_id,
                "ticker": order.ticker,
                "side": order.side,
                "quantity": order.filled_quantity,
                "price": price,
            }, source="oms")

        return OrderResult(order.order_id, "filled", order.quantity, price, "Filled")

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True if cancelled."""
        order = self._orders.get(order_id)
        if not order or not order.is_active:
            return False
        order.status = "cancelled"
        order.updated_at = time.time()
        return True

    def get_open_orders(self) -> list[Order]:
        """All active orders."""
        return [o for o in self._orders.values() if o.is_active]

    def get_order_history(self) -> list[Order]:
        """All orders sorted by creation time."""
        return sorted(self._orders.values(), key=lambda o: o.created_at)

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def check_stops_and_limits(self, prices: dict[str, float]) -> list[OrderResult]:
        """Check open limit/stop orders against current prices and fill if triggered."""
        results = []
        for order in list(self._orders.values()):
            if not order.is_active or order.order_type == "market":
                continue
            price = prices.get(order.ticker)
            if price is None:
                continue

            triggered = False
            fill_price = price

            if order.order_type == "limit":
                if order.side == "buy" and price <= order.limit_price:
                    triggered = True
                    fill_price = order.limit_price
                elif order.side == "sell" and price >= order.limit_price:
                    triggered = True
                    fill_price = order.limit_price

            elif order.order_type == "stop":
                if order.side == "buy" and price >= order.stop_price:
                    triggered = True
                elif order.side == "sell" and price <= order.stop_price:
                    triggered = True

            elif order.order_type == "stop_limit":
                if order.side == "buy" and price >= order.stop_price:
                    fill_price = order.limit_price
                    triggered = price <= order.limit_price
                elif order.side == "sell" and price <= order.stop_price:
                    fill_price = order.limit_price
                    triggered = price >= order.limit_price

            if triggered:
                results.append(self._fill_order(order, fill_price))

        return results
