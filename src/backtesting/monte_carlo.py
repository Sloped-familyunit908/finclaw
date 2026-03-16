"""
Monte Carlo Simulation
Randomize trade ordering to assess strategy robustness.
Produces confidence intervals for key metrics.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from agents.backtester import BacktestResult, Trade


@dataclass
class MonteCarloReport:
    """Results from Monte Carlo simulation."""
    n_simulations: int
    returns_mean: float
    returns_median: float
    returns_p5: float   # 5th percentile (worst case)
    returns_p25: float
    returns_p75: float
    returns_p95: float  # 95th percentile (best case)
    max_dd_mean: float
    max_dd_p5: float    # worst-case drawdown
    sharpe_mean: float
    sharpe_p5: float
    ruin_probability: float  # % of sims with return < -50%
    all_returns: list[float] = field(default_factory=list)
    all_drawdowns: list[float] = field(default_factory=list)

    def summary(self) -> str:
        return "\n".join([
            f"=== Monte Carlo Simulation ({self.n_simulations} runs) ===",
            f"Return: mean={self.returns_mean:+.2%}, median={self.returns_median:+.2%}",
            f"  5th pctl: {self.returns_p5:+.2%}  |  95th pctl: {self.returns_p95:+.2%}",
            f"Max Drawdown: mean={self.max_dd_mean:.2%}, worst={self.max_dd_p5:.2%}",
            f"Sharpe: mean={self.sharpe_mean:.2f}, 5th pctl={self.sharpe_p5:.2f}",
            f"Ruin Probability (< -50%): {self.ruin_probability:.1%}",
        ])


class MonteCarloSimulator:
    """Randomize trade order to test strategy robustness."""

    def __init__(self, n_simulations: int = 1000, seed: Optional[int] = None):
        self.n_simulations = n_simulations
        self.rng = random.Random(seed)

    def run(self, result: BacktestResult, initial_capital: float = 10000.0) -> MonteCarloReport:
        """
        Run Monte Carlo by reshuffling trades from a completed backtest.
        """
        trades = result.trades
        if not trades:
            return MonteCarloReport(
                n_simulations=0, returns_mean=0, returns_median=0,
                returns_p5=0, returns_p25=0, returns_p75=0, returns_p95=0,
                max_dd_mean=0, max_dd_p5=0, sharpe_mean=0, sharpe_p5=0,
                ruin_probability=0,
            )

        trade_pnl_pcts = [t.pnl_pct for t in trades]
        all_returns = []
        all_drawdowns = []
        all_sharpes = []

        for _ in range(self.n_simulations):
            shuffled = trade_pnl_pcts[:]
            self.rng.shuffle(shuffled)

            # Simulate equity curve
            equity = initial_capital
            peak = equity
            max_dd = 0.0
            daily_rets = []

            for pnl_pct in shuffled:
                prev = equity
                equity *= (1 + pnl_pct)
                equity = max(equity, 0.01)  # floor
                peak = max(peak, equity)
                dd = (equity - peak) / peak if peak > 0 else 0
                max_dd = min(max_dd, dd)
                if prev > 0:
                    daily_rets.append((equity - prev) / prev)

            total_ret = (equity / initial_capital) - 1
            all_returns.append(total_ret)
            all_drawdowns.append(max_dd)

            if daily_rets and len(daily_rets) > 1:
                mean_r = sum(daily_rets) / len(daily_rets)
                std_r = math.sqrt(sum((r - mean_r)**2 for r in daily_rets) / (len(daily_rets) - 1))
                sharpe = (mean_r * math.sqrt(252)) / max(std_r * math.sqrt(252), 0.001)
            else:
                sharpe = 0
            all_sharpes.append(sharpe)

        all_returns.sort()
        all_drawdowns.sort()
        all_sharpes.sort()
        n = len(all_returns)

        def pctl(arr, p):
            idx = max(int(len(arr) * p), 0)
            idx = min(idx, len(arr) - 1)
            return arr[idx]

        ruin = sum(1 for r in all_returns if r < -0.5) / n

        return MonteCarloReport(
            n_simulations=self.n_simulations,
            returns_mean=sum(all_returns) / n,
            returns_median=pctl(all_returns, 0.5),
            returns_p5=pctl(all_returns, 0.05),
            returns_p25=pctl(all_returns, 0.25),
            returns_p75=pctl(all_returns, 0.75),
            returns_p95=pctl(all_returns, 0.95),
            max_dd_mean=sum(all_drawdowns) / n,
            max_dd_p5=pctl(all_drawdowns, 0.05),
            sharpe_mean=sum(all_sharpes) / n,
            sharpe_p5=pctl(all_sharpes, 0.05),
            ruin_probability=ruin,
            all_returns=all_returns,
            all_drawdowns=all_drawdowns,
        )
