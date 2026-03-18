"""
DEPRECATED: Use `src.exchanges` for exchange adapters.

This module (`src.exchange`) is deprecated and will be removed in a future version.
The canonical exchange module is `src.exchanges`.

The `PaperTradingEngine` in this module is a legacy implementation.
For new code, use `src.paper.engine.PaperTradingEngine` instead.

All exports are re-exported here for backward compatibility.
"""

import warnings as _warnings

_warnings.warn(
    "src.exchange is deprecated. Use src.exchanges for exchange adapters "
    "or src.paper.engine for paper trading. "
    "This module will be removed in v6.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from .paper import PaperTradingEngine, Order, Position, OrderSide, OrderStatus

__all__ = ["PaperTradingEngine", "Order", "Position", "OrderSide", "OrderStatus"]
