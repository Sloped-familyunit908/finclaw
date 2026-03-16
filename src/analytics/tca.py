"""
Transaction Cost Analysis (TCA)
Decompose trading costs: commissions, slippage, market impact, opportunity cost.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TCAReport:
    """Comprehensive transaction cost breakdown."""
    # Totals
    total_cost_bps: float = 0.0       # total cost in basis points
    total_cost_dollars: float = 0.0
    commission_cost: float = 0.0
    slippage_cost: float = 0.0
    market_impact: float = 0.0
    opportunity_cost: float = 0.0

    # Breakdowns
    cost_by_ticker: dict[str, float] = field(default_factory=dict)
    cost_by_hour: dict[int, float] = field(default_factory=dict)
    cost_by_side: dict[str, float] = field(default_factory=dict)
    cost_by_size_bucket: dict[str, float] = field(default_factory=dict)

    # Per-trade stats
    avg_cost_bps: float = 0.0
    median_cost_bps: float = 0.0
    worst_cost_bps: float = 0.0
    best_cost_bps: float = 0.0
    n_trades: int = 0

    # As percentage of returns
    cost_as_pct_of_gross_return: float = 0.0

    def summary(self) -> str:
        lines = [
            "═══ Transaction Cost Analysis ═══",
            f"  Total Cost:       {self.total_cost_bps:>8.1f} bps  (${self.total_cost_dollars:,.2f})",
            f"    Commission:     {self._bps(self.commission_cost):>8.1f} bps  (${self.commission_cost:,.2f})",
            f"    Slippage:       {self._bps(self.slippage_cost):>8.1f} bps  (${self.slippage_cost:,.2f})",
            f"    Market Impact:  {self._bps(self.market_impact):>8.1f} bps  (${self.market_impact:,.2f})",
            f"    Opportunity:    {self._bps(self.opportunity_cost):>8.1f} bps  (${self.opportunity_cost:,.2f})",
            f"  Per Trade:  avg={self.avg_cost_bps:.1f}bps  "
            f"worst={self.worst_cost_bps:.1f}bps  best={self.best_cost_bps:.1f}bps",
            f"  Trades: {self.n_trades}   Cost/Gross Return: {self.cost_as_pct_of_gross_return:.1%}",
        ]
        if self.cost_by_ticker:
            lines.append("  By Ticker:")
            for ticker, cost in sorted(self.cost_by_ticker.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"    {ticker:>6}: ${cost:,.2f}")
        return "\n".join(lines)

    def _bps(self, dollar_cost: float) -> float:
        """Convert dollar cost to bps using total traded value."""
        if self.total_cost_dollars > 0 and self.total_cost_bps > 0:
            traded_value = self.total_cost_dollars / (self.total_cost_bps / 10_000)
            return (dollar_cost / max(traded_value, 1)) * 10_000
        return 0


@dataclass
class TradeFill:
    """Represents a single trade fill for TCA analysis."""
    ticker: str = ""
    side: str = "buy"          # "buy" or "sell"
    quantity: float = 0.0
    decision_price: float = 0.0  # price when signal was generated
    fill_price: float = 0.0      # actual execution price
    commission: float = 0.0
    fill_time_hour: int = 10     # hour of day (0-23)
    volume: float = 1_000_000    # market volume at time of trade
    pre_trade_price: Optional[float] = None
    post_trade_price: Optional[float] = None


class TCA:
    """
    Transaction Cost Analysis engine.
    Decomposes realized costs into commission, slippage, market impact,
    and opportunity cost components.
    """

    def __init__(self, risk_free_daily: float = 0.05 / 252):
        self.risk_free_daily = risk_free_daily

    def analyze(
        self,
        trades: list[TradeFill],
        gross_return: float = 0.0,
    ) -> TCAReport:
        """
        Analyze transaction costs from a list of fills.

        Args:
            trades: list of TradeFill objects
            gross_return: total gross return (before costs) in dollars
        """
        if not trades:
            return TCAReport()

        total_comm = 0.0
        total_slip = 0.0
        total_impact = 0.0
        total_opp = 0.0
        total_traded_value = 0.0

        by_ticker: dict[str, float] = {}
        by_hour: dict[int, float] = {}
        by_side: dict[str, float] = {}
        by_size: dict[str, float] = {"small": 0, "medium": 0, "large": 0}
        per_trade_bps: list[float] = []

        for t in trades:
            traded_value = abs(t.quantity * t.fill_price)
            total_traded_value += traded_value

            # Commission
            total_comm += t.commission

            # Slippage: difference between decision and fill price
            sign = 1 if t.side == "buy" else -1
            slip = sign * (t.fill_price - t.decision_price) * abs(t.quantity)
            slip = max(slip, 0)  # slippage is always a cost
            total_slip += slip

            # Market impact
            impact = 0.0
            if t.pre_trade_price and t.post_trade_price:
                impact = sign * (t.post_trade_price - t.pre_trade_price) * abs(t.quantity)
                impact = max(impact, 0)
            total_impact += impact

            # Opportunity cost: what if we'd filled at decision price?
            opp = abs(t.fill_price - t.decision_price) * abs(t.quantity) - slip
            opp = max(opp, 0)
            total_opp += opp

            # Per-trade cost in bps
            trade_cost = t.commission + slip + impact
            trade_bps = (trade_cost / max(traded_value, 1)) * 10_000
            per_trade_bps.append(trade_bps)

            # Breakdowns
            by_ticker[t.ticker] = by_ticker.get(t.ticker, 0) + trade_cost
            by_hour[t.fill_time_hour] = by_hour.get(t.fill_time_hour, 0) + trade_cost
            by_side[t.side] = by_side.get(t.side, 0) + trade_cost

            # Size buckets
            if traded_value < 10_000:
                by_size["small"] += trade_cost
            elif traded_value < 100_000:
                by_size["medium"] += trade_cost
            else:
                by_size["large"] += trade_cost

        total_cost = total_comm + total_slip + total_impact + total_opp
        total_bps = (total_cost / max(total_traded_value, 1)) * 10_000

        sorted_bps = sorted(per_trade_bps)
        n = len(sorted_bps)
        median_bps = sorted_bps[n // 2] if n else 0

        return TCAReport(
            total_cost_bps=total_bps,
            total_cost_dollars=total_cost,
            commission_cost=total_comm,
            slippage_cost=total_slip,
            market_impact=total_impact,
            opportunity_cost=total_opp,
            cost_by_ticker=by_ticker,
            cost_by_hour=by_hour,
            cost_by_side=by_side,
            cost_by_size_bucket=by_size,
            avg_cost_bps=sum(per_trade_bps) / max(n, 1),
            median_cost_bps=median_bps,
            worst_cost_bps=max(per_trade_bps, default=0),
            best_cost_bps=min(per_trade_bps, default=0),
            n_trades=n,
            cost_as_pct_of_gross_return=(
                total_cost / max(abs(gross_return), 0.01) if gross_return else 0
            ),
        )

    def from_backtest_trades(
        self,
        trades: list,  # list of TradeRecord from realistic.py
        decision_prices: Optional[dict[int, float]] = None,
    ) -> TCAReport:
        """
        Convert backtest TradeRecord objects into TCA analysis.

        Args:
            trades: list of TradeRecord from RealisticBacktester
            decision_prices: optional map of bar_index -> decision_price
        """
        fills = []
        gross = 0.0
        for t in trades:
            dec_price = t.entry_price
            if decision_prices and t.entry_bar in decision_prices:
                dec_price = decision_prices[t.entry_bar]

            fills.append(TradeFill(
                ticker=getattr(t, "ticker", ""),
                side=getattr(t, "side", "long"),
                quantity=getattr(t, "quantity", 1.0),
                decision_price=dec_price,
                fill_price=t.entry_price,
                commission=getattr(t, "commission", 0),
            ))
            gross += getattr(t, "pnl", 0)

        return self.analyze(fills, gross_return=gross)
