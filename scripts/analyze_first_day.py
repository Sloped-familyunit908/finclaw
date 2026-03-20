#!/usr/bin/env python3
"""
Analyze CN Scanner's "First-Day Experience"
=============================================
Reads local A-share CSV data, simulates cn_scanner stock picking,
and analyzes what happens on Day 1, Day 2, Day 3 after a buy signal.

Key questions:
  - What % of picks lose money on Day 1?
  - Is it because we're chasing highs? Or broad market pullback?
  - What can we do to fix it?

Usage:
    python scripts/analyze_first_day.py

Output:
    docs/first-day-analysis.md
"""

import sys
import os
import csv
import time
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cn_scanner import compute_score_v3, CN_UNIVERSE


# ═══════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════

def ticker_to_filename(ticker: str) -> str:
    """Convert '600519.SS' → 'sh_600519.csv'."""
    code = ticker.split(".")[0]
    return f"sh_{code}.csv"


def load_stock_csv(filepath: str) -> dict | None:
    """Load a CSV into arrays. Returns None if insufficient data."""
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dates.append(row["date"])
                opens.append(float(row["open"]))
                highs.append(float(row["high"]))
                lows.append(float(row["low"]))
                closes.append(float(row["close"]))
                volumes.append(float(row["volume"]))
    except (FileNotFoundError, KeyError, ValueError):
        return None

    if len(closes) < 60:
        return None

    return {
        "dates": dates,
        "open": np.array(opens, dtype=np.float64),
        "high": np.array(highs, dtype=np.float64),
        "low": np.array(lows, dtype=np.float64),
        "close": np.array(closes, dtype=np.float64),
        "volume": np.array(volumes, dtype=np.float64),
    }


# ═══════════════════════════════════════════════════════════════════
# Signal Simulation
# ═══════════════════════════════════════════════════════════════════

def simulate_scanner(data_dir: str, min_score: int = 6) -> list[dict]:
    """Walk through each day, score all stocks, collect buy signals.

    Returns list of signal events:
      {ticker, name, sector, signal_date, signal_idx,
       score, signal, entry_close, day1/2/3/5_return, ...}
    """
    print(f"Loading stock data from {data_dir} ...")

    # Load all stocks that are in CN_UNIVERSE and have local data
    stock_data = {}
    ticker_to_name = {}
    ticker_to_sector = {}

    for ticker, name, sector in CN_UNIVERSE:
        fname = ticker_to_filename(ticker)
        fpath = os.path.join(data_dir, fname)
        data = load_stock_csv(fpath)
        if data is not None:
            stock_data[ticker] = data
            ticker_to_name[ticker] = name
            ticker_to_sector[ticker] = sector

    print(f"  Loaded {len(stock_data)} stocks from CN_UNIVERSE")

    # Also load non-universe stocks if they exist
    all_csv = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    for fname in all_csv:
        code = fname.replace("sh_", "").replace(".csv", "")
        # Try to map to ticker format
        if code.startswith("6"):
            ticker = f"{code}.SS"
        else:
            ticker = f"{code}.SZ"

        if ticker not in stock_data:
            fpath = os.path.join(data_dir, fname)
            data = load_stock_csv(fpath)
            if data is not None:
                stock_data[ticker] = data
                ticker_to_name.setdefault(ticker, code)
                ticker_to_sector.setdefault(ticker, "unknown")

    print(f"  Total stocks with data: {len(stock_data)}")

    # Find the common date range
    all_lengths = [len(d["close"]) for d in stock_data.values()]
    if not all_lengths:
        print("  No data!")
        return []

    min_len = min(all_lengths)
    print(f"  Min data length: {min_len} days")

    # Walk forward: score each stock on each day
    signals = []
    warmup = 35  # need at least 30 bars for scoring, plus some buffer
    # Don't scan the last 5 days (need forward returns)
    scan_end = min_len - 6

    # For efficiency, only scan CN_UNIVERSE stocks (the ones the scanner actually picks)
    universe_tickers = [t for t, _, _ in CN_UNIVERSE if t in stock_data]
    print(f"  Scanning {len(universe_tickers)} universe stocks across {scan_end - warmup} days ...")

    t0 = time.time()

    for day_idx in range(warmup, scan_end):
        for ticker in universe_tickers:
            data = stock_data[ticker]
            if day_idx >= len(data["close"]) - 5:
                continue

            close_slice = data["close"][:day_idx + 1]
            volume_slice = data["volume"][:day_idx + 1]
            open_slice = data["open"][:day_idx + 1]
            high_slice = data["high"][:day_idx + 1]
            low_slice = data["low"][:day_idx + 1]

            result = compute_score_v3(close_slice, volume_slice, open_slice, high_slice, low_slice)

            if result["score"] >= min_score:
                signal_close = data["close"][day_idx]
                signal_date = data["dates"][day_idx]

                # T+1 buy at next day's open (A-share T+1 rule)
                buy_price = data["open"][day_idx + 1]

                # Forward returns from BUY price (T+1 open)
                returns = {}
                for fwd in [1, 2, 3, 5]:
                    fwd_idx = day_idx + 1 + fwd
                    if fwd_idx < len(data["close"]):
                        fwd_close = data["close"][fwd_idx]
                        returns[f"day{fwd}_return"] = (fwd_close / buy_price - 1) * 100
                    else:
                        returns[f"day{fwd}_return"] = None

                # Also compute "intraday return on entry day"
                # (how much did we lose from open to close on the buy day)
                entry_day_close = data["close"][day_idx + 1]
                entry_intraday_return = (entry_day_close / buy_price - 1) * 100

                # Was this a "chase high" entry?
                # Compare buy_price (T+1 open) vs signal_close (T close)
                gap_pct = (buy_price / signal_close - 1) * 100

                # How far is signal_close from 5-day high?
                lookback = min(5, day_idx + 1)
                recent_high = np.max(data["high"][day_idx - lookback + 1:day_idx + 1])
                pct_from_high = (signal_close / recent_high - 1) * 100

                # Market context: average return of all stocks on T+1
                # We'll compute this in a second pass

                signals.append({
                    "ticker": ticker,
                    "name": ticker_to_name.get(ticker, ""),
                    "sector": ticker_to_sector.get(ticker, ""),
                    "signal_date": signal_date,
                    "signal_idx": day_idx,
                    "score": result["score"],
                    "signal": result["signal"],
                    "reasons": result.get("reasons", []),
                    "signal_close": signal_close,
                    "buy_price": buy_price,
                    "gap_pct": gap_pct,
                    "pct_from_5d_high": pct_from_high,
                    "entry_intraday_return": entry_intraday_return,
                    **returns,
                })

    elapsed = time.time() - t0
    print(f"  Found {len(signals)} buy signals in {elapsed:.1f}s")

    # Second pass: compute market context for each signal
    # Average return of all stocks on T+1
    print("  Computing market context ...")
    date_to_market_return = {}
    for day_idx in range(warmup, scan_end):
        # Pick a reference date from any stock
        ref_date = None
        daily_returns = []
        for ticker in universe_tickers:
            data = stock_data[ticker]
            if day_idx + 1 < len(data["close"]) and day_idx < len(data["close"]):
                if ref_date is None:
                    ref_date = data["dates"][day_idx]
                ret = (data["close"][day_idx + 1] / data["close"][day_idx] - 1) * 100
                daily_returns.append(ret)
        if ref_date and daily_returns:
            date_to_market_return[ref_date] = np.mean(daily_returns)

    for sig in signals:
        sig["market_return_t1"] = date_to_market_return.get(sig["signal_date"], 0.0)

    return signals


# ═══════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze_signals(signals: list[dict]) -> dict:
    """Comprehensive analysis of first-day (and multi-day) performance."""
    if not signals:
        return {"error": "no_signals"}

    analysis = {}

    # ── Basic stats ──
    n = len(signals)
    analysis["total_signals"] = n

    # ── Day-by-day return distribution ──
    for day_label in ["day1", "day2", "day3", "day5"]:
        key = f"{day_label}_return"
        returns = [s[key] for s in signals if s[key] is not None]
        if returns:
            arr = np.array(returns)
            analysis[day_label] = {
                "count": len(returns),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "loss_pct": float(np.sum(arr < 0) / len(arr) * 100),
                "big_loss_pct": float(np.sum(arr < -3) / len(arr) * 100),
                "big_win_pct": float(np.sum(arr > 3) / len(arr) * 100),
                "p25": float(np.percentile(arr, 25)),
                "p75": float(np.percentile(arr, 75)),
            }

    # ── Entry intraday return (open→close on buy day) ──
    intraday = [s["entry_intraday_return"] for s in signals]
    arr = np.array(intraday)
    analysis["entry_intraday"] = {
        "mean": float(np.mean(arr)),
        "loss_pct": float(np.sum(arr < 0) / len(arr) * 100),
        "big_loss_pct": float(np.sum(arr < -2) / len(arr) * 100),
    }

    # ── Gap analysis (signal close → buy open) ──
    gaps = [s["gap_pct"] for s in signals]
    arr_gap = np.array(gaps)
    analysis["gap"] = {
        "mean": float(np.mean(arr_gap)),
        "median": float(np.median(arr_gap)),
        "gap_up_pct": float(np.sum(arr_gap > 0) / len(arr_gap) * 100),
        "gap_up_gt2pct": float(np.sum(arr_gap > 2) / len(arr_gap) * 100),
    }

    # ── Chase-high analysis: signals where gap > 2% ──
    chase_signals = [s for s in signals if s["gap_pct"] > 2]
    normal_signals = [s for s in signals if s["gap_pct"] <= 2]

    if chase_signals and normal_signals:
        chase_d1 = [s["day1_return"] for s in chase_signals if s["day1_return"] is not None]
        normal_d1 = [s["day1_return"] for s in normal_signals if s["day1_return"] is not None]
        analysis["chase_vs_normal"] = {
            "chase_count": len(chase_signals),
            "normal_count": len(normal_signals),
            "chase_day1_mean": float(np.mean(chase_d1)) if chase_d1 else 0,
            "normal_day1_mean": float(np.mean(normal_d1)) if normal_d1 else 0,
            "chase_day1_loss_pct": float(np.sum(np.array(chase_d1) < 0) / len(chase_d1) * 100) if chase_d1 else 0,
            "normal_day1_loss_pct": float(np.sum(np.array(normal_d1) < 0) / len(normal_d1) * 100) if normal_d1 else 0,
        }

    # ── Market context: did the market drop on signal day? ──
    market_up = [s for s in signals if s["market_return_t1"] > 0]
    market_down = [s for s in signals if s["market_return_t1"] <= 0]

    if market_up and market_down:
        up_d1 = [s["day1_return"] for s in market_up if s["day1_return"] is not None]
        down_d1 = [s["day1_return"] for s in market_down if s["day1_return"] is not None]
        analysis["market_context"] = {
            "market_up_days": len(market_up),
            "market_down_days": len(market_down),
            "d1_when_market_up": float(np.mean(up_d1)) if up_d1 else 0,
            "d1_when_market_down": float(np.mean(down_d1)) if down_d1 else 0,
            "loss_when_market_up": float(np.sum(np.array(up_d1) < 0) / len(up_d1) * 100) if up_d1 else 0,
            "loss_when_market_down": float(np.sum(np.array(down_d1) < 0) / len(down_d1) * 100) if down_d1 else 0,
        }

    # ── Score-based analysis: do higher-score picks do better? ──
    score_buckets = defaultdict(list)
    for s in signals:
        score = s["score"]
        if s["day1_return"] is not None:
            if score >= 14:
                score_buckets["14+ (strong buy)"].append(s["day1_return"])
            elif score >= 10:
                score_buckets["10-13 (buy)"].append(s["day1_return"])
            elif score >= 6:
                score_buckets["6-9 (watch)"].append(s["day1_return"])

    analysis["by_score"] = {}
    for bucket, returns in sorted(score_buckets.items()):
        arr = np.array(returns)
        analysis["by_score"][bucket] = {
            "count": len(returns),
            "mean_d1": float(np.mean(arr)),
            "loss_pct": float(np.sum(arr < 0) / len(arr) * 100),
        }

    # ── Sector analysis ──
    sector_d1 = defaultdict(list)
    for s in signals:
        if s["day1_return"] is not None:
            sector_d1[s["sector"]].append(s["day1_return"])

    analysis["by_sector"] = {}
    for sector, returns in sorted(sector_d1.items(), key=lambda x: -len(x[1])):
        if len(returns) >= 5:
            arr = np.array(returns)
            analysis["by_sector"][sector] = {
                "count": len(returns),
                "mean_d1": float(np.mean(arr)),
                "loss_pct": float(np.sum(arr < 0) / len(arr) * 100),
            }

    # ── Signal reason frequency ──
    reason_count = defaultdict(int)
    for s in signals:
        for r in s.get("reasons", []):
            reason_count[r] += 1
    analysis["top_reasons"] = dict(sorted(reason_count.items(), key=lambda x: -x[1])[:15])

    # ── Optimal hold period: when does avg return peak? ──
    for day_label in ["day1", "day2", "day3", "day5"]:
        key = f"{day_label}_return"
        returns = [s[key] for s in signals if s[key] is not None]
        if returns:
            analysis.setdefault("avg_by_day", {})[day_label] = float(np.mean(returns))

    return analysis


# ═══════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════

def generate_report(analysis: dict, signals: list[dict]) -> str:
    """Generate a Markdown report from the analysis."""
    lines = []
    lines.append("# CN Scanner 选股第一天表现分析")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    if "error" in analysis:
        lines.append("**Error:** No signals found. Check that `data/a_shares/` has sufficient data.")
        return "\n".join(lines)

    n = analysis["total_signals"]
    lines.append(f"## 📊 总览")
    lines.append("")
    lines.append(f"- **总信号数:** {n}")
    lines.append(f"- **扫描策略:** v3 (OHLCV signals)")
    lines.append(f"- **最低分数:** 6")
    lines.append(f"- **数据来源:** 本地 `data/a_shares/` CSV 文件")
    lines.append("")

    # ── Day-by-day returns ──
    lines.append("## 📈 买入后逐日收益分布")
    lines.append("")
    lines.append("| 指标 | Day 1 | Day 2 | Day 3 | Day 5 |")
    lines.append("|------|-------|-------|-------|-------|")

    for metric, label in [
        ("mean", "平均收益%"),
        ("median", "中位数%"),
        ("std", "标准差%"),
        ("loss_pct", "亏损比例%"),
        ("big_loss_pct", "大亏(>3%)比例%"),
        ("big_win_pct", "大赚(>3%)比例%"),
        ("p25", "25分位%"),
        ("p75", "75分位%"),
    ]:
        row = f"| {label} |"
        for day in ["day1", "day2", "day3", "day5"]:
            val = analysis.get(day, {}).get(metric, "-")
            if isinstance(val, float):
                row += f" {val:+.2f} |"
            else:
                row += f" {val} |"
        lines.append(row)

    lines.append("")

    # ── Entry intraday ──
    ei = analysis.get("entry_intraday", {})
    lines.append("## 🔍 买入当天表现（开盘买入→当天收盘）")
    lines.append("")
    lines.append(f"- **平均当天收益:** {ei.get('mean', 0):+.2f}%")
    lines.append(f"- **当天亏损比例:** {ei.get('loss_pct', 0):.1f}%")
    lines.append(f"- **当天大亏(>2%)比例:** {ei.get('big_loss_pct', 0):.1f}%")
    lines.append("")

    # ── Gap analysis ──
    gap = analysis.get("gap", {})
    lines.append("## 📊 跳空缺口分析（信号日收盘→买入日开盘）")
    lines.append("")
    lines.append(f"- **平均缺口:** {gap.get('mean', 0):+.2f}%")
    lines.append(f"- **中位缺口:** {gap.get('median', 0):+.2f}%")
    lines.append(f"- **高开比例:** {gap.get('gap_up_pct', 0):.1f}%")
    lines.append(f"- **大幅高开(>2%)比例:** {gap.get('gap_up_gt2pct', 0):.1f}%")
    lines.append("")
    if gap.get("mean", 0) > 0.5:
        lines.append("> ⚠️ **追高信号明显！** 信号发出后次日普遍高开，买入价已经偏高。")
        lines.append("")

    # ── Chase high vs normal ──
    cv = analysis.get("chase_vs_normal", {})
    if cv:
        lines.append("## 🏃 追高买入 vs 正常买入")
        lines.append("")
        lines.append("| 分组 | 数量 | Day1 平均收益% | Day1 亏损比例% |")
        lines.append("|------|------|----------------|----------------|")
        lines.append(f"| 追高(缺口>2%) | {cv.get('chase_count', 0)} | {cv.get('chase_day1_mean', 0):+.2f} | {cv.get('chase_day1_loss_pct', 0):.1f} |")
        lines.append(f"| 正常(缺口≤2%) | {cv.get('normal_count', 0)} | {cv.get('normal_day1_mean', 0):+.2f} | {cv.get('normal_day1_loss_pct', 0):.1f} |")
        lines.append("")

    # ── Market context ──
    mc = analysis.get("market_context", {})
    if mc:
        lines.append("## 🌊 市场环境影响")
        lines.append("")
        lines.append("| 市场状态 | 信号数 | Day1 平均收益% | Day1 亏损比例% |")
        lines.append("|----------|--------|----------------|----------------|")
        lines.append(f"| 大盘涨 | {mc.get('market_up_days', 0)} | {mc.get('d1_when_market_up', 0):+.2f} | {mc.get('loss_when_market_up', 0):.1f} |")
        lines.append(f"| 大盘跌 | {mc.get('market_down_days', 0)} | {mc.get('d1_when_market_down', 0):+.2f} | {mc.get('loss_when_market_down', 0):.1f} |")
        lines.append("")

    # ── By score ──
    by_score = analysis.get("by_score", {})
    if by_score:
        lines.append("## 🎯 分数段分析")
        lines.append("")
        lines.append("| 分数段 | 信号数 | Day1 平均收益% | Day1 亏损比例% |")
        lines.append("|--------|--------|----------------|----------------|")
        for bucket, stats in sorted(by_score.items()):
            lines.append(f"| {bucket} | {stats['count']} | {stats['mean_d1']:+.2f} | {stats['loss_pct']:.1f} |")
        lines.append("")

    # ── By sector ──
    by_sector = analysis.get("by_sector", {})
    if by_sector:
        lines.append("## 🏭 行业分析 (Top)")
        lines.append("")
        lines.append("| 行业 | 信号数 | Day1 平均收益% | Day1 亏损比例% |")
        lines.append("|------|--------|----------------|----------------|")
        for sector, stats in list(by_sector.items())[:10]:
            lines.append(f"| {sector} | {stats['count']} | {stats['mean_d1']:+.2f} | {stats['loss_pct']:.1f} |")
        lines.append("")

    # ── Avg return by day ──
    avg_by_day = analysis.get("avg_by_day", {})
    if avg_by_day:
        lines.append("## ⏱️ 最佳持有期")
        lines.append("")
        for day_label, avg_ret in avg_by_day.items():
            emoji = "🟢" if avg_ret > 0 else "🔴"
            lines.append(f"- **{day_label}:** {avg_ret:+.2f}% {emoji}")
        lines.append("")

    # ── Top reasons ──
    top_reasons = analysis.get("top_reasons", {})
    if top_reasons:
        lines.append("## 📋 最常见的买入信号理由")
        lines.append("")
        for reason, count in list(top_reasons.items())[:10]:
            lines.append(f"- {reason}: {count}次")
        lines.append("")

    # ── Conclusions and Recommendations ──
    lines.append("## 💡 结论与改进建议")
    lines.append("")

    d1 = analysis.get("day1", {})
    ei_data = analysis.get("entry_intraday", {})
    gap_data = analysis.get("gap", {})
    chase_data = analysis.get("chase_vs_normal", {})

    d1_loss = d1.get("loss_pct", 0)
    d1_mean = d1.get("mean", 0)

    lines.append("### 问题诊断")
    lines.append("")

    if d1_loss > 50:
        lines.append(f"1. **第一天亏损问题严重：** {d1_loss:.1f}% 的选股在第一天就亏钱")
    elif d1_loss > 40:
        lines.append(f"1. **第一天亏损概率偏高：** {d1_loss:.1f}% 的选股在第一天亏钱")
    else:
        lines.append(f"1. **第一天亏损概率可控：** {d1_loss:.1f}% 的选股在第一天亏钱")

    gap_mean = gap_data.get("mean", 0)
    if gap_mean > 0.5:
        lines.append(f"2. **追高买入是主要原因：** 信号日到买入日平均高开 {gap_mean:+.2f}%，说明信号触发后市场已抢跑")
    elif gap_mean > 0:
        lines.append(f"2. **轻微追高效应：** 信号日到买入日平均缺口 {gap_mean:+.2f}%")
    else:
        lines.append(f"2. **无明显追高：** 信号日到买入日平均缺口 {gap_mean:+.2f}%")

    if chase_data:
        chase_loss = chase_data.get("chase_day1_loss_pct", 0)
        normal_loss = chase_data.get("normal_day1_loss_pct", 0)
        if chase_loss > normal_loss + 5:
            lines.append(f"3. **追高买入亏损更多：** 高开>2%时亏损率{chase_loss:.0f}%，正常时{normal_loss:.0f}%")

    mc_data = analysis.get("market_context", {})
    if mc_data:
        up_loss = mc_data.get("loss_when_market_up", 0)
        down_loss = mc_data.get("loss_when_market_down", 0)
        if down_loss > up_loss + 10:
            lines.append(f"4. **大盘下跌放大亏损：** 大盘跌时亏损率{down_loss:.0f}%，涨时{up_loss:.0f}%")

    lines.append("")
    lines.append("### 改进建议")
    lines.append("")

    suggestions = []
    if gap_mean > 0.5:
        suggestions.append("**1. 加入缺口过滤器：** 如果T+1开盘比T收盘高开>2%，放弃买入。追高是亏损的首要原因。")
    suggestions.append("**2. 增加市场环境过滤：** 在大盘趋势向下时降低仓位或放弃买入，避免逆势操作。")
    suggestions.append("**3. 提高最低分数阈值：** 考虑将最低分数从6提高到10，只做高确信度的交易。")
    suggestions.append("**4. 分时段入场：** 不要集中在开盘买入，考虑在盘中低点或尾盘入场。")
    suggestions.append("**5. 加入RSI二次确认：** 信号触发后等1天，确认RSI没有继续走弱才买入。")

    for sug in suggestions:
        lines.append(f"- {sug}")

    lines.append("")
    lines.append("---")
    lines.append("*本报告由 `scripts/analyze_first_day.py` 自动生成*")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    data_dir = str(PROJECT_ROOT / "data" / "a_shares")
    output_path = str(PROJECT_ROOT / "docs" / "first-day-analysis.md")

    print("=" * 60)
    print("CN Scanner First-Day Analysis")
    print("=" * 60)

    signals = simulate_scanner(data_dir, min_score=6)

    if not signals:
        print("No signals found! Check data directory.")
        return

    print(f"\n{'=' * 60}")
    print("Analyzing ...")
    analysis = analyze_signals(signals)

    report = generate_report(analysis, signals)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport written to: {output_path}")

    # Print summary to console
    d1 = analysis.get("day1", {})
    print(f"\n--- Quick Summary ---")
    print(f"Total signals: {analysis.get('total_signals', 0)}")
    print(f"Day 1 mean return: {d1.get('mean', 0):+.2f}%")
    print(f"Day 1 loss rate: {d1.get('loss_pct', 0):.1f}%")
    gap = analysis.get("gap", {})
    print(f"Avg gap (signal->buy): {gap.get('mean', 0):+.2f}%")
    print(f"Chase high (>2% gap): {gap.get('gap_up_gt2pct', 0):.1f}%")


if __name__ == "__main__":
    main()
