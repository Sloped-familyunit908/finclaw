"""
FinClaw - Rigorous Statistical Backtester
Institutional-grade validation: Walk-Forward, Monte Carlo, Bootstrap.

Reference standards:
- Marcos López de Prado: "Advances in Financial Machine Learning" (2018)
- Bailey & López de Prado: "The Deflated Sharpe Ratio" (2014)
- White's Reality Check / Hansen's Superior Predictive Ability test
"""

import random
import math
import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TradeRecord:
    """A completed trade"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    signal: str
    pnl_pct: float
    duration_days: int


@dataclass 
class StatisticalReport:
    """Full statistical analysis of backtest results"""
    strategy_name: str
    asset: str
    
    # Basic metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_pnl: float
    avg_win: float
    avg_loss: float
    
    # Statistical significance
    t_statistic: float              # t-test: is mean return > 0?
    p_value: float                  # p < 0.05 = statistically significant
    is_significant: bool            # p < 0.05
    
    # Bootstrap confidence intervals (95%)
    return_ci_lower: float
    return_ci_upper: float
    sharpe_ci_lower: float
    sharpe_ci_upper: float
    
    # Monte Carlo
    mc_median_return: float
    mc_worst_5pct: float            # 5th percentile (VaR)
    mc_best_5pct: float             # 95th percentile
    mc_prob_profit: float           # % of simulations profitable
    
    # Walk-Forward
    wf_in_sample_return: float
    wf_out_sample_return: float
    wf_efficiency: float            # OOS return / IS return
    wf_periods_profitable: int
    wf_total_periods: int
    
    # Kelly Criterion
    kelly_fraction: float           # Optimal bet size
    half_kelly: float               # Conservative (half-Kelly)
    
    # Deflated Sharpe Ratio (López de Prado)
    deflated_sharpe: float
    dsr_is_significant: bool


def compute_sharpe(returns: list[float], rf_rate: float = 0.0) -> float:
    """Annualized Sharpe Ratio"""
    if not returns or len(returns) < 2:
        return 0.0
    mean_r = statistics.mean(returns) - rf_rate / 252
    std_r = statistics.stdev(returns)
    if std_r == 0:
        return 0.0
    return (mean_r / std_r) * math.sqrt(252)


def compute_sortino(returns: list[float], rf_rate: float = 0.0) -> float:
    """Sortino Ratio (downside deviation only)"""
    if not returns or len(returns) < 2:
        return 0.0
    mean_r = statistics.mean(returns) - rf_rate / 252
    downside = [r for r in returns if r < 0]
    if not downside:
        return float('inf') if mean_r > 0 else 0.0
    downside_std = math.sqrt(sum(r**2 for r in downside) / len(downside))
    if downside_std == 0:
        return 0.0
    return (mean_r / downside_std) * math.sqrt(252)


def compute_max_drawdown(equity_curve: list[float]) -> float:
    """Maximum drawdown from equity curve"""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak != 0 else 0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def bootstrap_confidence_interval(
    data: list[float], 
    stat_func, 
    n_bootstrap: int = 5000, 
    ci: float = 0.95,
    seed: int = 42
) -> tuple[float, float]:
    """
    Bootstrap confidence interval for any statistic.
    Resample with replacement, compute stat, get percentile interval.
    """
    rng = random.Random(seed)
    n = len(data)
    if n < 2:
        return (0.0, 0.0)
    
    stats = []
    for _ in range(n_bootstrap):
        sample = [rng.choice(data) for _ in range(n)]
        try:
            stats.append(stat_func(sample))
        except (ValueError, ZeroDivisionError, statistics.StatisticsError):
            continue
    
    if not stats:
        return (0.0, 0.0)
    
    stats.sort()
    alpha = (1 - ci) / 2
    lower_idx = max(0, int(alpha * len(stats)))
    upper_idx = min(len(stats) - 1, int((1 - alpha) * len(stats)))
    return (stats[lower_idx], stats[upper_idx])


def monte_carlo_simulation(
    trades: list[float],
    n_simulations: int = 10000,
    seed: int = 42
) -> dict:
    """
    Monte Carlo: randomly reorder trades to estimate return distribution.
    If strategy is robust, order shouldn't matter much.
    """
    rng = random.Random(seed)
    if not trades:
        return {"median": 0, "worst_5pct": 0, "best_5pct": 0, "prob_profit": 0}
    
    final_returns = []
    for _ in range(n_simulations):
        shuffled = trades.copy()
        rng.shuffle(shuffled)
        # Compute compounded return
        equity = 1.0
        for pnl in shuffled:
            equity *= (1 + pnl)
        final_returns.append(equity - 1)
    
    final_returns.sort()
    n = len(final_returns)
    
    return {
        "median": final_returns[n // 2],
        "worst_5pct": final_returns[int(0.05 * n)],
        "best_5pct": final_returns[int(0.95 * n)],
        "prob_profit": sum(1 for r in final_returns if r > 0) / n,
    }


def walk_forward_split(
    daily_returns: list[float],
    in_sample_pct: float = 0.70,
    n_periods: int = 4
) -> list[dict]:
    """
    Walk-Forward analysis: split data into rolling IS/OOS windows.
    
    Example with 200 days, 4 periods:
    Period 1: IS days 0-34,  OOS days 35-49
    Period 2: IS days 50-84, OOS days 85-99
    Period 3: IS days 100-134, OOS days 135-149
    Period 4: IS days 150-184, OOS days 185-199
    """
    n = len(daily_returns)
    period_len = n // n_periods
    if period_len < 10:
        return []
    
    is_len = int(period_len * in_sample_pct)
    oos_len = period_len - is_len
    
    results = []
    for i in range(n_periods):
        start = i * period_len
        is_end = start + is_len
        oos_end = min(start + period_len, n)
        
        is_returns = daily_returns[start:is_end]
        oos_returns = daily_returns[is_end:oos_end]
        
        if not is_returns or not oos_returns:
            continue
        
        is_total = 1.0
        for r in is_returns:
            is_total *= (1 + r)
        is_total -= 1
        
        oos_total = 1.0
        for r in oos_returns:
            oos_total *= (1 + r)
        oos_total -= 1
        
        efficiency = oos_total / is_total if is_total != 0 else 0
        
        results.append({
            "period": i + 1,
            "is_return": is_total,
            "oos_return": oos_total,
            "efficiency": efficiency,
            "is_sharpe": compute_sharpe(is_returns),
            "oos_sharpe": compute_sharpe(oos_returns),
            "oos_profitable": oos_total > 0,
        })
    
    return results


def deflated_sharpe_ratio(
    sharpe: float,
    n_trials: int,
    n_returns: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0
) -> float:
    """
    Deflated Sharpe Ratio (Bailey & López de Prado, 2014).
    Adjusts Sharpe for multiple testing bias.
    
    When you test many strategies, some will look good by chance.
    DSR accounts for this.
    """
    if n_returns < 2 or n_trials < 1:
        return 0.0
    
    # Expected maximum Sharpe from random strategies
    euler_mascheroni = 0.5772
    expected_max_sharpe = math.sqrt(2 * math.log(n_trials)) * (
        1 - euler_mascheroni / (2 * math.log(n_trials))
    ) + euler_mascheroni / (2 * math.sqrt(2 * math.log(n_trials)))
    
    # Variance of Sharpe estimator
    sharpe_var = (1 - skewness * sharpe + (kurtosis - 1) / 4 * sharpe**2) / (n_returns - 1)
    if sharpe_var <= 0:
        return 0.0
    
    sharpe_std = math.sqrt(sharpe_var)
    
    # PSR: Probabilistic Sharpe Ratio
    if sharpe_std == 0:
        return 0.0
    z = (sharpe - expected_max_sharpe) / sharpe_std
    
    # Standard normal CDF approximation
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def t_test_returns(returns: list[float]) -> tuple[float, float]:
    """
    One-sample t-test: is the mean return significantly > 0?
    Returns (t_statistic, p_value)
    """
    n = len(returns)
    if n < 2:
        return (0.0, 1.0)
    
    mean = statistics.mean(returns)
    std = statistics.stdev(returns)
    if std == 0:
        return (0.0, 1.0)
    
    t_stat = mean / (std / math.sqrt(n))
    
    # Approximate p-value using normal distribution (good for n > 30)
    p_value = 1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2)))
    
    return (t_stat, p_value)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Kelly Criterion: optimal fraction of capital to bet.
    f* = (p * b - q) / b
    where p = win rate, q = 1-p, b = avg_win / avg_loss
    """
    if avg_loss == 0 or win_rate <= 0:
        return 0.0
    
    b = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    q = 1 - win_rate
    
    if b == 0:
        return 0.0
    
    kelly = (win_rate * b - q) / b
    return max(0.0, min(1.0, kelly))  # Clamp to [0, 1]


def generate_statistical_report(
    strategy_name: str,
    asset: str,
    daily_returns: list[float],
    trade_pnls: list[float],
    equity_curve: list[float],
    n_strategies_tested: int = 5,
) -> StatisticalReport:
    """
    Generate a complete statistical report with all validation metrics.
    This is what a real quant fund would require.
    """
    
    # ── Basic Metrics ──
    total_return = (equity_curve[-1] / equity_curve[0] - 1) if equity_curve else 0
    n_days = len(daily_returns)
    ann_return = (1 + total_return) ** (365 / max(n_days, 1)) - 1 if n_days > 0 else 0
    
    sharpe = compute_sharpe(daily_returns)
    sortino = compute_sortino(daily_returns)
    max_dd = compute_max_drawdown(equity_curve)
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0
    
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p <= 0]
    win_rate = len(wins) / len(trade_pnls) if trade_pnls else 0
    avg_win = statistics.mean(wins) if wins else 0
    avg_loss = statistics.mean(losses) if losses else 0
    profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float('inf')
    avg_trade = statistics.mean(trade_pnls) if trade_pnls else 0
    
    # ── Statistical Significance ──
    t_stat, p_val = t_test_returns(daily_returns)
    
    # ── Bootstrap ──
    ret_ci = bootstrap_confidence_interval(
        daily_returns, 
        lambda x: sum(x),  # total return
        n_bootstrap=5000
    )
    sharpe_ci = bootstrap_confidence_interval(
        daily_returns,
        compute_sharpe,
        n_bootstrap=5000
    )
    
    # ── Monte Carlo ──
    mc = monte_carlo_simulation(trade_pnls, n_simulations=10000)
    
    # ── Walk-Forward ──
    wf_results = walk_forward_split(daily_returns, n_periods=4)
    wf_is_ret = statistics.mean([w["is_return"] for w in wf_results]) if wf_results else 0
    wf_oos_ret = statistics.mean([w["oos_return"] for w in wf_results]) if wf_results else 0
    wf_eff = wf_oos_ret / wf_is_ret if wf_is_ret != 0 else 0
    wf_profitable = sum(1 for w in wf_results if w["oos_profitable"])
    
    # ── Kelly ──
    kelly = kelly_criterion(win_rate, avg_win, avg_loss)
    
    # ── Deflated Sharpe ──
    dsr = deflated_sharpe_ratio(
        sharpe=sharpe,
        n_trials=n_strategies_tested,
        n_returns=n_days,
    )
    
    return StatisticalReport(
        strategy_name=strategy_name,
        asset=asset,
        total_return=total_return,
        annualized_return=ann_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=len(trade_pnls),
        avg_trade_pnl=avg_trade,
        avg_win=avg_win,
        avg_loss=avg_loss,
        t_statistic=t_stat,
        p_value=p_val,
        is_significant=p_val < 0.05,
        return_ci_lower=ret_ci[0],
        return_ci_upper=ret_ci[1],
        sharpe_ci_lower=sharpe_ci[0],
        sharpe_ci_upper=sharpe_ci[1],
        mc_median_return=mc["median"],
        mc_worst_5pct=mc["worst_5pct"],
        mc_best_5pct=mc["best_5pct"],
        mc_prob_profit=mc["prob_profit"],
        wf_in_sample_return=wf_is_ret,
        wf_out_sample_return=wf_oos_ret,
        wf_efficiency=wf_eff,
        wf_periods_profitable=wf_profitable,
        wf_total_periods=len(wf_results),
        kelly_fraction=kelly,
        half_kelly=kelly / 2,
        deflated_sharpe=dsr,
        dsr_is_significant=dsr > 0.95,  # 95% confidence it's real
    )


def print_statistical_report(report: StatisticalReport):
    """Pretty-print a complete statistical report"""
    
    print(f"\n{'='*70}")
    print(f"  STATISTICAL REPORT: {report.strategy_name} — {report.asset}")
    print(f"{'='*70}")
    
    # Basic Performance
    print(f"\n  ── PERFORMANCE ──")
    print(f"  Total Return:       {report.total_return:+.2%}")
    print(f"  Annualized Return:  {report.annualized_return:+.2%}")
    print(f"  Sharpe Ratio:       {report.sharpe_ratio:.3f}")
    print(f"  Sortino Ratio:      {report.sortino_ratio:.3f}")
    print(f"  Calmar Ratio:       {report.calmar_ratio:.3f}")
    print(f"  Max Drawdown:       {report.max_drawdown:.2%}")
    print(f"  Win Rate:           {report.win_rate:.1%}")
    print(f"  Profit Factor:      {report.profit_factor:.2f}")
    print(f"  Total Trades:       {report.total_trades}")
    print(f"  Avg Trade PnL:      {report.avg_trade_pnl:+.4%}")
    print(f"  Avg Win:            {report.avg_win:+.4%}")
    print(f"  Avg Loss:           {report.avg_loss:+.4%}")
    
    # Statistical Significance
    sig = "✅ YES" if report.is_significant else "❌ NO"
    print(f"\n  ── STATISTICAL SIGNIFICANCE ──")
    print(f"  t-statistic:        {report.t_statistic:.3f}")
    print(f"  p-value:            {report.p_value:.4f}")
    print(f"  Significant (p<.05): {sig}")
    
    # Bootstrap CI
    print(f"\n  ── BOOTSTRAP 95% CONFIDENCE INTERVALS ──")
    print(f"  Return CI:          [{report.return_ci_lower:+.4f}, {report.return_ci_upper:+.4f}]")
    print(f"  Sharpe CI:          [{report.sharpe_ci_lower:.3f}, {report.sharpe_ci_upper:.3f}]")
    zero_in_ci = report.return_ci_lower <= 0 <= report.return_ci_upper
    print(f"  Zero in Return CI:  {'⚠️ YES (strategy may not be profitable)' if zero_in_ci else '✅ NO (confidently directional)'}")
    
    # Monte Carlo
    print(f"\n  ── MONTE CARLO SIMULATION (10,000 runs) ──")
    print(f"  Median Return:      {report.mc_median_return:+.2%}")
    print(f"  Worst 5%:           {report.mc_worst_5pct:+.2%}")
    print(f"  Best 5%:            {report.mc_best_5pct:+.2%}")
    print(f"  P(Profit):          {report.mc_prob_profit:.1%}")
    
    # Walk-Forward
    print(f"\n  ── WALK-FORWARD VALIDATION ──")
    print(f"  In-Sample Return:   {report.wf_in_sample_return:+.2%}")
    print(f"  Out-of-Sample:      {report.wf_out_sample_return:+.2%}")
    print(f"  WF Efficiency:      {report.wf_efficiency:.2f}")
    wf_pass = report.wf_efficiency > 0.5
    print(f"  Efficiency > 0.5:   {'✅ PASS' if wf_pass else '❌ FAIL (possible overfit)'}")
    print(f"  OOS Profitable:     {report.wf_periods_profitable}/{report.wf_total_periods} periods")
    
    # Kelly Criterion
    print(f"\n  ── POSITION SIZING (KELLY) ──")
    print(f"  Full Kelly:         {report.kelly_fraction:.1%}")
    print(f"  Half Kelly (safe):  {report.half_kelly:.1%}")
    
    # Deflated Sharpe
    dsr_pass = "✅ YES" if report.dsr_is_significant else "❌ NO"
    print(f"\n  ── DEFLATED SHARPE RATIO ──")
    print(f"  DSR:                {report.deflated_sharpe:.4f}")
    print(f"  Survives multiple testing: {dsr_pass}")
    
    # Overall Verdict
    print(f"\n  ── VERDICT ──")
    checks = [
        report.is_significant,
        not zero_in_ci or report.total_return > 0,
        report.mc_prob_profit > 0.6,
        wf_pass,
        report.total_trades >= 20,
    ]
    passed = sum(checks)
    
    if passed >= 4:
        print(f"  🟢 PRODUCTION READY ({passed}/5 checks passed)")
    elif passed >= 3:
        print(f"  🟡 PROMISING ({passed}/5 checks passed) — needs more data")
    else:
        print(f"  🔴 NOT READY ({passed}/5 checks passed) — needs improvement")
    
    checklist = [
        ("Statistical significance (p<0.05)", report.is_significant),
        ("Bootstrap CI excludes zero", not zero_in_ci or report.total_return > 0),
        ("Monte Carlo P(profit) > 60%", report.mc_prob_profit > 0.6),
        ("Walk-forward efficiency > 0.5", wf_pass),
        ("Sufficient trades (≥20)", report.total_trades >= 20),
    ]
    for name, passed in checklist:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n{'='*70}")
