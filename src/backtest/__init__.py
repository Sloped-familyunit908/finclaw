"""FinClaw Enhanced Backtest Engine v5.6.0

Event-driven backtesting with proper order management, position tracking,
and Monte Carlo simulation.
"""

from .engine import (
    BacktestEngine,
    BacktestResult,
    EventType,
    Event,
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)
from .orders import OrderManager, Order, OrderType, OrderSide, OrderStatus
from .positions import PositionTracker, Position, PositionSide
from .monte_carlo import MonteCarloSimulator, MonteCarloResult

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "EventType",
    "Event",
    "MarketEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
    "OrderManager",
    "Order",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "PositionTracker",
    "Position",
    "PositionSide",
    "MonteCarloSimulator",
    "MonteCarloResult",
]
