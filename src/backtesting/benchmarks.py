"""
Benchmark Suite
Standard benchmarks for comparing strategy performance.
Buy-and-hold, equal-weight, 60/40, risk parity, and custom benchmarks.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BenchmarkResult:
    """Result from running a benchmark strategy."""
    name: str
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    daily_returns: list[float] = field(default_factory=list)

    def summary_row(self) -> dict:
        return {
            "Name": self.name,
            "Return": f"{self.total_return:+.2%}",
            "CAGR": f"{self.cagr:+.2%}",
            "Sharpe": f"{self.sharpe_ratio:.2f}",
            "Sortino": f"{self.sortino_ratio:.2f}",
            "MaxDD": f"{self.max_drawdown:.2%}",
            "Vol": f"{self.volatility:.2%}",
        }


class BenchmarkBase:
    """Base class for benchmark strategies."""
    name: str = "Base"

    def run(self, price_data: dict[str, list[float]], n_bars: int,
            risk_free: float = 0.05) -> BenchmarkResult:
        raise NotImplementedError

    @staticmethod
    def _compute_metrics(name: str, equity: list[float],
                         risk_free: float = 0.05) -> BenchmarkResult:
        if len(equity) < 2:
            return BenchmarkResult(name=name)

        total_ret = equity[-1] / equity[0] - 1
        years = max(len(equity) / 252, 0.01)
        cagr = (equity[-1] / equity[0]) ** (1 / years) - 1 if equity[-1] > 0 else -1

        daily = [(equity[i] / equity[i - 1] - 1) for i in range(1, len(equity))]
        vol = _std(daily) * math.sqrt(252) if len(daily) > 1 else 0.001
        avg_ret = sum(daily) / len(daily) * 252 if daily else 0
        sharpe = (avg_ret - risk_free) / max(vol, 0.001)

        down = [r for r in daily if r < 0]
        dd_dev = math.sqrt(sum(r ** 2 for r in down) / max(len(down), 1)) * math.sqrt(252) if down else 0.001
        sortino = (avg_ret - risk_free) / max(dd_dev, 0.001)

        peak = equity[0]
        max_dd = 0
        for eq in equity:
            peak = max(peak, eq)
            dd = (eq - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)

        calmar = cagr / max(abs(max_dd), 0.001)

        return BenchmarkResult(
            name=name, total_return=total_ret, cagr=cagr,
            sharpe_ratio=sharpe, sortino_ratio=sortino,
            max_drawdown=max_dd, volatility=vol, calmar_ratio=calmar,
            equity_curve=equity, daily_returns=daily,
        )


class BuyAndHold(BenchmarkBase):
    """Buy-and-hold a single asset."""

    def __init__(self, symbol: str = "SPY"):
        self.symbol = symbol
        self.name = f"B&H {symbol}"

    def run(self, price_data: dict[str, list[float]], n_bars: int = 0,
            risk_free: float = 0.05) -> BenchmarkResult:
        prices = price_data.get(self.symbol, [])
        if not prices:
            return BenchmarkResult(name=self.name)
        # Normalize to $1 start
        start = prices[0]
        equity = [p / start for p in prices]
        return self._compute_metrics(self.name, equity, risk_free)


class EqualWeight(BenchmarkBase):
    """Equal-weight portfolio rebalanced daily."""

    def __init__(self, symbols: Optional[list[str]] = None):
        self.symbols = symbols or ["AAPL", "MSFT", "GOOGL", "AMZN"]
        self.name = f"EqWt({len(self.symbols)})"

    def run(self, price_data: dict[str, list[float]], n_bars: int = 0,
            risk_free: float = 0.05) -> BenchmarkResult:
        available = [s for s in self.symbols if s in price_data and len(price_data[s]) > 1]
        if not available:
            return BenchmarkResult(name=self.name)

        min_len = min(len(price_data[s]) for s in available)
        weight = 1.0 / len(available)
        equity = [1.0]

        for i in range(1, min_len):
            day_ret = sum(
                weight * (price_data[s][i] / price_data[s][i - 1] - 1)
                for s in available
            )
            equity.append(equity[-1] * (1 + day_ret))

        return self._compute_metrics(self.name, equity, risk_free)


class ClassicPortfolio(BenchmarkBase):
    """Classic stock/bond allocation (e.g., 60/40)."""

    def __init__(self, stocks_pct: float = 0.6, bonds_pct: float = 0.4,
                 stock_symbol: str = "SPY", bond_symbol: str = "TLT"):
        self.stocks_pct = stocks_pct
        self.bonds_pct = bonds_pct
        self.stock_symbol = stock_symbol
        self.bond_symbol = bond_symbol
        self.name = f"{int(stocks_pct * 100)}/{int(bonds_pct * 100)}"

    def run(self, price_data: dict[str, list[float]], n_bars: int = 0,
            risk_free: float = 0.05) -> BenchmarkResult:
        stocks = price_data.get(self.stock_symbol, [])
        bonds = price_data.get(self.bond_symbol, [])
        if not stocks or not bonds:
            return BenchmarkResult(name=self.name)

        min_len = min(len(stocks), len(bonds))
        equity = [1.0]
        for i in range(1, min_len):
            s_ret = stocks[i] / stocks[i - 1] - 1
            b_ret = bonds[i] / bonds[i - 1] - 1
            day_ret = self.stocks_pct * s_ret + self.bonds_pct * b_ret
            equity.append(equity[-1] * (1 + day_ret))

        return self._compute_metrics(self.name, equity, risk_free)


class RiskParityBenchmark(BenchmarkBase):
    """
    Simplified risk parity: weight inversely proportional to rolling volatility.
    Rebalances daily based on trailing 60-day vol.
    """

    def __init__(self, symbols: Optional[list[str]] = None, lookback: int = 60):
        self.symbols = symbols or ["SPY", "TLT", "GLD"]
        self.lookback = lookback
        self.name = f"RiskParity({len(self.symbols)})"

    def run(self, price_data: dict[str, list[float]], n_bars: int = 0,
            risk_free: float = 0.05) -> BenchmarkResult:
        available = [s for s in self.symbols if s in price_data and len(price_data[s]) > self.lookback + 1]
        if not available:
            return BenchmarkResult(name=self.name)

        min_len = min(len(price_data[s]) for s in available)
        equity = [1.0] * self.lookback  # flat during warmup

        for i in range(self.lookback, min_len):
            # Compute inverse vol weights
            inv_vols = []
            rets_map = {}
            for s in available:
                window_rets = [
                    price_data[s][j] / price_data[s][j - 1] - 1
                    for j in range(i - self.lookback + 1, i + 1)
                ]
                vol = _std(window_rets) if len(window_rets) > 1 else 0.01
                inv_vols.append(1.0 / max(vol, 0.001))
                rets_map[s] = price_data[s][i] / price_data[s][i - 1] - 1

            total_inv = sum(inv_vols)
            weights = [iv / total_inv for iv in inv_vols]

            day_ret = sum(w * rets_map[s] for w, s in zip(weights, available))
            equity.append(equity[-1] * (1 + day_ret))

        return self._compute_metrics(self.name, equity, risk_free)


# Pre-built benchmark registry
BENCHMARKS = {
    "buy_and_hold_spy": BuyAndHold("SPY"),
    "equal_weight": EqualWeight(["AAPL", "MSFT", "GOOGL", "AMZN"]),
    "60_40": ClassicPortfolio(stocks_pct=0.6, bonds_pct=0.4),
    "risk_parity": RiskParityBenchmark(),
}


def run_all_benchmarks(
    price_data: dict[str, list[float]],
    risk_free: float = 0.05,
    custom: Optional[dict[str, BenchmarkBase]] = None,
) -> dict[str, BenchmarkResult]:
    """Run all registered benchmarks. Returns name -> BenchmarkResult."""
    registry = {**BENCHMARKS}
    if custom:
        registry.update(custom)
    results = {}
    for name, bm in registry.items():
        results[name] = bm.run(price_data, risk_free=risk_free)
    return results


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))
