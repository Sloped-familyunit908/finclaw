"""
Tax Lot Tracker — FIFO, LIFO, SpecificID, HighestCost, TaxOptimal disposal methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class TaxLot:
    """A single tax lot."""
    symbol: str
    shares: float
    price: float          # cost basis per share
    date: date
    lot_id: int = 0

    @property
    def cost_basis(self) -> float:
        return self.shares * self.price

    @property
    def holding_days(self) -> int:
        return (date.today() - self.date).days

    @property
    def is_long_term(self) -> bool:
        return self.holding_days >= 365

    def gain_at(self, current_price: float) -> float:
        return (current_price - self.price) * self.shares


@dataclass
class TaxResult:
    """Result of a sale for tax purposes."""
    symbol: str
    shares_sold: float
    proceeds: float
    cost_basis: float
    realized_gain: float
    is_long_term: bool
    lots_used: list[dict]
    method: str


@dataclass
class HarvestCandidate:
    """A tax-loss harvesting candidate."""
    symbol: str
    unrealized_loss: float
    shares: float
    current_price: float
    cost_basis_per_share: float
    is_long_term: bool


class TaxLotTracker:
    """Track tax lots for multiple symbols with various disposal methods."""

    def __init__(self, short_term_rate: float = 0.37, long_term_rate: float = 0.20):
        self._lots: dict[str, list[TaxLot]] = {}
        self._next_id: int = 1
        self.short_term_rate = short_term_rate
        self.long_term_rate = long_term_rate

    def add_lot(self, symbol: str, shares: float, price: float, dt: date) -> TaxLot:
        """Record a purchase as a new tax lot."""
        if shares <= 0:
            raise ValueError("Shares must be positive")
        if price < 0:
            raise ValueError("Price must be non-negative")
        lot = TaxLot(symbol=symbol, shares=shares, price=price, date=dt, lot_id=self._next_id)
        self._next_id += 1
        self._lots.setdefault(symbol, []).append(lot)
        return lot

    def sell(
        self,
        symbol: str,
        shares: float,
        price: float,
        dt: date,
        method: str = "FIFO",
    ) -> TaxResult:
        """Sell shares using specified disposal method.

        Methods: FIFO, LIFO, SpecificID, HighestCost, TaxOptimal
        """
        if symbol not in self._lots or not self._lots[symbol]:
            raise ValueError(f"No lots for {symbol}")

        available = sum(lot.shares for lot in self._lots[symbol])
        if shares > available + 1e-9:
            raise ValueError(f"Insufficient shares for {symbol}: have {available}, selling {shares}")

        lots = self._lots[symbol]
        ordered = self._order_lots(lots, method, price, dt)

        remaining = shares
        lots_used = []
        total_cost = 0.0
        is_lt = True  # all long-term?

        for lot in ordered:
            if remaining <= 1e-9:
                break
            used = min(lot.shares, remaining)
            cost = used * lot.price
            total_cost += cost
            lot_lt = (dt - lot.date).days >= 365

            lots_used.append({
                "lot_id": lot.lot_id,
                "shares": round(used, 6),
                "cost_basis": round(cost, 2),
                "purchase_date": lot.date.isoformat(),
                "is_long_term": lot_lt,
            })

            if not lot_lt:
                is_lt = False

            lot.shares -= used
            remaining -= used

        # Clean up empty lots
        self._lots[symbol] = [l for l in self._lots[symbol] if l.shares > 1e-9]

        proceeds = shares * price
        gain = proceeds - total_cost

        return TaxResult(
            symbol=symbol,
            shares_sold=round(shares, 6),
            proceeds=round(proceeds, 2),
            cost_basis=round(total_cost, 2),
            realized_gain=round(gain, 2),
            is_long_term=is_lt,
            lots_used=lots_used,
            method=method,
        )

    def unrealized_gains(self, current_prices: dict[str, float]) -> dict:
        """Calculate unrealized gains per symbol and total.

        Returns:
            {symbol: {shares, cost_basis, market_value, unrealized_gain, unrealized_pct}, 'total': ...}
        """
        result = {}
        total_cost = 0.0
        total_value = 0.0

        for symbol, lots in self._lots.items():
            if not lots:
                continue
            price = current_prices.get(symbol, 0.0)
            shares = sum(l.shares for l in lots)
            cost = sum(l.cost_basis for l in lots)
            value = shares * price
            gain = value - cost

            result[symbol] = {
                "shares": round(shares, 6),
                "cost_basis": round(cost, 2),
                "market_value": round(value, 2),
                "unrealized_gain": round(gain, 2),
                "unrealized_pct": round(gain / cost, 6) if cost > 0 else 0.0,
            }
            total_cost += cost
            total_value += value

        result["total"] = {
            "cost_basis": round(total_cost, 2),
            "market_value": round(total_value, 2),
            "unrealized_gain": round(total_value - total_cost, 2),
        }
        return result

    def tax_loss_harvest(
        self,
        current_prices: dict[str, float],
        threshold: float = 0.0,
    ) -> list[HarvestCandidate]:
        """Identify positions with unrealized losses exceeding threshold.

        Args:
            current_prices: {symbol: current_price}
            threshold: minimum loss amount to include (positive number)

        Returns:
            list of HarvestCandidate sorted by loss magnitude (largest first)
        """
        candidates = []
        for symbol, lots in self._lots.items():
            price = current_prices.get(symbol, 0.0)
            for lot in lots:
                loss = lot.gain_at(price)
                if loss < -abs(threshold):
                    candidates.append(HarvestCandidate(
                        symbol=symbol,
                        unrealized_loss=round(loss, 2),
                        shares=lot.shares,
                        current_price=price,
                        cost_basis_per_share=lot.price,
                        is_long_term=lot.is_long_term,
                    ))

        candidates.sort(key=lambda c: c.unrealized_loss)  # most negative first
        return candidates

    def get_lots(self, symbol: str | None = None) -> list[TaxLot]:
        """Get all lots, optionally filtered by symbol."""
        if symbol:
            return list(self._lots.get(symbol, []))
        return [lot for lots in self._lots.values() for lot in lots]

    def _order_lots(
        self,
        lots: list[TaxLot],
        method: str,
        sale_price: float,
        sale_date: date,
    ) -> list[TaxLot]:
        """Order lots by disposal method."""
        if method == "FIFO":
            return sorted(lots, key=lambda l: l.date)
        elif method == "LIFO":
            return sorted(lots, key=lambda l: l.date, reverse=True)
        elif method == "HighestCost":
            return sorted(lots, key=lambda l: l.price, reverse=True)
        elif method == "SpecificID":
            return list(lots)  # Caller manages order
        elif method == "TaxOptimal":
            return self._tax_optimal_order(lots, sale_price, sale_date)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _tax_optimal_order(
        self,
        lots: list[TaxLot],
        sale_price: float,
        sale_date: date,
    ) -> list[TaxLot]:
        """Order to minimize tax: sell losses first, then long-term gains, then short-term."""
        def tax_score(lot: TaxLot) -> tuple:
            gain = (sale_price - lot.price) * lot.shares
            is_lt = (sale_date - lot.date).days >= 365
            if gain <= 0:
                return (0, gain)  # Losses first (most negative first)
            elif is_lt:
                return (1, gain)  # Long-term gains (lower rate)
            else:
                return (2, gain)  # Short-term gains last

        return sorted(lots, key=tax_score)
