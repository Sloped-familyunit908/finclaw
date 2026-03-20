#!/usr/bin/env python3
"""
Golden Dip Backtest - Full A-share backtest
===========================================
Reads all CSV files from data/a_shares/, runs GoldenDipStrategy on each,
and produces a comprehensive report at docs/golden-dip-report.md.

Usage:
    python scripts/golden_dip_backtest.py
"""

import sys
import os
import csv
import time
from pathlib import Path
from dataclasses import dataclass

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.golden_dip import GoldenDipStrategy, BacktestResult, BacktestTrade


@dataclass
class StockData:
    """Parsed stock data from CSV."""
    code: str
    dates: list
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    volumes: np.ndarray
    amounts: np.ndarray


def load_csv(filepath: str) -> StockData:
    """Load a single CSV file into StockData."""
    dates, opens, highs, lows, closes, volumes, amounts = [], [], [], [], [], [], []
    code = ""

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not code:
                code = row.get("code", "")
            dates.append(row["date"])
            opens.append(float(row["open"]))
            highs.append(float(row["high"]))
            lows.append(float(row["low"]))
            closes.append(float(row["close"]))
            volumes.append(float(row["volume"]))
            amounts.append(float(row.get("amount", 0)))

    return StockData(
        code=code,
        dates=dates,
        opens=np.array(opens),
        highs=np.array(highs),
        lows=np.array(lows),
        closes=np.array(closes),
        volumes=np.array(volumes),
        amounts=np.array(amounts),
    )


def load_all_stocks(data_dir: str) -> list:
    """Load all CSV files from directory."""
    stocks = []
    csv_files = sorted(Path(data_dir).glob("*.csv"))
    for f in csv_files:
        try:
            stock = load_csv(str(f))
            if len(stock.closes) >= 150:  # need enough data
                stocks.append(stock)
        except Exception as e:
            print(f"  Warning: Failed to load {f.name}: {e}")
    return stocks


def run_backtest_all(stocks: list, strategy: GoldenDipStrategy) -> list:
    """Run backtest on all stocks."""
    results = []
    for i, stock in enumerate(stocks):
        if (i + 1) % 100 == 0:
            print(f"  Processing {i + 1}/{len(stocks)}...")

        result = strategy.backtest(
            prices=stock.closes,
            volumes=stock.volumes,
            open_prices=stock.opens,
            dates=np.array(stock.dates),
            code=stock.code,
        )
        results.append(result)
    return results


def analyze_false_signals(results_with_trades: list) -> dict:
    """Analyze losing trades to understand false signals."""
    total_losing = 0
    reasons = {}
    losing_details = []

    for result in results_with_trades:
        for trade in result.trades:
            if trade.return_pct <= 0:
                total_losing += 1
                reason = trade.exit_reason
                reasons[reason] = reasons.get(reason, 0) + 1
                if trade.return_pct < -10:  # significant losses
                    losing_details.append({
                        "code": trade.code,
                        "entry_date": trade.entry_date,
                        "exit_date": trade.exit_date,
                        "return_pct": trade.return_pct,
                        "holding_days": trade.holding_days,
                        "exit_reason": trade.exit_reason,
                        "max_dd_during": trade.max_drawdown_during,
                    })

    losing_details.sort(key=lambda x: x["return_pct"])

    return {
        "total_losing": total_losing,
        "reasons": reasons,
        "worst_trades": losing_details[:20],  # top 20 worst
    }


def generate_report(
    results: list,
    strategy: GoldenDipStrategy,
    elapsed_seconds: float,
    total_stocks: int,
) -> str:
    """Generate markdown report."""
    # Aggregate statistics
    all_trades = []
    active_results = []
    for r in results:
        all_trades.extend(r.trades)
        if r.total_trades > 0:
            active_results.append(r)

    total_trades = len(all_trades)
    winning = [t for t in all_trades if t.return_pct > 0]
    losing = [t for t in all_trades if t.return_pct <= 0]

    win_rate = len(winning) / total_trades * 100 if total_trades > 0 else 0

    returns = [t.return_pct for t in all_trades]
    avg_return = np.mean(returns) if returns else 0
    median_return = np.median(returns) if returns else 0
    max_gain = max(returns) if returns else 0
    max_loss = min(returns) if returns else 0

    holding_days = [t.holding_days for t in all_trades]
    avg_holding = np.mean(holding_days) if holding_days else 0
    median_holding = np.median(holding_days) if holding_days else 0

    pain_values = [t.max_drawdown_during for t in all_trades]
    avg_pain = np.mean(pain_values) if pain_values else 0

    # Per-stock annualized returns for stocks with trades
    annualized_returns = [r.annualized_return_pct for r in active_results if r.annualized_return_pct != 0]
    avg_annualized = np.mean(annualized_returns) if annualized_returns else 0
    median_annualized = np.median(annualized_returns) if annualized_returns else 0

    max_drawdowns = [r.max_drawdown_pct for r in active_results if r.max_drawdown_pct > 0]
    avg_max_dd = np.mean(max_drawdowns) if max_drawdowns else 0

    calmar_ratios = [r.calmar_ratio for r in active_results if r.calmar_ratio != 0 and not np.isinf(r.calmar_ratio)]
    avg_calmar = np.mean(calmar_ratios) if calmar_ratios else 0

    # Holding days distribution
    total_dist = {"<7d": 0, "7-30d": 0, "30-90d": 0, "90-180d": 0, ">180d": 0}
    for r in active_results:
        for k, v in r.holding_days_distribution.items():
            total_dist[k] = total_dist.get(k, 0) + v

    # False signal analysis
    false_signals = analyze_false_signals(active_results)

    # Exit reason distribution
    exit_reasons = {}
    for t in all_trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    # Top winners
    top_winners = sorted(all_trades, key=lambda t: t.return_pct, reverse=True)[:15]
    top_losers = sorted(all_trades, key=lambda t: t.return_pct)[:15]

    # Build report
    lines = []
    lines.append("# 黄金坑买入策略 - 回测报告")
    lines.append("")
    lines.append(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**回测耗时**: {elapsed_seconds:.1f} 秒")
    lines.append(f"**数据范围**: 2024-03 到 2026-03 (约2年日线)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. 策略概述")
    lines.append("")
    lines.append("**核心思路**: 确认大牛股 → 等回调黄金坑 → 反人性买入 → 坚定持有")
    lines.append("")
    lines.append("### 买入条件")
    lines.append(f"- 120日 R² > {strategy.r2_bull_threshold} (清晰上升趋势)")
    lines.append(f"- 120日斜率 > 0 (方向向上)")
    lines.append(f"- 60日收益率 > {strategy.return_60d_min*100:.0f}% (确实在涨)")
    lines.append(f"- 从近期高点回调 > {strategy.pullback_pct*100:.0f}% (跌出黄金坑)")
    lines.append(f"- RSI < {strategy.rsi_oversold} (短期超卖)")
    lines.append(f"- 120日 R² > {strategy.r2_dip_threshold} (大趋势没破)")
    lines.append(f"- 量能萎缩 < {strategy.volume_shrink_ratio*100:.0f}% 均量 (恐慌抛售结束)")
    lines.append("")
    lines.append("### 仓位管理")
    lines.append(f"- 首次买入: {strategy.position_initial*100:.0f}% 仓位")
    lines.append(f"- 继续下跌 {strategy.add_drop_pct*100:.0f}%: 加仓到 {strategy.position_add1*100:.0f}%")
    lines.append(f"- 再跌 {strategy.add_drop_pct*100:.0f}%: 满仓 {strategy.position_add2*100:.0f}%")
    lines.append("")
    lines.append("### 卖出条件 (反人性：不轻易卖)")
    lines.append(f"- 120日 R² < {strategy.r2_sell_threshold} (趋势真的破了)")
    lines.append(f"- 从最高点回撤 > {strategy.trailing_stop*100:.0f}% (止损保护)")
    lines.append(f"- RSI > {strategy.rsi_overheat} 连续 {strategy.rsi_overheat_days} 天 (极度过热)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. 回测统计总览")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总股票数 | {total_stocks} |")
    lines.append(f"| 有效回测股票数 | {len(active_results)} |")
    lines.append(f"| 总交易次数 | {total_trades} |")
    lines.append(f"| 盈利交易 | {len(winning)} |")
    lines.append(f"| 亏损交易 | {len(losing)} |")
    lines.append(f"| **胜率** | **{win_rate:.1f}%** |")
    lines.append(f"| 平均收益率 | {avg_return:+.2f}% |")
    lines.append(f"| 中位数收益率 | {median_return:+.2f}% |")
    lines.append(f"| 最大单笔收益 | {max_gain:+.2f}% |")
    lines.append(f"| 最大单笔亏损 | {max_loss:+.2f}% |")
    lines.append(f"| 平均年化收益率 | {avg_annualized:+.2f}% |")
    lines.append(f"| 中位数年化收益率 | {median_annualized:+.2f}% |")
    lines.append(f"| 平均最大回撤 | {avg_max_dd:.2f}% |")
    lines.append(f"| 平均 Calmar 比率 | {avg_calmar:.2f} |")
    lines.append(f"| 平均持仓天数 | {avg_holding:.1f} 天 |")
    lines.append(f"| 中位数持仓天数 | {median_holding:.1f} 天 |")
    lines.append(f"| **痛苦指数** | **{avg_pain:.2f}%** |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. 持仓天数分布")
    lines.append("")
    lines.append("| 区间 | 交易次数 | 占比 |")
    lines.append("|------|---------|------|")
    for bucket, count in total_dist.items():
        pct = count / total_trades * 100 if total_trades > 0 else 0
        lines.append(f"| {bucket} | {count} | {pct:.1f}% |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. 退出原因分布")
    lines.append("")
    lines.append("| 退出原因 | 次数 | 占比 |")
    lines.append("|---------|------|------|")
    for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
        pct = count / total_trades * 100 if total_trades > 0 else 0
        lines.append(f"| {reason} | {count} | {pct:.1f}% |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Top 15 最佳交易")
    lines.append("")
    lines.append("| 代码 | 买入日 | 卖出日 | 收益率 | 持仓天数 | 退出原因 |")
    lines.append("|------|-------|-------|--------|---------|---------|")
    for t in top_winners:
        lines.append(f"| {t.code} | {t.entry_date} | {t.exit_date} | {t.return_pct:+.2f}% | {t.holding_days} | {t.exit_reason} |")
    lines.append("")
    lines.append("## 6. Top 15 最差交易")
    lines.append("")
    lines.append("| 代码 | 买入日 | 卖出日 | 收益率 | 持仓天数 | 期间最大回撤 | 退出原因 |")
    lines.append("|------|-------|-------|--------|---------|------------|---------|")
    for t in top_losers:
        lines.append(f"| {t.code} | {t.entry_date} | {t.exit_date} | {t.return_pct:+.2f}% | {t.holding_days} | {t.max_drawdown_during:.1f}% | {t.exit_reason} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 7. 假信号分析")
    lines.append("")
    lines.append(f"**总亏损交易数**: {false_signals['total_losing']}")
    lines.append("")
    lines.append("### 亏损原因分布")
    lines.append("")
    lines.append("| 退出原因 | 亏损次数 |")
    lines.append("|---------|---------|")
    for reason, count in sorted(false_signals["reasons"].items(), key=lambda x: -x[1]):
        lines.append(f"| {reason} | {count} |")
    lines.append("")
    if false_signals["worst_trades"]:
        lines.append("### 最严重的假信号 (亏损>10%)")
        lines.append("")
        lines.append("| 代码 | 买入日 | 卖出日 | 收益率 | 持仓天数 | 期间最大回撤 | 退出原因 |")
        lines.append("|------|-------|-------|--------|---------|------------|---------|")
        for t in false_signals["worst_trades"]:
            lines.append(f"| {t['code']} | {t['entry_date']} | {t['exit_date']} | {t['return_pct']:+.2f}% | {t['holding_days']} | {t['max_dd_during']:.1f}% | {t['exit_reason']} |")
        lines.append("")
    lines.append("### 假信号成因分析")
    lines.append("")
    lines.append("1. **趋势看似成立但实际即将逆转**: R²和斜率在信号产生时满足条件，但随后趋势迅速恶化")
    lines.append("2. **市场系统性风险**: 大盘下跌拖累个股，即使个股基本面未变")
    lines.append("3. **回调深度不够**: 10%回调阈值可能在某些情况下不够深，买入后继续大跌")
    lines.append("")
    lines.append("### 建议的过滤器改进")
    lines.append("")
    lines.append("1. **加入大盘过滤**: 当沪深300指数处于下跌趋势时，不触发买入信号")
    lines.append("2. **行业动量过滤**: 验证所在行业是否处于上升通道")
    lines.append("3. **更严格的量价确认**: 要求底部出现放量阳线作为反转确认")
    lines.append("4. **多周期R²确认**: 不仅看120日R²，还要看60日和30日R²是否协同")
    lines.append("5. **换手率过滤**: 极低换手率可能意味着流动性陷阱")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 8. 策略对比")
    lines.append("")
    lines.append("| 策略 | 平均年化 | 平均最大回撤 | 平均Calmar | 平均持仓天数 | 操作难度 |")
    lines.append("|------|---------|------------|-----------|-------------|---------|")
    lines.append(f"| cn_scanner短线 | 待测 | 待测 | 待测 | ~3天 | 每天操作，高频 |")
    lines.append(f"| 趋势发现hold | 待测 | 待测 | 待测 | 数月 | 买入后不管 |")
    lines.append(f"| **黄金坑买入** | **{avg_annualized:+.2f}%** | **{avg_max_dd:.2f}%** | **{avg_calmar:.2f}** | **{avg_holding:.0f}天** | **偶尔操作** |")
    lines.append("")
    lines.append("### 策略定位分析")
    lines.append("")
    lines.append("- **cn_scanner短线**: 高频交易，每天需要盯盘，适合专业交易者")
    lines.append("- **趋势发现hold**: 发现趋势后长期持有，最省心但需要忍受大波动")
    lines.append("- **黄金坑买入**: 介于两者之间，在确认趋势的基础上等待黄金坑买入，")
    lines.append("  既避免了追高，又不需要每天操作。核心优势是**买入时机更好**，")
    lines.append("  通过等待回调来获得更好的风险收益比。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 9. 结论与建议")
    lines.append("")
    if total_trades > 0:
        if win_rate >= 60:
            lines.append(f"✅ **策略表现良好**: 胜率 {win_rate:.1f}%，平均收益 {avg_return:+.2f}%")
        elif win_rate >= 45:
            lines.append(f"⚠️ **策略表现中等**: 胜率 {win_rate:.1f}%，需要进一步优化")
        else:
            lines.append(f"❌ **策略表现较差**: 胜率 {win_rate:.1f}%，建议调整参数或增加过滤条件")
        lines.append("")
        lines.append(f"- 痛苦指数 {avg_pain:.2f}% 表示持仓期间平均承受的最大回调")
        if avg_pain > 15:
            lines.append("- ⚠️ 痛苦指数较高，持仓过程心理压力大，需要强大的反人性能力")
        lines.append(f"- 平均持仓 {avg_holding:.0f} 天，属于中线操作")
    else:
        lines.append("⚠️ **未产生任何交易信号**: 当前参数在此数据集上过于严格")
        lines.append("")
        lines.append("建议:")
        lines.append("- 降低 R² 阈值 (如 0.5 → 0.4)")
        lines.append("- 扩大回调阈值范围 (如 10% → 8%)")
        lines.append("- 放宽 RSI 超卖条件 (如 35 → 40)")
        lines.append("- 检查数据是否包含足够的牛股样本")
    lines.append("")

    return "\n".join(lines)


def main():
    data_dir = PROJECT_ROOT / "data" / "a_shares"
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("  黄金坑买入策略 - 全面回测 🦀")
    print("=" * 60)
    print()

    # Load data
    print(f"[1/4] 加载数据 ({data_dir})...")
    stocks = load_all_stocks(str(data_dir))
    print(f"  ✅ 加载了 {len(stocks)} 只有效股票")
    print()

    # Initialize strategy
    strategy = GoldenDipStrategy()

    # Run backtest
    print(f"[2/4] 运行回测...")
    start_time = time.time()
    results = run_backtest_all(stocks, strategy)
    elapsed = time.time() - start_time
    print(f"  ✅ 回测完成, 耗时 {elapsed:.1f} 秒")
    print()

    # Statistics summary
    active_results = [r for r in results if r.total_trades > 0]
    all_trades = []
    for r in results:
        all_trades.extend(r.trades)

    print(f"[3/4] 统计结果...")
    print(f"  触发交易的股票: {len(active_results)}/{len(stocks)}")
    print(f"  总交易次数: {len(all_trades)}")
    if all_trades:
        returns = [t.return_pct for t in all_trades]
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r <= 0]
        print(f"  胜率: {len(winners)/len(all_trades)*100:.1f}%")
        print(f"  平均收益率: {np.mean(returns):+.2f}%")
        print(f"  最大收益: {max(returns):+.2f}%")
        print(f"  最大亏损: {min(returns):+.2f}%")
    print()

    # Generate report
    print(f"[4/4] 生成报告...")
    report = generate_report(results, strategy, elapsed, len(stocks))
    report_path = docs_dir / "golden-dip-report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  ✅ 报告已保存到 {report_path}")
    print()

    print("=" * 60)
    print("  回测完成！ 🦀🎉")
    print("=" * 60)


if __name__ == "__main__":
    main()
