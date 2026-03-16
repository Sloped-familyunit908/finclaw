"""
FinClaw Tax Calculator v3.5.0
Capital gains tax calculation with wash sale detection and tax-loss harvesting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaxLot:
    ticker: str
    buy_date: str
    buy_price: float
    shares: float
    sell_date: Optional[str] = None
    sell_price: Optional[float] = None

    @property
    def is_long_term(self) -> bool:
        if not self.sell_date:
            return False
        buy = datetime.fromisoformat(self.buy_date)
        sell = datetime.fromisoformat(self.sell_date)
        return (sell - buy).days > 365

    @property
    def gain(self) -> float:
        if self.sell_price is None:
            return 0.0
        return (self.sell_price - self.buy_price) * self.shares

    @property
    def cost_basis(self) -> float:
        return self.buy_price * self.shares


# Default US tax rates (2024 simplified)
US_TAX_RATES = {
    "short_term": 0.37,   # Ordinary income top rate
    "long_term": 0.20,    # Long-term capital gains top rate
}

TAX_RATES = {
    "US": US_TAX_RATES,
    "UK": {"short_term": 0.20, "long_term": 0.20},
    "DE": {"short_term": 0.26375, "long_term": 0.26375},  # Abgeltungsteuer
}


class TaxCalculator:
    """
    Capital gains tax calculator with wash sale detection
    and tax-loss harvesting optimization.
    """

    def __init__(self, jurisdiction: str = "US"):
        self.jurisdiction = jurisdiction
        self.rates = TAX_RATES.get(jurisdiction, US_TAX_RATES)

    def calculate(self, trades: list[dict]) -> dict:
        """
        Calculate taxes from a list of trades.

        Each trade: {ticker, action (buy/sell), date, price, shares}

        Returns:
            {short_term_gains, long_term_gains, total_tax,
             wash_sales, tax_lots, harvest_opportunities}
        """
        lots = self._build_lots(trades)
        wash_sales = self._detect_wash_sales(trades, lots)
        wash_tickers_dates = {(w["ticker"], w["sell_date"]) for w in wash_sales}

        short_term = 0.0
        long_term = 0.0
        for lot in lots:
            if lot.sell_price is None:
                continue
            # Skip wash sale adjustments
            if (lot.ticker, lot.sell_date) in wash_tickers_dates:
                continue
            if lot.is_long_term:
                long_term += lot.gain
            else:
                short_term += lot.gain

        total_tax = (
            max(0, short_term) * self.rates["short_term"]
            + max(0, long_term) * self.rates["long_term"]
        )

        harvest = self._find_harvest_opportunities(lots)

        return {
            "short_term_gains": round(short_term, 2),
            "long_term_gains": round(long_term, 2),
            "total_tax": round(total_tax, 2),
            "wash_sales": wash_sales,
            "tax_lots": [
                {
                    "ticker": l.ticker,
                    "buy_date": l.buy_date,
                    "sell_date": l.sell_date,
                    "gain": round(l.gain, 2),
                    "is_long_term": l.is_long_term,
                }
                for l in lots if l.sell_price is not None
            ],
            "harvest_opportunities": harvest,
        }

    def _build_lots(self, trades: list[dict]) -> list[TaxLot]:
        """Match buys to sells using FIFO."""
        open_lots: dict[str, list[TaxLot]] = {}
        closed_lots: list[TaxLot] = []

        for t in sorted(trades, key=lambda x: x["date"]):
            ticker = t["ticker"]
            if t["action"] == "buy":
                lot = TaxLot(
                    ticker=ticker,
                    buy_date=t["date"],
                    buy_price=t["price"],
                    shares=t["shares"],
                )
                open_lots.setdefault(ticker, []).append(lot)
            elif t["action"] == "sell":
                remaining = t["shares"]
                queue = open_lots.get(ticker, [])
                while remaining > 0 and queue:
                    lot = queue[0]
                    if lot.shares <= remaining:
                        lot.sell_date = t["date"]
                        lot.sell_price = t["price"]
                        closed_lots.append(lot)
                        remaining -= lot.shares
                        queue.pop(0)
                    else:
                        # Partial sell — split lot
                        sold = TaxLot(
                            ticker=ticker,
                            buy_date=lot.buy_date,
                            buy_price=lot.buy_price,
                            shares=remaining,
                            sell_date=t["date"],
                            sell_price=t["price"],
                        )
                        closed_lots.append(sold)
                        lot.shares -= remaining
                        remaining = 0

        # Include remaining open lots
        for queue in open_lots.values():
            closed_lots.extend(queue)
        return closed_lots

    def _detect_wash_sales(
        self, trades: list[dict], lots: list[TaxLot]
    ) -> list[dict]:
        """Detect wash sales (repurchase within 30 days of a loss)."""
        wash_sales = []
        sells_at_loss = [
            l for l in lots
            if l.sell_price is not None and l.gain < 0
        ]
        buys = [t for t in trades if t["action"] == "buy"]

        for lot in sells_at_loss:
            sell_dt = datetime.fromisoformat(lot.sell_date)
            for buy in buys:
                if buy["ticker"] != lot.ticker:
                    continue
                buy_dt = datetime.fromisoformat(buy["date"])
                delta = (buy_dt - sell_dt).days
                if -30 <= delta <= 30 and buy["date"] != lot.buy_date:
                    wash_sales.append({
                        "ticker": lot.ticker,
                        "sell_date": lot.sell_date,
                        "buy_date": buy["date"],
                        "disallowed_loss": round(abs(lot.gain), 2),
                    })
                    break
        return wash_sales

    def _find_harvest_opportunities(self, lots: list[TaxLot]) -> list[dict]:
        """Find open lots with unrealized losses for harvesting."""
        return [
            {
                "ticker": l.ticker,
                "buy_date": l.buy_date,
                "cost_basis": round(l.cost_basis, 2),
                "shares": l.shares,
            }
            for l in lots
            if l.sell_price is None
        ]

    def optimize_harvesting(
        self, portfolio: dict, losses_needed: float
    ) -> list[dict]:
        """
        Suggest positions to sell for tax-loss harvesting.

        Args:
            portfolio: {ticker: {shares, cost_basis, current_price}}
            losses_needed: Target loss amount to harvest.

        Returns list of suggested sells sorted by loss magnitude.
        """
        candidates = []
        for ticker, pos in portfolio.items():
            unrealized = (pos["current_price"] - pos["cost_basis"]) * pos["shares"]
            if unrealized < 0:
                candidates.append({
                    "ticker": ticker,
                    "shares": pos["shares"],
                    "unrealized_loss": round(abs(unrealized), 2),
                    "cost_basis": pos["cost_basis"],
                    "current_price": pos["current_price"],
                })
        candidates.sort(key=lambda x: x["unrealized_loss"], reverse=True)

        result = []
        harvested = 0.0
        for c in candidates:
            if harvested >= losses_needed:
                break
            result.append(c)
            harvested += c["unrealized_loss"]
        return result
