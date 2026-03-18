"""
DEPRECATED: Use ``src.backtesting`` for all backtesting functionality.

This module (``src.backtest``) is deprecated and will be removed in v6.0.
The canonical backtesting module is ``src.backtesting``, which now contains
the core engine, order management, positions, and Monte Carlo simulation
(all previously housed here) plus extended analysis tools.

All exports are re-exported here for backward compatibility.
"""

import warnings as _warnings

_warnings.warn(
    "src.backtest is deprecated. Use src.backtesting for all backtesting "
    "functionality. This module will be removed in v6.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical module's core engine
from src.backtesting.core_engine import (
    BacktestEngine,
    BacktestResult,
    EventType,
    Event,
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)
from src.backtesting.orders import OrderManager, Order, OrderType, OrderSide, OrderStatus
from src.backtesting.positions import PositionTracker, Position, PositionSide
from src.backtesting.core_monte_carlo import MonteCarloSimulator, MonteCarloResult

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
