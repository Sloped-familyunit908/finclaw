#!/usr/bin/env python3
"""
Long-Term Backtest Comparison Script
=====================================
Compares different strategy/parameter combos over 1y and 2y periods.

Usage:
    python scripts/long_term_backtest.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cn_scanner import backtest_cn_strategy


def run_backtest(strategy: str, hold_days: int, min_score: int, period: str) -> dict:
    """Run a single backtest configuration and return summary."""
    try:
        result = backtest_cn_strategy(
            hold_days=hold_days,
            min_score=min_score,
            period=period,
            lookback_days=400,  # use max lookback to cover entire period
            strategy=strategy,
        )
        return result["summary"]
    except Exception as e:
        print(f"  ERROR running {strategy} hold={hold_days}d score>={min_score} period={period}: {e}")
        return {
            "total_batches": 0, "avg_return": 0.0, "win_rate": 0.0,
            "best_batch": 0.0, "worst_batch": 0.0, "annualized": 0.0,
            "hold_days": hold_days, "min_score": min_score,
        }


def main():
    configs = [
        # (label, strategy, hold_days, min_score, period)
        ("V2 hold=5d score>=12 1y",  "v2", 5, 12, "1y"),
        ("V2 hold=5d score>=12 2y",  "v2", 5, 12, "2y"),
        ("V2 hold=5d score>=8  1y",  "v2", 5,  8, "1y"),
        ("V3 hold=5d score>=16 1y",  "v3", 5, 16, "1y"),
    ]

    results = []
    for label, strategy, hold_days, min_score, period in configs:
        print(f"\n  Running: {label} ...")
        summary = run_backtest(strategy, hold_days, min_score, period)
        results.append((label, summary))

    # ── Print comparison table ───────────────────────────────────
    print("\n")
    print("  " + "=" * 100)
    print(f"  {'Config':<30} {'Batches':>8} {'Avg Ret':>10} {'Win Rate':>10} "
          f"{'Best':>10} {'Worst':>10} {'Ann. Est':>10}")
    print("  " + "-" * 100)

    for label, s in results:
        print(f"  {label:<30} {s['total_batches']:>8} {s['avg_return']:>+9.2f}% "
              f"{s['win_rate']:>9.1f}% {s['best_batch']:>+9.2f}% "
              f"{s['worst_batch']:>+9.2f}% {s['annualized']:>+9.1f}%")

    print("  " + "=" * 100)
    print()


if __name__ == "__main__":
    main()
