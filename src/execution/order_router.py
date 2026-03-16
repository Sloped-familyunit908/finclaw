"""Order Router for FinClaw execution layer.

Routes orders to execution venues (mock by default).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    symbol: str
    quantity: float
    side: str = "buy"  # buy / sell
    order_type: str = "market"  # market / limit
    limit_price: Optional[float] = None
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    venue: str = "mock"


@dataclass
class OrderResult:
    order_id: str
    status: OrderStatus
    fill_price: float = 0.0
    filled_quantity: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockVenue:
    """Simulated exchange that fills everything at requested price."""

    def execute(self, order: Order, market_price: Optional[float] = None) -> OrderResult:
        price = market_price or order.limit_price or 100.0
        return OrderResult(
            order_id=order.order_id,
            status=OrderStatus.FILLED,
            fill_price=price,
            filled_quantity=order.quantity,
        )


class OrderRouter:
    """Routes orders to execution venues.

    Usage:
        router = OrderRouter()
        result = router.submit(order)
        status = router.get_status(order.order_id)
    """

    def __init__(self, default_venue: str = "mock"):
        self.default_venue = default_venue
        self._venues = {"mock": MockVenue()}
        self._orders: Dict[str, Order] = {}
        self._results: Dict[str, OrderResult] = {}

    def register_venue(self, name: str, venue: Any):
        """Register a custom execution venue."""
        self._venues[name] = venue

    def submit(self, order: Order, market_price: Optional[float] = None) -> OrderResult:
        """Submit an order for execution."""
        venue_name = order.venue or self.default_venue
        venue = self._venues.get(venue_name)
        if venue is None:
            result = OrderResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message=f"Unknown venue: {venue_name}",
            )
            self._results[order.order_id] = result
            return result

        self._orders[order.order_id] = order
        result = venue.execute(order, market_price)
        self._results[order.order_id] = result
        return result

    def cancel(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if cancelled."""
        result = self._results.get(order_id)
        if result and result.status == OrderStatus.PENDING:
            result.status = OrderStatus.CANCELLED
            return True
        return False

    def get_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status by ID."""
        result = self._results.get(order_id)
        return result.status if result else None

    def pending_orders(self) -> List[Order]:
        """Return all pending orders."""
        return [
            self._orders[oid]
            for oid, result in self._results.items()
            if result.status == OrderStatus.PENDING
        ]

    def all_results(self) -> Dict[str, OrderResult]:
        """Return all order results."""
        return dict(self._results)
