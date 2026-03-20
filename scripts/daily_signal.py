"""
Daily Signal Generator - Multi-Strategy Ensemble
==================================================
Run ensemble strategy on latest data, generate daily buy/sell signals.

Usage:
    python scripts/daily_signal.py [--data-dir data/a_shares] [--output docs/signals]
    
Designed to run daily (e.g., cron at UTC 01:00 = Beijing 09:00 pre-market).
"""

import sys
import os
import glob
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategies.ensemble import StrategyEnsemble


def load_csv_data(csv_path: str) -> dict | None:
    """Load a single CSV file into arrays.
    
    CSV columns: date,code,open,high,low,close,volume,amount,turn
    """
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    code = ""
    
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            header = f.readline()
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 7:
                    continue
                vol_str = parts[6].strip()
                if not vol_str:
                    continue
                try:
                    vol = float(vol_str)
                except ValueError:
                    continue
                dates.append(parts[0])
                code = parts[1]
                opens.append(float(parts[2]))
                highs.append(float(parts[3]))
                lows.append(float(parts[4]))
                closes.append(float(parts[5]))
                volumes.append(vol)
    except Exception:
        return None
    
    if not dates:
        return None
    
    return {
        "dates": np.array(dates),
        "opens": np.array(opens, dtype=np.float64),
        "highs": np.array(highs, dtype=np.float64),
        "lows": np.array(lows, dtype=np.float64),
        "closes": np.array(closes, dtype=np.float64),
        "volumes": np.array(volumes, dtype=np.float64),
        "code": code,
        "name": code,
    }


def load_all_stocks(data_dir: str) -> dict:
    """Load all CSV files from data directory."""
    pattern = os.path.join(data_dir, "*.csv")
    csv_files = sorted(glob.glob(pattern))
    
    all_data = {}
    for csv_path in csv_files:
        data = load_csv_data(csv_path)
        if data is None or len(data["closes"]) < 60:
            continue
        code = data["code"]
        all_data[code] = data
    
    return all_data


def generate_signal_report(stock_data: dict, today: str = None) -> str:
    """Generate comprehensive daily signal report."""
    ensemble = StrategyEnsemble(min_votes=2, min_consensus=0.4)
    
    if today is None:
        today = datetime.now().strftime("%Y-%m-%d")
    
    # Scan all stocks
    signals = ensemble.scan_all(stock_data)
    
    strong_buys = [s for s in signals if s.signal == "strong_buy"]
    buys = [s for s in signals if s.signal == "buy"]
    watches = [s for s in signals if s.signal == "watch"]
    
    lines = [
        f"# 📊 {today} 多策略投票信号",
        "",
        f"> 5策略投票系统：cn_scanner, trend_discovery, golden_dip, imminent_breakout, limit_up_pullback",
        f"> 共扫描 **{len(stock_data)}** 只股票",
        "",
    ]
    
    # Strong buy
    lines.append("## 🔴 强烈买入 (≥3/5策略推荐)")
    if strong_buys:
        lines.append("")
        lines.append("| 代码 | 名称 | 价格 | 得票 | 共识度 | 推荐策略 | 平均分 |")
        lines.append("|------|------|------|------|--------|----------|--------|")
        for s in strong_buys[:10]:
            stars = "★" * s.votes + "☆" * (s.total_strategies - s.votes)
            lines.append(
                f"| {s.code} | {s.name} | ¥{s.price:.2f} | "
                f"{s.votes}/{s.total_strategies} {stars} | "
                f"{s.consensus:.0%} | {', '.join(s.strategies)} | "
                f"{s.avg_score:.1f} |"
            )
    else:
        lines.append("\n无强烈买入信号")
    
    lines.append("")
    
    # Buy
    lines.append("## 🟢 买入 (≥2/5策略推荐)")
    if buys:
        lines.append("")
        lines.append("| 代码 | 名称 | 价格 | 得票 | 推荐策略 | 平均分 |")
        lines.append("|------|------|------|------|----------|--------|")
        for s in buys[:20]:
            lines.append(
                f"| {s.code} | {s.name} | ¥{s.price:.2f} | "
                f"{s.votes}/{s.total_strategies} | "
                f"{', '.join(s.strategies)} | {s.avg_score:.1f} |"
            )
    else:
        lines.append("\n无买入信号")
    
    lines.append("")
    
    # Watch
    lines.append("## 👀 关注 (1/5策略推荐)")
    if watches:
        lines.append(f"\n共 {len(watches)} 只关注标的（仅显示前10）")
        lines.append("")
        for s in watches[:10]:
            lines.append(f"- {s.code} {s.name} ¥{s.price:.2f} ({', '.join(s.strategies)})")
    else:
        lines.append("\n无关注标的")
    
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by FinClaw Ensemble*")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily Signal Generator")
    parser.add_argument("--data-dir", type=str,
                        default=str(Path(__file__).resolve().parent.parent / "data" / "a_shares"),
                        help="Directory with CSV data files")
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).resolve().parent.parent / "docs" / "signals"),
                        help="Output directory for signal reports")
    parser.add_argument("--date", type=str, default=None,
                        help="Override date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    today = args.date or datetime.now().strftime("%Y-%m-%d")
    
    print(f"📊 Daily Signal Generator - {today}")
    print(f"  Data: {args.data_dir}")
    
    # Load data
    print("  Loading stock data...")
    stock_data = load_all_stocks(args.data_dir)
    print(f"  Loaded {len(stock_data)} stocks")
    
    if not stock_data:
        print("❌ No data found!")
        return
    
    # Generate signal
    print("  Running ensemble analysis...")
    report = generate_signal_report(stock_data, today)
    
    # Save to file
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{today}.md"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"  ✅ Signal saved to {output_path}")
    print()
    
    # Also print to stdout
    print(report)


if __name__ == "__main__":
    main()
