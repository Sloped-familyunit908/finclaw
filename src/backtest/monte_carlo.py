"""Monte Carlo Simulation for FinClaw Backtest Engine v5.6.0

Reshuffles trade sequences to generate confidence intervals for strategy metrics.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    n_simulations: int = 0
    returns_mean: float = 0.0
    returns_median: float = 0.0
    returns_p5: float = 0.0
    returns_p25: float = 0.0
    returns_p75: float = 0.0
    returns_p95: float = 0.0
    max_dd_mean: float = 0.0
    max_dd_p95: float = 0.0
    var_95: float = 0.0
    expected_max_drawdown: float = 0.0
    ruin_probability: float = 0.0
    sharpe_mean: float = 0.0
    all_returns: List[float] = field(default_factory=list)
    all_drawdowns: List[float] = field(default_factory=list)
    all_final_equities: List[float] = field(default_factory=list)


class MonteCarloSimulator:
    """Monte Carlo simulation by reshuffling trade sequences."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self._result: Optional[MonteCarloResult] = None

    def simulate(
        self,
        trades: List[Dict[str, Any]],
        n_simulations: int = 1000,
        initial_capital: float = 100_000,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation by reshuffling trade P&L sequence.

        Args:
            trades: List of trade dicts with 'pnl' key.
            n_simulations: Number of simulations.
            initial_capital: Starting capital.

        Returns:
            MonteCarloResult with confidence intervals.
        """
        if not trades:
            self._result = MonteCarloResult()
            return self._result

        pnls = [t.get("pnl", 0.0) for t in trades]

        all_returns = []
        all_drawdowns = []
        all_final_equities = []
        all_sharpes = []

        for _ in range(n_simulations):
            shuffled = pnls[:]
            self.rng.shuffle(shuffled)

            equity = initial_capital
            peak = equity
            max_dd = 0.0
            period_returns = []

            for pnl in shuffled:
                prev = equity
                equity += pnl
                equity = max(equity, 0.01)
                peak = max(peak, equity)
                dd = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
                if prev > 0:
                    period_returns.append((equity - prev) / prev)

            total_ret = (equity / initial_capital) - 1
            all_returns.append(total_ret)
            all_drawdowns.append(max_dd)
            all_final_equities.append(equity)

            # Sharpe approximation
            if len(period_returns) > 1:
                mean_r = sum(period_returns) / len(period_returns)
                var_r = sum((r - mean_r) ** 2 for r in period_returns) / (len(period_returns) - 1)
                std_r = math.sqrt(var_r) if var_r > 0 else 0.001
                sharpe = (mean_r / std_r) * math.sqrt(252)
            else:
                sharpe = 0.0
            all_sharpes.append(sharpe)

        all_returns.sort()
        all_drawdowns.sort()
        n = len(all_returns)

        def pctl(arr, p):
            idx = min(max(int(len(arr) * p), 0), len(arr) - 1)
            return arr[idx]

        ruin_count = sum(1 for r in all_returns if r < -0.5)

        self._result = MonteCarloResult(
            n_simulations=n_simulations,
            returns_mean=sum(all_returns) / n,
            returns_median=pctl(all_returns, 0.5),
            returns_p5=pctl(all_returns, 0.05),
            returns_p25=pctl(all_returns, 0.25),
            returns_p75=pctl(all_returns, 0.75),
            returns_p95=pctl(all_returns, 0.95),
            max_dd_mean=sum(all_drawdowns) / n,
            max_dd_p95=pctl(all_drawdowns, 0.95),
            var_95=pctl(all_returns, 0.05),  # VaR at 95% confidence = 5th pctl
            expected_max_drawdown=sum(all_drawdowns) / n,
            ruin_probability=ruin_count / n if n > 0 else 0.0,
            sharpe_mean=sum(all_sharpes) / n,
            all_returns=all_returns,
            all_drawdowns=all_drawdowns,
            all_final_equities=all_final_equities,
        )
        return self._result

    def var_95(self) -> float:
        """Value at Risk at 95% confidence (5th percentile of return distribution)."""
        if not self._result:
            return 0.0
        return self._result.var_95

    def expected_max_drawdown(self) -> float:
        """Expected maximum drawdown (mean of simulated max drawdowns)."""
        if not self._result:
            return 0.0
        return self._result.expected_max_drawdown

    def ruin_probability(self, threshold: float = -0.5) -> float:
        """Probability of ruin (return below threshold)."""
        if not self._result or not self._result.all_returns:
            return 0.0
        n = len(self._result.all_returns)
        return sum(1 for r in self._result.all_returns if r < threshold) / n
