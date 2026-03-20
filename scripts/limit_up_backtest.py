#!/usr/bin/env python3
"""
Limit-Up Pullback Backtest - Full A-share backtest
====================================================
Reads all CSV files from data/a_shares/, runs LimitUpPullback on each,
performs parameter sensitivity analysis, and outputs report to
docs/limit-up-pullback-report.md.

Usage:
    python scripts/limit_up_backtest.py
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

from src.strategies.limit_up_pullback import LimitUpPullback, LimitUpSignal


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
    """Load all CSV files from directory, filtering ST and low-volume stocks."""
    stocks = []
    csv_files = sorted(Path(data_dir).glob("*.csv"))
    skipped_st = 0
    skipped_vol = 0
    skipped_short = 0

    for f in csv_files:
        try:
            stock = load_csv(str(f))

            # Filter: need at least 30 days of data
            if len(stock.closes) < 30:
                skipped_short += 1
                continue

            # Filter: skip ST stocks (by filename heuristic)
            fname = f.stem.lower()
            if "st" in fname:
                skipped_st += 1
                continue

            # Filter: skip stocks with average daily amount < 50M
            avg_amount = np.mean(stock.amounts)
            if avg_amount < 50_000_000:
                skipped_vol += 1
                continue

            stocks.append(stock)
        except Exception as e:
            pass

    print(f"  Loaded {len(stocks)} stocks (skipped: {skipped_st} ST, "
          f"{skipped_vol} low-vol, {skipped_short} short)")
    return stocks


def run_single_config(stocks: list, strat: LimitUpPullback) -> list:
    """Run backtest with a single config on all stocks."""
    results = []
    for stock in stocks:
        result = strat.backtest(
            opens=stock.opens,
            highs=stock.highs,
            lows=stock.lows,
            closes=stock.closes,
            volumes=stock.volumes,
            code=stock.code,
        )
        results.append(result)
    return results


def aggregate_results(results: list) -> dict:
    """Aggregate per-stock results into overall statistics."""
    all_trades = []
    stocks_with_trades = 0

    for r in results:
        all_trades.extend(r["trades"])
        if r["total_trades"] > 0:
            stocks_with_trades += 1

    total_trades = len(all_trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "stocks_with_trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "median_return": 0,
            "max_return": 0,
            "min_return": 0,
            "avg_hold_days": 0,
            "by_pullback_days": {},
            "by_exit_reason": {},
        }

    returns = [t["return_pct"] for t in all_trades]
    winning = [r for r in returns if r > 0]
    hold_days = [t["hold_days"] for t in all_trades]

    # By pullback days
    by_pb = {}
    for t in all_trades:
        pd_key = t.get("pullback_days", "?")
        if pd_key not in by_pb:
            by_pb[pd_key] = {"returns": [], "count": 0}
        by_pb[pd_key]["returns"].append(t["return_pct"])
        by_pb[pd_key]["count"] += 1

    for k in by_pb:
        rets = by_pb[k]["returns"]
        wins = [r for r in rets if r > 0]
        by_pb[k]["win_rate"] = len(wins) / len(rets) * 100 if rets else 0
        by_pb[k]["avg_return"] = float(np.mean(rets)) if rets else 0

    # By exit reason
    by_exit = {}
    for t in all_trades:
        reason = t.get("exit_reason", "unknown")
        if reason not in by_exit:
            by_exit[reason] = {"count": 0, "returns": []}
        by_exit[reason]["count"] += 1
        by_exit[reason]["returns"].append(t["return_pct"])

    for k in by_exit:
        rets = by_exit[k]["returns"]
        by_exit[k]["avg_return"] = float(np.mean(rets)) if rets else 0

    return {
        "total_trades": total_trades,
        "stocks_with_trades": stocks_with_trades,
        "win_rate": len(winning) / total_trades * 100,
        "avg_return": float(np.mean(returns)),
        "median_return": float(np.median(returns)),
        "max_return": float(np.max(returns)),
        "min_return": float(np.min(returns)),
        "avg_hold_days": float(np.mean(hold_days)),
        "by_pullback_days": by_pb,
        "by_exit_reason": by_exit,
    }


def sensitivity_analysis(stocks: list) -> dict:
    """Run parameter sweep and return results by config."""
    configs = {}

    # 1. Pullback days: 2 vs 3 vs 4
    print("  Analyzing pullback day sensitivity...")
    for pb_days in [2, 3, 4]:
        strat = LimitUpPullback(
            min_pullback_days=pb_days, max_pullback_days=pb_days,
            tp_pct=10.0, sl_pct=5.0, max_volume_ratio=0.6,
        )
        results = run_single_config(stocks, strat)
        agg = aggregate_results(results)
        configs[f"pullback_{pb_days}d"] = agg

    # 2. Take profit: 10% vs 15% vs 20%
    print("  Analyzing take-profit sensitivity...")
    for tp in [10, 15, 20]:
        strat = LimitUpPullback(tp_pct=float(tp), sl_pct=5.0)
        results = run_single_config(stocks, strat)
        agg = aggregate_results(results)
        configs[f"tp_{tp}pct"] = agg

    # 3. Volume ratio: 40% vs 50% vs 60%
    print("  Analyzing volume-ratio sensitivity...")
    for vr in [0.4, 0.5, 0.6]:
        strat = LimitUpPullback(max_volume_ratio=vr)
        results = run_single_config(stocks, strat)
        agg = aggregate_results(results)
        configs[f"vol_{int(vr*100)}pct"] = agg

    return configs


def generate_report(
    agg: dict,
    sensitivity: dict,
    elapsed: float,
    total_stocks: int,
) -> str:
    """Generate the markdown report."""
    lines = []
    lines.append("# 涨停回调不破底 - 回测报告")
    lines.append("")
    lines.append(f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**回测耗时**: {elapsed:.1f} 秒")
    lines.append(f"**股票数量**: {total_stocks}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Strategy overview
    lines.append("## 1. 策略概述")
    lines.append("")
    lines.append("**核心思路**: 涨停板 → 回调不破底 → 缩量确认 → T+1买入")
    lines.append("")
    lines.append("### 买入条件")
    lines.append("- 某天涨停（主板+10%，创业/科创+20%）")
    lines.append("- 接下来2-4天回调")
    lines.append("- 回调不破涨停大阳线的最低价")
    lines.append("- 缩量（回调平均量 < 涨停日量的60%）")
    lines.append("- T+1开盘价买入")
    lines.append("")
    lines.append("### 卖出条件")
    lines.append("- 止盈: +10%")
    lines.append("- 止损: -5%")
    lines.append("- 最长持有: 5天")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Overall results
    lines.append("## 2. 总体回测结果（默认参数）")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总交易次数 | {agg['total_trades']} |")
    lines.append(f"| 产生交易的股票数 | {agg['stocks_with_trades']} |")
    lines.append(f"| 胜率 | {agg['win_rate']:.1f}% |")
    lines.append(f"| 平均收益率 | {agg['avg_return']:.2f}% |")
    lines.append(f"| 中位数收益率 | {agg['median_return']:.2f}% |")
    lines.append(f"| 最大单笔收益 | {agg['max_return']:.2f}% |")
    lines.append(f"| 最大单笔亏损 | {agg['min_return']:.2f}% |")
    lines.append(f"| 平均持有天数 | {agg['avg_hold_days']:.1f} |")
    lines.append("")

    # By pullback days
    if agg["by_pullback_days"]:
        lines.append("### 按回调天数分析")
        lines.append("")
        lines.append("| 回调天数 | 交易数 | 胜率 | 平均收益 |")
        lines.append("|----------|--------|------|----------|")
        for k in sorted(agg["by_pullback_days"].keys()):
            d = agg["by_pullback_days"][k]
            lines.append(f"| {k} | {d['count']} | {d['win_rate']:.1f}% | {d['avg_return']:.2f}% |")
        lines.append("")

    # By exit reason
    if agg["by_exit_reason"]:
        lines.append("### 按退出原因分析")
        lines.append("")
        lines.append("| 退出原因 | 次数 | 平均收益 |")
        lines.append("|----------|------|----------|")
        for k, d in agg["by_exit_reason"].items():
            lines.append(f"| {k} | {d['count']} | {d['avg_return']:.2f}% |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Sensitivity analysis
    lines.append("## 3. 参数敏感度分析")
    lines.append("")

    # Pullback days
    lines.append("### 3.1 回调天数 (2天 vs 3天 vs 4天)")
    lines.append("")
    lines.append("| 回调天数 | 交易数 | 胜率 | 平均收益 | 中位数收益 |")
    lines.append("|----------|--------|------|----------|------------|")
    for days in [2, 3, 4]:
        key = f"pullback_{days}d"
        if key in sensitivity:
            d = sensitivity[key]
            lines.append(f"| {days}天 | {d['total_trades']} | {d['win_rate']:.1f}% | "
                        f"{d['avg_return']:.2f}% | {d['median_return']:.2f}% |")
    lines.append("")

    # Take profit
    lines.append("### 3.2 止盈比例 (10% vs 15% vs 20%)")
    lines.append("")
    lines.append("| 止盈 | 交易数 | 胜率 | 平均收益 | 最大收益 |")
    lines.append("|------|--------|------|----------|----------|")
    for tp in [10, 15, 20]:
        key = f"tp_{tp}pct"
        if key in sensitivity:
            d = sensitivity[key]
            lines.append(f"| {tp}% | {d['total_trades']} | {d['win_rate']:.1f}% | "
                        f"{d['avg_return']:.2f}% | {d['max_return']:.2f}% |")
    lines.append("")

    # Volume ratio
    lines.append("### 3.3 缩量比例 (40% vs 50% vs 60%)")
    lines.append("")
    lines.append("| 缩量阈值 | 交易数 | 胜率 | 平均收益 |")
    lines.append("|----------|--------|------|----------|")
    for vr in [40, 50, 60]:
        key = f"vol_{vr}pct"
        if key in sensitivity:
            d = sensitivity[key]
            lines.append(f"| {vr}% | {d['total_trades']} | {d['win_rate']:.1f}% | "
                        f"{d['avg_return']:.2f}% |")
    lines.append("")

    lines.append("---")
    lines.append("")

    # Findings
    lines.append("## 4. 关键发现")
    lines.append("")

    # Find best pullback days
    best_pb = None
    best_pb_wr = -1
    for days in [2, 3, 4]:
        key = f"pullback_{days}d"
        if key in sensitivity and sensitivity[key]["total_trades"] > 0:
            if sensitivity[key]["win_rate"] > best_pb_wr:
                best_pb_wr = sensitivity[key]["win_rate"]
                best_pb = days

    if best_pb:
        lines.append(f"- **最优回调天数**: {best_pb}天 (胜率 {best_pb_wr:.1f}%)")

    # Find best TP
    best_tp = None
    best_tp_ret = -999
    for tp in [10, 15, 20]:
        key = f"tp_{tp}pct"
        if key in sensitivity and sensitivity[key]["total_trades"] > 0:
            if sensitivity[key]["avg_return"] > best_tp_ret:
                best_tp_ret = sensitivity[key]["avg_return"]
                best_tp = tp

    if best_tp:
        lines.append(f"- **最优止盈**: {best_tp}% (平均收益 {best_tp_ret:.2f}%)")

    # Find best volume ratio
    best_vr = None
    best_vr_wr = -1
    for vr in [40, 50, 60]:
        key = f"vol_{vr}pct"
        if key in sensitivity and sensitivity[key]["total_trades"] > 0:
            if sensitivity[key]["win_rate"] > best_vr_wr:
                best_vr_wr = sensitivity[key]["win_rate"]
                best_vr = vr

    if best_vr:
        lines.append(f"- **最优缩量比例**: {best_vr}% (胜率 {best_vr_wr:.1f}%)")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. 注意事项")
    lines.append("")
    lines.append("- 回测不含手续费和滑点（实际收益会更低）")
    lines.append("- 涨停封板买不到的情况未考虑")
    lines.append("- 结果基于历史数据，不保证未来收益")
    lines.append("- 建议结合成交额、板块、市场情绪综合判断")
    lines.append("")

    return "\n".join(lines)


def main():
    data_dir = os.path.join(str(PROJECT_ROOT), "data", "a_shares")
    docs_dir = os.path.join(str(PROJECT_ROOT), "docs")
    os.makedirs(docs_dir, exist_ok=True)

    print("=== 涨停回调不破底 - 全量回测 ===")
    print()

    # Load data
    print("1. Loading stock data...")
    t0 = time.time()
    stocks = load_all_stocks(data_dir)
    print(f"   Loaded {len(stocks)} stocks in {time.time() - t0:.1f}s")

    if not stocks:
        print("   No stock data found! Please check data/a_shares/ directory.")
        return

    # Default config backtest
    print()
    print("2. Running default config backtest...")
    t1 = time.time()
    default_strat = LimitUpPullback()
    default_results = run_single_config(stocks, default_strat)
    default_agg = aggregate_results(default_results)
    print(f"   Done in {time.time() - t1:.1f}s — {default_agg['total_trades']} trades found")
    print(f"   Win rate: {default_agg['win_rate']:.1f}%, Avg return: {default_agg['avg_return']:.2f}%")

    # Sensitivity analysis
    print()
    print("3. Running sensitivity analysis...")
    t2 = time.time()
    sensitivity = sensitivity_analysis(stocks)
    print(f"   Done in {time.time() - t2:.1f}s")

    # Generate report
    print()
    print("4. Generating report...")
    elapsed = time.time() - t0
    report = generate_report(default_agg, sensitivity, elapsed, len(stocks))

    report_path = os.path.join(docs_dir, "limit-up-pullback-report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"   Report saved to {report_path}")

    print()
    print("=== Done! ===")


if __name__ == "__main__":
    main()
