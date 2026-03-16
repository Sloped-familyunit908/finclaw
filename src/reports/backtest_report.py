"""
Backtest Report Generator
Generate comprehensive backtest reports with stats, monthly returns, equity curves, and trade logs.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TradeRecord:
    """Single trade in the log."""
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    pnl_pct: float
    holding_period: int
    side: str = "long"


@dataclass
class MonthlyReturn:
    """Monthly return entry."""
    month: int  # 1-12
    year: int   # optional grouping
    return_pct: float
    num_trades: int


@dataclass
class BacktestReport:
    """Comprehensive backtest report."""
    # Summary stats
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    num_trades: int
    avg_trade_return: float
    avg_win: float
    avg_loss: float
    
    # Detailed
    monthly_returns: list[MonthlyReturn]
    equity_curve: list[float]
    trade_log: list[TradeRecord]
    risk_over_time: list[dict[str, float]]
    
    # Benchmark comparison
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None


class BacktestReportGenerator:
    """
    Generate comprehensive backtest reports from price data and a strategy.
    
    Usage:
        gen = BacktestReportGenerator()
        report = gen.generate(strategy, data, benchmark_data=spy_prices)
    """

    def generate(
        self,
        strategy: Any,
        data: list[float],
        benchmark_data: Optional[list[float]] = None,
        trading_days_per_year: int = 252,
        bars_per_month: int = 21,
    ) -> BacktestReport:
        """Generate a full backtest report."""
        if len(data) < 30:
            raise ValueError("Need at least 30 data points for backtest report")

        trades = self._run_trades(strategy, data)
        equity = self._build_equity_curve(trades, data)
        monthly = self._calc_monthly_returns(trades, bars_per_month)
        risk_ts = self._calc_rolling_risk(equity, window=20)

        # Core stats
        total_ret = (equity[-1] / equity[0] - 1) if equity[0] > 0 else 0
        n_years = len(data) / trading_days_per_year
        ann_ret = (1 + total_ret) ** (1 / n_years) - 1 if n_years > 0 else 0

        trade_returns = [t.pnl_pct for t in trades]
        sharpe = self._sharpe(trade_returns, trading_days_per_year)
        sortino = self._sortino(trade_returns, trading_days_per_year)
        mdd = self._max_drawdown(equity)
        win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns) if trade_returns else 0

        wins = [r for r in trade_returns if r > 0]
        losses = [r for r in trade_returns if r <= 0]
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_trade = sum(trade_returns) / len(trade_returns) if trade_returns else 0

        # Benchmark
        bench_ret = alpha = beta_val = ir = None
        if benchmark_data and len(benchmark_data) >= len(data):
            bench_ret, alpha, beta_val, ir = self._benchmark_stats(
                equity, data, benchmark_data, trading_days_per_year,
            )

        return BacktestReport(
            total_return=round(total_ret, 6),
            annualized_return=round(ann_ret, 6),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            max_drawdown=round(mdd, 6),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            num_trades=len(trades),
            avg_trade_return=round(avg_trade, 6),
            avg_win=round(avg_win, 6),
            avg_loss=round(avg_loss, 6),
            monthly_returns=monthly,
            equity_curve=equity,
            trade_log=trades,
            risk_over_time=risk_ts,
            benchmark_return=bench_ret,
            alpha=alpha,
            beta=beta_val,
            information_ratio=ir,
        )

    def _run_trades(self, strategy: Any, data: list[float]) -> list[TradeRecord]:
        """Simulate trades from strategy signals."""
        trades = []
        position = None
        window = 30

        for i in range(window, len(data)):
            sig = self._get_signal(strategy, data[:i + 1])
            if position is None and sig == "buy":
                position = (data[i], i)
            elif position is not None and sig == "sell":
                entry_price, entry_idx = position
                exit_price = data[i]
                trades.append(TradeRecord(
                    entry_idx=entry_idx, exit_idx=i,
                    entry_price=entry_price, exit_price=exit_price,
                    pnl_pct=(exit_price / entry_price) - 1,
                    holding_period=i - entry_idx,
                ))
                position = None
        return trades

    def _get_signal(self, strategy: Any, prices: list[float]) -> str:
        if hasattr(strategy, "generate_signal"):
            return getattr(strategy.generate_signal(prices), "signal", "hold")
        if hasattr(strategy, "score_single"):
            return getattr(strategy.score_single(prices), "signal", "hold")
        if hasattr(strategy, "signal"):
            val = strategy.signal(prices)
            if isinstance(val, (int, float)):
                return "buy" if val > 0.3 else ("sell" if val < -0.3 else "hold")
        return "hold"

    def _build_equity_curve(self, trades: list[TradeRecord], data: list[float]) -> list[float]:
        """Build equity curve: 1.0 at start, compound through trades."""
        equity = [1.0] * len(data)
        for t in trades:
            growth = t.exit_price / t.entry_price if t.entry_price > 0 else 1
            for i in range(t.exit_idx, len(data)):
                equity[i] *= growth
        return equity

    def _calc_monthly_returns(self, trades: list[TradeRecord], bars_per_month: int) -> list[MonthlyReturn]:
        """Group trades into monthly buckets."""
        if not trades:
            return []
        monthly: dict[int, list[float]] = {}
        for t in trades:
            month_idx = t.entry_idx // bars_per_month
            monthly.setdefault(month_idx, []).append(t.pnl_pct)
        
        result = []
        for m_idx in sorted(monthly):
            rets = monthly[m_idx]
            compounded = 1.0
            for r in rets:
                compounded *= (1 + r)
            result.append(MonthlyReturn(
                month=(m_idx % 12) + 1,
                year=m_idx // 12,
                return_pct=round(compounded - 1, 6),
                num_trades=len(rets),
            ))
        return result

    def _calc_rolling_risk(self, equity: list[float], window: int = 20) -> list[dict[str, float]]:
        """Rolling volatility and drawdown."""
        risk = []
        for i in range(window, len(equity)):
            w = equity[i - window:i + 1]
            rets = [(w[j] / w[j-1]) - 1 for j in range(1, len(w))]
            mean_r = sum(rets) / len(rets)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / len(rets))
            peak = max(w)
            dd = (peak - w[-1]) / peak if peak > 0 else 0
            risk.append({
                "idx": i,
                "rolling_vol": round(std_r, 6),
                "rolling_dd": round(dd, 6),
            })
        return risk

    def _sharpe(self, returns: list[float], annual_factor: int, rf: float = 0.02) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns))
        if std_r == 0:
            return 0.0
        return (mean_r - rf / annual_factor) * math.sqrt(annual_factor) / std_r

    def _sortino(self, returns: list[float], annual_factor: int, rf: float = 0.02) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        down = [r for r in returns if r < 0]
        if not down:
            return float('inf') if mean_r > 0 else 0.0
        down_dev = math.sqrt(sum(r ** 2 for r in down) / len(down))
        if down_dev == 0:
            return 0.0
        return (mean_r - rf / annual_factor) * math.sqrt(annual_factor) / down_dev

    def _max_drawdown(self, equity: list[float]) -> float:
        peak = equity[0]
        mdd = 0.0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0
            mdd = max(mdd, dd)
        return mdd

    def _benchmark_stats(self, equity, data, benchmark, annual_factor):
        """Compare against benchmark."""
        n = min(len(data), len(benchmark))
        strat_rets = [(data[i] / data[i-1]) - 1 for i in range(1, n)]
        bench_rets = [(benchmark[i] / benchmark[i-1]) - 1 for i in range(1, n)]
        
        bench_total = (benchmark[n-1] / benchmark[0]) - 1 if benchmark[0] > 0 else 0
        
        # Beta
        mean_s = sum(strat_rets) / len(strat_rets)
        mean_b = sum(bench_rets) / len(bench_rets)
        cov = sum((s - mean_s) * (b - mean_b) for s, b in zip(strat_rets, bench_rets)) / len(strat_rets)
        var_b = sum((b - mean_b) ** 2 for b in bench_rets) / len(bench_rets)
        beta_val = cov / var_b if var_b > 0 else 0
        
        # Alpha (annualized)
        alpha = (mean_s - beta_val * mean_b) * annual_factor
        
        # Information ratio
        excess = [s - b for s, b in zip(strat_rets, bench_rets)]
        mean_excess = sum(excess) / len(excess)
        te = math.sqrt(sum((e - mean_excess) ** 2 for e in excess) / len(excess))
        ir = mean_excess * math.sqrt(annual_factor) / te if te > 0 else 0
        
        return round(bench_total, 6), round(alpha, 6), round(beta_val, 4), round(ir, 4)
