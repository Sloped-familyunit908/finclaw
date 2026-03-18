"""Order Management System for FinClaw Backtest Engine v5.6.0

Supports: market, limit, stop, trailing stop, and OCO (one-cancels-other) orders.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    TRAILING_STOP = "trailing_stop"
    OCO = "oco"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


@dataclass
class Order:
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None       # limit price
    stop_price: Optional[float] = None   # stop trigger price
    trail_pct: Optional[float] = None    # trailing stop percentage
    take_profit: Optional[float] = None  # OCO take profit
    stop_loss: Optional[float] = None    # OCO stop loss
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    timestamp: Any = None
    # Internal: tracking for trailing stop
    _trail_high: float = 0.0
    _trail_low: float = float('inf')
    # Internal: linked OCO order
    _linked_order_id: Optional[str] = None


class OrderManager:
    """Manages order creation, tracking, and pending order checks."""

    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.cancelled_orders: List[Order] = []

    def market_order(self, symbol: str, quantity: float, side: str) -> Order:
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide(side),
            order_type=OrderType.MARKET,
        )
        self.orders[order.order_id] = order
        # Market orders fill immediately — don't add to pending
        return order

    def limit_order(self, symbol: str, quantity: float, price: float, side: str) -> Order:
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide(side),
            order_type=OrderType.LIMIT,
            price=price,
        )
        self.orders[order.order_id] = order
        self.pending_orders.append(order)
        return order

    def stop_order(self, symbol: str, quantity: float, stop_price: float, side: str) -> Order:
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide(side),
            order_type=OrderType.STOP,
            stop_price=stop_price,
        )
        self.orders[order.order_id] = order
        self.pending_orders.append(order)
        return order

    def trailing_stop(self, symbol: str, quantity: float, trail_pct: float, side: str) -> Order:
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide(side),
            order_type=OrderType.TRAILING_STOP,
            trail_pct=trail_pct,
        )
        self.orders[order.order_id] = order
        self.pending_orders.append(order)
        return order

    def oco_order(self, symbol: str, quantity: float, take_profit: float, stop_loss: float) -> tuple[Order, Order]:
        """One-Cancels-Other: creates a take-profit limit sell and a stop-loss sell."""
        tp_order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=take_profit,
            take_profit=take_profit,
        )
        sl_order = Order(
            symbol=symbol,
            quantity=quantity,
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            stop_price=stop_loss,
            stop_loss=stop_loss,
        )
        tp_order._linked_order_id = sl_order.order_id
        sl_order._linked_order_id = tp_order.order_id

        self.orders[tp_order.order_id] = tp_order
        self.orders[sl_order.order_id] = sl_order
        self.pending_orders.append(tp_order)
        self.pending_orders.append(sl_order)
        return tp_order, sl_order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                self.pending_orders = [o for o in self.pending_orders if o.order_id != order_id]
                self.cancelled_orders.append(order)
                return True
        return False

    def check_pending(self, symbol: str, market_event: Any) -> List[Order]:
        """Check pending orders against current market data. Returns triggered orders."""
        triggered: List[Order] = []
        remaining: List[Order] = []

        high = getattr(market_event, 'high', 0.0)
        low = getattr(market_event, 'low', 0.0)
        close = getattr(market_event, 'close', 0.0)

        for order in self.pending_orders:
            if order.symbol != symbol or order.status != OrderStatus.PENDING:
                remaining.append(order)
                continue

            filled = False

            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and low <= (order.price or 0):
                    order.status = OrderStatus.FILLED
                    order.filled_price = order.price or close
                    filled = True
                elif order.side == OrderSide.SELL and high >= (order.price or 0):
                    order.status = OrderStatus.FILLED
                    order.filled_price = order.price or close
                    filled = True

            elif order.order_type == OrderType.STOP:
                if order.side == OrderSide.SELL and low <= (order.stop_price or 0):
                    order.status = OrderStatus.FILLED
                    order.filled_price = order.stop_price or close
                    filled = True
                elif order.side == OrderSide.BUY and high >= (order.stop_price or 0):
                    order.status = OrderStatus.FILLED
                    order.filled_price = order.stop_price or close
                    filled = True

            elif order.order_type == OrderType.TRAILING_STOP:
                trail_pct = order.trail_pct or 0.0
                if order.side == OrderSide.SELL:
                    order._trail_high = max(order._trail_high, high)
                    trail_price = order._trail_high * (1 - trail_pct)
                    if low <= trail_price:
                        order.status = OrderStatus.FILLED
                        order.filled_price = trail_price
                        filled = True
                else:
                    order._trail_low = min(order._trail_low, low)
                    trail_price = order._trail_low * (1 + trail_pct)
                    if high >= trail_price:
                        order.status = OrderStatus.FILLED
                        order.filled_price = trail_price
                        filled = True

            if filled:
                order.filled_quantity = order.quantity
                triggered.append(order)
                self.filled_orders.append(order)
                # Cancel linked OCO order
                if order._linked_order_id:
                    self.cancel_order(order._linked_order_id)
            else:
                remaining.append(order)

        self.pending_orders = remaining
        return triggered

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    def get_pending_count(self) -> int:
        return len(self.pending_orders)
