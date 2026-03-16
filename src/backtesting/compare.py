"""
Strategy Performance Comparison
Compare multiple strategy/benchmark results side-by-side with rankings.
"""

from dataclasses import dataclass, field
from typing import Optional, Union
import math


@dataclass
class StrategyMetrics:
    """Unified metrics for comparison."""
    name: str
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    total_costs: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    daily_returns: list[float] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of comparing multiple strategies."""
    strategies: list[StrategyMetrics]
    rankings: dict[str, list[str]]  # metric_name -> ordered list of strategy names
    best_overall: str = ""
    correlation_matrix: Optional[dict[str, dict[str, float]]] = None

    def table(self) -> str:
        """Format as text table."""
        if not self.strategies:
            return "No strategies to compare."

        header = f"{'Strategy':<20} {'Return':>10} {'CAGR':>8} {'Sharpe':>8} " \
                 f"{'Sortino':>8} {'MaxDD':>8} {'Win%':>7} {'PF':>6} {'Trades':>7}"
        sep = "-" * len(header)
        lines = [sep, header, sep]

        for s in self.strategies:
            lines.append(
                f"{s.name:<20} {s.total_return:>+9.2%} {s.cagr:>+7.2%} "
                f"{s.sharpe_ratio:>8.2f} {s.sortino_ratio:>8.2f} "
                f"{s.max_drawdown:>8.2%} {s.win_rate:>6.1%} "
                f"{s.profit_factor:>6.2f} {s.total_trades:>7}"
            )

        lines.append(sep)
        if self.best_overall:
            lines.append(f"🏆 Best Overall: {self.best_overall}")

        # Rankings
        for metric, names in self.rankings.items():
            lines.append(f"  Best {metric}: {names[0]}")

        return "\n".join(lines)


class StrategyComparator:
    """Compare multiple strategy results side-by-side."""

    def __init__(self):
        self._entries: list[StrategyMetrics] = []

    def add(self, name: str, result: object) -> "StrategyComparator":
        """
        Add a result to compare. Accepts BacktestResult, BenchmarkResult,
        or any object with compatible fields.
        """
        metrics = StrategyMetrics(
            name=name,
            total_return=getattr(result, "total_return", 0),
            cagr=getattr(result, "cagr", getattr(result, "annualized_return", 0)),
            sharpe_ratio=getattr(result, "sharpe_ratio", 0),
            sortino_ratio=getattr(result, "sortino_ratio", 0),
            max_drawdown=getattr(result, "max_drawdown", 0),
            volatility=getattr(result, "volatility", 0),
            calmar_ratio=getattr(result, "calmar_ratio", 0),
            win_rate=getattr(result, "win_rate", 0),
            profit_factor=getattr(result, "profit_factor", 0),
            total_trades=getattr(result, "total_trades", 0),
            total_costs=getattr(result, "total_costs", 0),
            equity_curve=getattr(result, "equity_curve", []),
            daily_returns=getattr(result, "daily_returns", []),
        )
        self._entries.append(metrics)
        return self

    def add_metrics(self, metrics: StrategyMetrics) -> "StrategyComparator":
        self._entries.append(metrics)
        return self

    def compare(self) -> ComparisonResult:
        """Run comparison and rank strategies."""
        if not self._entries:
            return ComparisonResult(strategies=[], rankings={})

        # Define ranking criteria (higher is better except max_drawdown)
        criteria = {
            "Return": ("total_return", True),
            "CAGR": ("cagr", True),
            "Sharpe": ("sharpe_ratio", True),
            "Sortino": ("sortino_ratio", True),
            "MaxDD": ("max_drawdown", False),  # less negative is better
            "Win Rate": ("win_rate", True),
            "Profit Factor": ("profit_factor", True),
            "Calmar": ("calmar_ratio", True),
        }

        rankings: dict[str, list[str]] = {}
        scores: dict[str, float] = {s.name: 0 for s in self._entries}

        for metric_name, (attr, higher_better) in criteria.items():
            sorted_entries = sorted(
                self._entries,
                key=lambda s: getattr(s, attr, 0),
                reverse=higher_better,
            )
            rankings[metric_name] = [s.name for s in sorted_entries]

            # Score: best gets N points, worst gets 1
            for rank, entry in enumerate(sorted_entries):
                scores[entry.name] += len(self._entries) - rank

        best = max(scores, key=scores.get) if scores else ""

        # Correlation matrix
        corr_matrix = self._compute_correlations()

        return ComparisonResult(
            strategies=list(self._entries),
            rankings=rankings,
            best_overall=best,
            correlation_matrix=corr_matrix,
        )

    def _compute_correlations(self) -> Optional[dict[str, dict[str, float]]]:
        """Compute return correlation matrix between strategies."""
        entries_with_rets = [s for s in self._entries if len(s.daily_returns) > 5]
        if len(entries_with_rets) < 2:
            return None

        matrix: dict[str, dict[str, float]] = {}
        for a in entries_with_rets:
            matrix[a.name] = {}
            for b in entries_with_rets:
                min_len = min(len(a.daily_returns), len(b.daily_returns))
                if min_len < 3:
                    matrix[a.name][b.name] = 0
                    continue
                ar = a.daily_returns[:min_len]
                br = b.daily_returns[:min_len]
                corr = _correlation(ar, br)
                matrix[a.name][b.name] = round(corr, 3)
        return matrix

    def reset(self):
        self._entries.clear()


def _correlation(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return 0
    return cov / (sx * sy)
