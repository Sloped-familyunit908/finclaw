"""Position Tracker for FinClaw Backtest Engine v5.6.0

Tracks open positions, calculates P&L, and portfolio value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    side: PositionSide
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_cost: float = 0.0

    def __post_init__(self):
        self.total_cost = self.avg_price * self.quantity


class PositionTracker:
    """Tracks all positions and calculates P&L."""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        self._last_entry_price: float = 0.0  # For trade recording

    def open_position(self, symbol: str, quantity: float, price: float, side: str) -> Position:
        """Open or add to a position."""
        pos_side = PositionSide(side)

        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.side == pos_side:
                # Average into existing position
                total_cost = pos.avg_price * pos.quantity + price * quantity
                pos.quantity += quantity
                pos.avg_price = total_cost / pos.quantity if pos.quantity > 0 else 0
                pos.total_cost = pos.avg_price * pos.quantity
            else:
                # Opposite side — close existing first, then open remainder
                if quantity >= pos.quantity:
                    pnl = self._calc_pnl(pos, price, pos.quantity)
                    remainder = quantity - pos.quantity
                    self._record_close(pos, price, pos.quantity, pnl)
                    del self.positions[symbol]
                    if remainder > 0:
                        return self.open_position(symbol, remainder, price, side)
                else:
                    pnl = self._calc_pnl(pos, price, quantity)
                    pos.quantity -= quantity
                    pos.total_cost = pos.avg_price * pos.quantity
                    self._record_close(pos, price, quantity, pnl)
            self._last_entry_price = pos.avg_price
            return pos if symbol in self.positions else Position(symbol, 0, price, pos_side)
        else:
            pos = Position(symbol=symbol, quantity=quantity, avg_price=price, side=pos_side)
            self.positions[symbol] = pos
            self._last_entry_price = price
            return pos

    def close_position(self, symbol: str, quantity: float, price: float) -> float:
        """Close (fully or partially) a position. Returns realized PnL."""
        if symbol not in self.positions:
            self._last_entry_price = 0.0
            return 0.0

        pos = self.positions[symbol]
        self._last_entry_price = pos.avg_price
        close_qty = min(quantity, pos.quantity)
        pnl = self._calc_pnl(pos, price, close_qty)

        pos.realized_pnl += pnl
        pos.quantity -= close_qty
        pos.total_cost = pos.avg_price * pos.quantity

        self._record_close(pos, price, close_qty, pnl)

        if pos.quantity <= 0:
            del self.positions[symbol]

        return pnl

    def get_pnl(self, symbol: str, current_price: float) -> float:
        """Get unrealized P&L for a position."""
        if symbol not in self.positions:
            return 0.0
        pos = self.positions[symbol]
        return self._calc_pnl(pos, current_price, pos.quantity)

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Get total portfolio value (positions only, not cash)."""
        total = 0.0
        for symbol, pos in self.positions.items():
            price = prices.get(symbol, pos.avg_price)
            if pos.side == PositionSide.LONG:
                total += pos.quantity * price
            else:
                total += pos.quantity * (2 * pos.avg_price - price)
        return total

    def get_total_unrealized_pnl(self, prices: Dict[str, float]) -> float:
        """Get total unrealized P&L across all positions."""
        return sum(self.get_pnl(sym, prices.get(sym, 0)) for sym in self.positions)

    def _calc_pnl(self, pos: Position, price: float, quantity: float) -> float:
        if pos.side == PositionSide.LONG:
            return (price - pos.avg_price) * quantity
        else:
            return (pos.avg_price - price) * quantity

    def _record_close(self, pos: Position, price: float, quantity: float, pnl: float):
        self.closed_positions.append({
            "symbol": pos.symbol,
            "side": pos.side.value,
            "quantity": quantity,
            "entry_price": pos.avg_price,
            "exit_price": price,
            "pnl": pnl,
        })

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        return self.positions.get(symbol)

    def get_all_symbols(self) -> List[str]:
        return list(self.positions.keys())
