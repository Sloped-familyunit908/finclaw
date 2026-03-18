"""
Paper Trading Engine - simulated order execution with real market prices.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    status: OrderStatus
    price: float = 0.0
    filled_price: float = 0.0
    limit_price: float | None = None
    timestamp: float = 0.0
    fill_timestamp: float = 0.0
    reject_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "price": self.price,
            "filled_price": self.filled_price,
            "limit_price": self.limit_price,
            "timestamp": self.timestamp,
            "fill_timestamp": self.fill_timestamp,
            "reject_reason": self.reject_reason,
        }


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": self.avg_cost,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
        }


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, Position]
    total_value: float
    initial_balance: float

    @property
    def positions_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_return(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return ((self.total_value - self.initial_balance) / self.initial_balance) * 100

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "positions_value": self.positions_value,
            "total_value": self.total_value,
            "initial_balance": self.initial_balance,
            "total_return": self.total_return,
        }


@dataclass
class PnL:
    realized: float
    unrealized: float
    total: float
    total_return_pct: float
    win_count: int
    loss_count: int
    total_trades: int

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.win_count / self.total_trades) * 100

    def to_dict(self) -> dict:
        return {
            "realized": self.realized,
            "unrealized": self.unrealized,
            "total": self.total,
            "total_return_pct": self.total_return_pct,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
        }


def _fetch_price(symbol: str, exchange: str = "yahoo") -> float | None:
    """Fetch current price for a symbol."""
    try:
        if exchange == "yahoo":
            import yfinance as yf
            import logging
            import warnings

            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = yf.Ticker(symbol)
                info = t.fast_info
                price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
                if price:
                    return float(price)
                hist = t.history(period="1d")
                if not hist.empty:
                    return float(hist["Close"].iloc[-1])
        else:
            from src.exchanges.registry import ExchangeRegistry

            adapter = ExchangeRegistry.get(exchange)
            ticker = adapter.get_ticker(symbol)
            return float(ticker.get("last", 0))
    except Exception as e:
        logger.warning("Failed to fetch price for %s via %s: %s", symbol, exchange, e)
    return None


class PaperTradingEngine:
    """Simulated trading engine with real market prices."""

    def __init__(self, initial_balance: float = 100000, exchange: str = "yahoo"):
        if initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.exchange = exchange
        self.positions: dict[str, Position] = {}
        self.orders: list[Order] = []
        self.trade_log: list[dict] = []
        self._realized_pnl = 0.0
        self._equity_history: list[tuple[float, float]] = []  # (timestamp, value)
        self._price_overrides: dict[str, float] = {}  # for testing

    def _get_price(self, symbol: str) -> float | None:
        """Get price, checking overrides first (for testing)."""
        if symbol in self._price_overrides:
            return self._price_overrides[symbol]
        return _fetch_price(symbol, self.exchange)

    def set_price(self, symbol: str, price: float) -> None:
        """Override price for a symbol (useful for testing)."""
        self._price_overrides[symbol] = price

    def clear_price_overrides(self) -> None:
        self._price_overrides.clear()

    def buy(self, symbol: str, quantity: float, order_type: str = "market", limit_price: float | None = None) -> Order:
        """Place a buy order."""
        if quantity <= 0:
            return self._rejected_order(symbol, OrderSide.BUY, quantity, f"Invalid quantity: must be positive, got {quantity}")

        otype = OrderType(order_type)
        now = time.time()

        if otype == OrderType.MARKET:
            price = self._get_price(symbol)
            if price is None:
                return self._rejected_order(symbol, OrderSide.BUY, quantity, f"Cannot fetch price for {symbol}")

            cost = price * quantity
            if cost > self.balance:
                return self._rejected_order(symbol, OrderSide.BUY, quantity, f"Insufficient funds: need ${cost:,.2f}, have ${self.balance:,.2f}")

            self.balance -= cost

            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = pos.avg_cost * pos.quantity + price * quantity
                pos.quantity += quantity
                pos.avg_cost = total_cost / pos.quantity
                pos.current_price = price
            else:
                self.positions[symbol] = Position(symbol=symbol, quantity=quantity, avg_cost=price, current_price=price)

            order = Order(
                id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=otype,
                status=OrderStatus.FILLED,
                price=price,
                filled_price=price,
                timestamp=now,
                fill_timestamp=now,
            )
            self.orders.append(order)
            self.trade_log.append({
                "order_id": order.id,
                "symbol": symbol,
                "side": "BUY",
                "quantity": quantity,
                "price": price,
                "cost": cost,
                "timestamp": now,
            })
            self._record_equity()
            return order

        elif otype == OrderType.LIMIT:
            if limit_price is None:
                return self._rejected_order(symbol, OrderSide.BUY, quantity, "Limit price required")
            order = Order(
                id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=otype,
                status=OrderStatus.PENDING,
                limit_price=limit_price,
                timestamp=now,
            )
            self.orders.append(order)
            return order

        return self._rejected_order(symbol, OrderSide.BUY, quantity, f"Unknown order type: {order_type}")

    def sell(self, symbol: str, quantity: float, order_type: str = "market", limit_price: float | None = None) -> Order:
        """Place a sell order."""
        if quantity <= 0:
            return self._rejected_order(symbol, OrderSide.SELL, quantity, f"Invalid quantity: must be positive, got {quantity}")

        if symbol not in self.positions:
            return self._rejected_order(symbol, OrderSide.SELL, quantity, f"No position in {symbol}")

        if self.positions[symbol].quantity < quantity:
            return self._rejected_order(symbol, OrderSide.SELL, quantity, f"Insufficient shares: have {self.positions[symbol].quantity}, want {quantity}")

        otype = OrderType(order_type)
        now = time.time()

        if otype == OrderType.MARKET:
            price = self._get_price(symbol)
            if price is None:
                return self._rejected_order(symbol, OrderSide.SELL, quantity, f"Cannot fetch price for {symbol}")

            proceeds = price * quantity
            pos = self.positions[symbol]
            trade_pnl = (price - pos.avg_cost) * quantity
            self._realized_pnl += trade_pnl
            self.balance += proceeds

            pos.quantity -= quantity
            pos.current_price = price
            if pos.quantity <= 0:
                del self.positions[symbol]

            order = Order(
                id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=otype,
                status=OrderStatus.FILLED,
                price=price,
                filled_price=price,
                timestamp=now,
                fill_timestamp=now,
            )
            self.orders.append(order)
            self.trade_log.append({
                "order_id": order.id,
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": price,
                "proceeds": proceeds,
                "pnl": trade_pnl,
                "timestamp": now,
            })
            self._record_equity()
            return order

        elif otype == OrderType.LIMIT:
            if limit_price is None:
                return self._rejected_order(symbol, OrderSide.SELL, quantity, "Limit price required")
            order = Order(
                id=str(uuid.uuid4())[:8],
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=otype,
                status=OrderStatus.PENDING,
                limit_price=limit_price,
                timestamp=now,
            )
            self.orders.append(order)
            return order

        return self._rejected_order(symbol, OrderSide.SELL, quantity, f"Unknown order type: {order_type}")

    def _rejected_order(self, symbol: str, side: OrderSide, quantity: float, reason: str) -> Order:
        order = Order(
            id=str(uuid.uuid4())[:8],
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.REJECTED,
            timestamp=time.time(),
        )
        order.price = 0
        order.reject_reason = reason
        self.orders.append(order)
        return order

    def get_portfolio(self) -> Portfolio:
        """Get current portfolio snapshot."""
        for sym, pos in self.positions.items():
            price = self._get_price(sym)
            if price is not None:
                pos.current_price = price

        positions_value = sum(p.market_value for p in self.positions.values())
        total = self.balance + positions_value

        return Portfolio(
            cash=self.balance,
            positions=dict(self.positions),
            total_value=total,
            initial_balance=self.initial_balance,
        )

    def get_pnl(self) -> PnL:
        """Calculate realized + unrealized P&L."""
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())

        sells = [t for t in self.trade_log if t["side"] == "SELL"]
        win_count = sum(1 for t in sells if t.get("pnl", 0) > 0)
        loss_count = sum(1 for t in sells if t.get("pnl", 0) < 0)

        total = self._realized_pnl + unrealized
        total_return = (total / self.initial_balance) * 100 if self.initial_balance else 0

        return PnL(
            realized=self._realized_pnl,
            unrealized=unrealized,
            total=total,
            total_return_pct=total_return,
            win_count=win_count,
            loss_count=loss_count,
            total_trades=len(sells),
        )

    def get_trade_history(self) -> list[dict]:
        """Return chronological trade log."""
        return list(self.trade_log)

    def get_equity_history(self) -> list[tuple[float, float]]:
        """Return equity curve data points."""
        return list(self._equity_history)

    def _record_equity(self) -> None:
        positions_value = sum(p.market_value for p in self.positions.values())
        total = self.balance + positions_value
        self._equity_history.append((time.time(), total))

    def reset(self) -> None:
        """Reset engine to initial state."""
        self.balance = self.initial_balance
        self.positions.clear()
        self.orders.clear()
        self.trade_log.clear()
        self._realized_pnl = 0.0
        self._equity_history.clear()
        self._price_overrides.clear()
