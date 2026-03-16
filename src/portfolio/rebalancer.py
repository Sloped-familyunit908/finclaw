"""
Portfolio Rebalancer
Calendar, threshold, and tax-aware rebalancing strategies.
"""

import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class RebalanceFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


@dataclass
class Position:
    """A single portfolio position."""
    symbol: str
    shares: float
    current_price: float
    cost_basis: float           # average cost per share
    holding_days: int = 0       # days held (for tax-aware)

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.cost_basis) * self.shares

    @property
    def unrealized_pnl_pct(self) -> float:
        return (self.current_price / self.cost_basis - 1) if self.cost_basis > 0 else 0

    @property
    def is_short_term(self) -> bool:
        return self.holding_days < 365


@dataclass
class RebalanceAction:
    """A single rebalancing trade."""
    symbol: str
    action: str           # "buy" or "sell"
    shares: float
    estimated_value: float
    reason: str
    tax_impact: Optional[float] = None  # estimated tax on realized gain


@dataclass
class RebalanceResult:
    """Result of a rebalancing analysis."""
    actions: list[RebalanceAction]
    pre_weights: dict[str, float]
    post_weights: dict[str, float]
    target_weights: dict[str, float]
    total_turnover: float         # total value traded / portfolio value
    estimated_tax: float          # estimated total tax impact
    drift_before: float           # max drift from target before rebalance
    drift_after: float            # max drift after rebalance


class PortfolioRebalancer:
    """
    Portfolio rebalancer supporting multiple strategies.
    
    Usage:
        rebalancer = PortfolioRebalancer(
            target_weights={'SPY': 0.6, 'TLT': 0.3, 'GLD': 0.1},
            method='threshold',
            threshold=0.05,
        )
        result = rebalancer.rebalance(positions)
    """

    def __init__(
        self,
        target_weights: dict[str, float],
        method: str = "threshold",        # calendar, threshold, tax_aware
        threshold: float = 0.05,          # 5% drift trigger
        frequency: RebalanceFrequency = RebalanceFrequency.QUARTERLY,
        short_term_tax_rate: float = 0.37,
        long_term_tax_rate: float = 0.20,
        tax_loss_harvest: bool = False,
        min_trade_value: float = 100.0,   # skip tiny trades
    ):
        # Normalize target weights
        total = sum(target_weights.values())
        if total <= 0:
            raise ValueError("Target weights must sum to positive value")
        self.target_weights = {k: v / total for k, v in target_weights.items()}
        self.method = method
        self.threshold = threshold
        self.frequency = frequency
        self.short_term_tax_rate = short_term_tax_rate
        self.long_term_tax_rate = long_term_tax_rate
        self.tax_loss_harvest = tax_loss_harvest
        self.min_trade_value = min_trade_value

    def rebalance(
        self,
        positions: list[Position],
        day_of_period: int = 0,  # for calendar: day within period
    ) -> RebalanceResult:
        """Analyze and generate rebalancing trades."""
        portfolio_value = sum(p.market_value for p in positions)
        if portfolio_value <= 0:
            return RebalanceResult([], {}, {}, self.target_weights, 0, 0, 0, 0)

        pos_map = {p.symbol: p for p in positions}
        current_weights = {p.symbol: p.market_value / portfolio_value for p in positions}

        # Check if rebalance is needed
        max_drift = self._calc_max_drift(current_weights)

        if self.method == "calendar":
            needs_rebalance = self._calendar_trigger(day_of_period)
        elif self.method == "threshold":
            needs_rebalance = max_drift > self.threshold
        elif self.method == "tax_aware":
            needs_rebalance = max_drift > self.threshold
        else:
            raise ValueError(f"Unknown method: {self.method}")

        if not needs_rebalance:
            return RebalanceResult(
                actions=[], pre_weights=current_weights,
                post_weights=current_weights, target_weights=self.target_weights,
                total_turnover=0, estimated_tax=0,
                drift_before=max_drift, drift_after=max_drift,
            )

        # Generate trades
        if self.method == "tax_aware":
            actions = self._tax_aware_trades(pos_map, current_weights, portfolio_value)
        else:
            actions = self._simple_trades(pos_map, current_weights, portfolio_value)

        # Filter tiny trades
        actions = [a for a in actions if abs(a.estimated_value) >= self.min_trade_value]

        # Compute post-rebalance weights
        post_weights = dict(current_weights)
        for a in actions:
            delta = a.estimated_value if a.action == "buy" else -a.estimated_value
            post_weights[a.symbol] = post_weights.get(a.symbol, 0) + delta / portfolio_value

        turnover = sum(abs(a.estimated_value) for a in actions) / portfolio_value
        tax = sum(a.tax_impact or 0 for a in actions)
        drift_after = self._calc_max_drift(post_weights)

        return RebalanceResult(
            actions=actions,
            pre_weights=current_weights,
            post_weights=post_weights,
            target_weights=self.target_weights,
            total_turnover=round(turnover, 6),
            estimated_tax=round(tax, 2),
            drift_before=round(max_drift, 6),
            drift_after=round(drift_after, 6),
        )

    def needs_rebalance(self, positions: list[Position], day_of_period: int = 0) -> bool:
        """Quick check if rebalance is needed."""
        portfolio_value = sum(p.market_value for p in positions)
        if portfolio_value <= 0:
            return False
        current_weights = {p.symbol: p.market_value / portfolio_value for p in positions}
        max_drift = self._calc_max_drift(current_weights)

        if self.method == "calendar":
            return self._calendar_trigger(day_of_period)
        return max_drift > self.threshold

    def _calc_max_drift(self, current_weights: dict[str, float]) -> float:
        max_d = 0.0
        for sym, target_w in self.target_weights.items():
            current_w = current_weights.get(sym, 0)
            max_d = max(max_d, abs(current_w - target_w))
        return max_d

    def _calendar_trigger(self, day_of_period: int) -> bool:
        """Trigger on first day of period."""
        return day_of_period == 0

    def _simple_trades(
        self, pos_map: dict, current_weights: dict, portfolio_value: float,
    ) -> list[RebalanceAction]:
        actions = []
        for sym, target_w in self.target_weights.items():
            current_w = current_weights.get(sym, 0)
            diff_w = target_w - current_w
            trade_value = abs(diff_w * portfolio_value)

            if abs(diff_w) < 0.001:
                continue

            pos = pos_map.get(sym)
            price = pos.current_price if pos else 1.0
            shares = trade_value / price if price > 0 else 0

            action = "buy" if diff_w > 0 else "sell"
            tax_impact = None
            if action == "sell" and pos:
                realized_gain = min(trade_value, pos.unrealized_pnl * (shares / pos.shares) if pos.shares > 0 else 0)
                if realized_gain > 0:
                    rate = self.short_term_tax_rate if pos.is_short_term else self.long_term_tax_rate
                    tax_impact = round(realized_gain * rate, 2)

            actions.append(RebalanceAction(
                symbol=sym, action=action,
                shares=round(shares, 4),
                estimated_value=round(trade_value, 2),
                reason=f"Drift {diff_w:+.2%} from target {target_w:.1%}",
                tax_impact=tax_impact,
            ))
        return actions

    def _tax_aware_trades(
        self, pos_map: dict, current_weights: dict, portfolio_value: float,
    ) -> list[RebalanceAction]:
        """Tax-aware: prefer selling long-term gains and harvesting losses."""
        actions = []
        sells_needed = {}
        buys_needed = {}

        for sym, target_w in self.target_weights.items():
            current_w = current_weights.get(sym, 0)
            diff_w = target_w - current_w
            if abs(diff_w) < 0.001:
                continue
            if diff_w < 0:
                sells_needed[sym] = abs(diff_w)
            else:
                buys_needed[sym] = diff_w

        # Sort sells: prefer long-term gains, then losses (for harvesting)
        sell_order = sorted(
            sells_needed.keys(),
            key=lambda s: (
                0 if (pos_map.get(s) and not pos_map[s].is_short_term) else 1,
                pos_map[s].unrealized_pnl if pos_map.get(s) else 0,
            ),
        )

        for sym in sell_order:
            diff_w = sells_needed[sym]
            trade_value = diff_w * portfolio_value
            pos = pos_map.get(sym)
            price = pos.current_price if pos else 1.0
            shares = trade_value / price if price > 0 else 0

            tax_impact = None
            if pos and pos.unrealized_pnl > 0:
                gain_per_share = pos.current_price - pos.cost_basis
                realized = gain_per_share * shares
                rate = self.short_term_tax_rate if pos.is_short_term else self.long_term_tax_rate
                tax_impact = round(max(0, realized * rate), 2)
            elif pos and self.tax_loss_harvest and pos.unrealized_pnl < 0:
                # Tax loss harvesting: negative tax = tax benefit
                loss_per_share = pos.cost_basis - pos.current_price
                realized_loss = loss_per_share * shares
                rate = self.short_term_tax_rate  # losses offset at marginal rate
                tax_impact = round(-realized_loss * rate, 2)

            actions.append(RebalanceAction(
                symbol=sym, action="sell", shares=round(shares, 4),
                estimated_value=round(trade_value, 2),
                reason=f"Tax-aware sell: {'long-term' if pos and not pos.is_short_term else 'short-term'}",
                tax_impact=tax_impact,
            ))

        for sym, diff_w in buys_needed.items():
            trade_value = diff_w * portfolio_value
            pos = pos_map.get(sym)
            price = pos.current_price if pos else 1.0
            shares = trade_value / price if price > 0 else 0
            actions.append(RebalanceAction(
                symbol=sym, action="buy", shares=round(shares, 4),
                estimated_value=round(trade_value, 2),
                reason=f"Rebalance buy to target {self.target_weights[sym]:.1%}",
            ))

        return actions


class Rebalancer:
    """Simplified rebalancer matching the v4.5 spec API."""

    def __init__(self, target_weights: dict[str, float], threshold: float = 0.05):
        self.target_weights = target_weights
        self.threshold = threshold
        self._inner = PortfolioRebalancer(target_weights=target_weights, threshold=threshold)

    def check_drift(self, current_weights: dict[str, float]) -> dict:
        """Check drift of each asset from target."""
        drifts = {}
        max_drift = 0.0
        for sym, target in self.target_weights.items():
            current = current_weights.get(sym, 0.0)
            drift = current - target
            drifts[sym] = round(drift, 6)
            max_drift = max(max_drift, abs(drift))
        return {
            "drifts": drifts,
            "max_drift": round(max_drift, 6),
            "needs_rebalance": max_drift > self.threshold,
        }

    def generate_trades(self, current: dict[str, float], prices: dict[str, float]) -> list[dict]:
        """Generate trade list to rebalance.

        Args:
            current: {symbol: current_value}
            prices: {symbol: current_price}
        """
        total_value = sum(current.values())
        if total_value <= 0:
            return []

        trades = []
        for sym, target_w in self.target_weights.items():
            current_val = current.get(sym, 0.0)
            target_val = target_w * total_value
            diff = target_val - current_val
            price = prices.get(sym, 1.0)
            if abs(diff) < 1.0:
                continue
            trades.append({
                "symbol": sym,
                "action": "buy" if diff > 0 else "sell",
                "shares": round(abs(diff) / price, 4),
                "value": round(abs(diff), 2),
            })
        return trades

    def calendar_rebalance(self, frequency: str = "monthly") -> bool:
        """Check if calendar rebalance is due (stub: always True for day 0)."""
        return True

    def band_rebalance(self, current: dict[str, float]) -> bool:
        """Check if any asset breaches the band threshold."""
        total = sum(current.values())
        if total <= 0:
            return False
        weights = {s: v / total for s, v in current.items()}
        drift = self.check_drift(weights)
        return drift["needs_rebalance"]
