"""
Benchmark Comparison
Compare strategy results against SPY/QQQ buy-and-hold benchmarks.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BenchmarkMetrics:
    name: str
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float


@dataclass
class BenchmarkReport:
    strategy_name: str
    strategy_return: float
    strategy_sharpe: float
    strategy_max_dd: float
    benchmarks: list[BenchmarkMetrics] = field(default_factory=list)
    alpha_vs: dict[str, float] = field(default_factory=dict)  # name -> alpha
    beta_vs: dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "=== Benchmark Comparison ===",
            f"Strategy: {self.strategy_name}  Return={self.strategy_return:+.2%}  Sharpe={self.strategy_sharpe:.2f}",
        ]
        for bm in self.benchmarks:
            alpha = self.alpha_vs.get(bm.name, 0)
            lines.append(
                f"  vs {bm.name:6s}: Return={bm.total_return:+.2%}  "
                f"Sharpe={bm.sharpe_ratio:.2f}  Alpha={alpha:+.2%}"
            )
        return "\n".join(lines)


class BenchmarkComparison:
    """Compare strategy performance against buy-and-hold benchmarks."""

    @staticmethod
    def compute_buy_hold(
        name: str,
        prices: list[float],
        risk_free: float = 0.05,
    ) -> BenchmarkMetrics:
        """Compute buy-and-hold metrics from a price series."""
        if len(prices) < 2:
            return BenchmarkMetrics(name=name, total_return=0, annualized_return=0,
                                    volatility=0, sharpe_ratio=0, max_drawdown=0)

        total_return = (prices[-1] / prices[0]) - 1
        days = len(prices)
        years = max(days / 252, 0.01)
        ann_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1

        # Daily returns
        daily_rets = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
        vol = _std(daily_rets) * math.sqrt(252) if len(daily_rets) > 1 else 0.001
        avg_r = sum(daily_rets) / len(daily_rets) * 252
        sharpe = (avg_r - risk_free) / max(vol, 0.001)

        # Max drawdown
        peak = prices[0]
        max_dd = 0
        for p in prices:
            peak = max(peak, p)
            dd = (p - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)

        return BenchmarkMetrics(
            name=name,
            total_return=total_return,
            annualized_return=ann_return,
            volatility=vol,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
        )

    def compare(
        self,
        strategy_name: str,
        strategy_return: float,
        strategy_sharpe: float,
        strategy_max_dd: float,
        strategy_daily_returns: list[float],
        benchmark_series: dict[str, list[float]],  # name -> price series
    ) -> BenchmarkReport:
        """
        Compare strategy against multiple benchmarks.
        
        benchmark_series: {"SPY": [100, 101, ...], "QQQ": [200, 201, ...]}
        """
        report = BenchmarkReport(
            strategy_name=strategy_name,
            strategy_return=strategy_return,
            strategy_sharpe=strategy_sharpe,
            strategy_max_dd=strategy_max_dd,
        )

        for name, prices in benchmark_series.items():
            bm = self.compute_buy_hold(name, prices)
            report.benchmarks.append(bm)
            report.alpha_vs[name] = strategy_return - bm.total_return

            # Beta computation
            if len(prices) > 1 and len(strategy_daily_returns) > 1:
                bm_rets = [(prices[i] / prices[i-1]) - 1 for i in range(1, len(prices))]
                min_len = min(len(strategy_daily_returns), len(bm_rets))
                if min_len > 2:
                    sr = strategy_daily_returns[:min_len]
                    br = bm_rets[:min_len]
                    cov = _cov(sr, br)
                    var_bm = _var(br)
                    report.beta_vs[name] = cov / max(var_bm, 1e-10)

        return report


def _std(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _var(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def _cov(x, y):
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
