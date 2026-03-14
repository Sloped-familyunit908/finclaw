"""
WhaleTrader - Paper Trading Engine
Simulates trades without real money. Default mode for safety.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    id: str
    asset: str
    side: OrderSide
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    reason: str = ""  # Why the agent made this trade


@dataclass
class Position:
    asset: str
    quantity: float
    avg_entry_price: float
    current_price: float = 0.0
    opened_at: datetime = field(default_factory=datetime.now)

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_entry_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_entry_price == 0:
            return 0
        return (self.current_price - self.avg_entry_price) / self.avg_entry_price


class PaperTradingEngine:
    """
    Paper trading engine that simulates real trading without actual money.
    Tracks positions, P&L, and order history.
    """

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, Position] = {}
        self.order_history: list[Order] = []
        self.trade_log: list[dict] = []
        self._order_counter = 0

    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + positions)"""
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    @property
    def total_pnl(self) -> float:
        """Total profit/loss since inception"""
        return self.total_value - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        """Total P&L as percentage"""
        return self.total_pnl / self.initial_capital

    def update_prices(self, prices: dict[str, float]):
        """Update current prices for all positions"""
        for asset, price in prices.items():
            if asset in self.positions:
                self.positions[asset].current_price = price

    def place_order(self, asset: str, side: OrderSide, quantity: float,
                    current_price: float, reason: str = "") -> Order:
        """
        Place a paper trade order. Executes immediately at current price.
        
        Args:
            asset: Asset symbol
            side: BUY or SELL
            quantity: Amount to trade
            current_price: Current market price
            reason: AI agent's reasoning for the trade
            
        Returns:
            Filled Order object
        """
        self._order_counter += 1
        order_id = f"PAPER-{self._order_counter:06d}"

        order = Order(
            id=order_id,
            asset=asset,
            side=side,
            quantity=quantity,
            price=current_price,
            reason=reason,
        )

        # Validate order
        if side == OrderSide.BUY:
            cost = quantity * current_price
            if cost > self.cash:
                order.status = OrderStatus.REJECTED
                order.reason = f"Insufficient cash. Need ${cost:,.2f}, have ${self.cash:,.2f}"
                self.order_history.append(order)
                return order
        elif side == OrderSide.SELL:
            if asset not in self.positions or self.positions[asset].quantity < quantity:
                available = self.positions[asset].quantity if asset in self.positions else 0
                order.status = OrderStatus.REJECTED
                order.reason = f"Insufficient position. Want to sell {quantity}, have {available}"
                self.order_history.append(order)
                return order

        # Execute order (paper trades fill immediately)
        order.status = OrderStatus.FILLED
        order.filled_price = current_price
        order.filled_at = datetime.now()

        if side == OrderSide.BUY:
            self._execute_buy(asset, quantity, current_price)
        else:
            self._execute_sell(asset, quantity, current_price)

        self.order_history.append(order)
        self._log_trade(order)

        return order

    def _execute_buy(self, asset: str, quantity: float, price: float):
        """Execute a buy order"""
        cost = quantity * price
        self.cash -= cost

        if asset in self.positions:
            pos = self.positions[asset]
            total_cost = (pos.avg_entry_price * pos.quantity) + cost
            pos.quantity += quantity
            pos.avg_entry_price = total_cost / pos.quantity
            pos.current_price = price
        else:
            self.positions[asset] = Position(
                asset=asset,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
            )

    def _execute_sell(self, asset: str, quantity: float, price: float):
        """Execute a sell order"""
        proceeds = quantity * price
        self.cash += proceeds

        pos = self.positions[asset]
        realized_pnl = (price - pos.avg_entry_price) * quantity

        pos.quantity -= quantity
        pos.current_price = price

        if pos.quantity <= 0.0001:  # Close position (float precision)
            del self.positions[asset]

        return realized_pnl

    def _log_trade(self, order: Order):
        """Log trade for analytics"""
        self.trade_log.append({
            "order_id": order.id,
            "asset": order.asset,
            "side": order.side.value,
            "quantity": order.quantity,
            "price": order.filled_price,
            "timestamp": order.filled_at.isoformat(),
            "reason": order.reason,
            "portfolio_value": self.total_value,
            "cash": self.cash,
        })

    def get_portfolio_summary(self) -> dict:
        """Get current portfolio summary"""
        positions_data = {}
        for asset, pos in self.positions.items():
            positions_data[asset] = {
                "quantity": pos.quantity,
                "avg_entry": pos.avg_entry_price,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": f"{pos.unrealized_pnl_pct:.2%}",
            }

        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "positions_value": sum(p.market_value for p in self.positions.values()),
            "total_value": self.total_value,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": f"{self.total_pnl_pct:.2%}",
            "num_positions": len(self.positions),
            "num_trades": len(self.trade_log),
            "positions": positions_data,
        }

    def __repr__(self):
        return (f"<PaperTradingEngine: ${self.total_value:,.2f} "
                f"({self.total_pnl_pct:+.2%}) | "
                f"{len(self.positions)} positions | "
                f"{len(self.trade_log)} trades>")
