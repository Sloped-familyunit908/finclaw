#!/usr/bin/env python3
"""
find_best_params.py — Auto-optimisation for V1/V2/V3 A-share strategies.
=========================================================================
Runs backtests across a grid of (hold_days, min_score) for all three strategies,
then prints a ranked comparison and the best configuration.

Usage:
    python scripts/find_best_params.py
"""

from __future__ import annotations

import sys
import os
import json
import time
from itertools import product

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.cn_scanner import backtest_cn_strategy, CN_UNIVERSE


# ── Synthetic Data Generator ────────────────────────────────────────

def generate_synthetic_universe(n_bars: int = 200, n_stocks: int = 20, seed: int = 42) -> dict[str, dict]:
    """Generate synthetic OHLCV data for backtesting (no API calls)."""
    rng = np.random.RandomState(seed)
    data: dict[str, dict] = {}

    patterns = [
        "uptrend", "downtrend", "sideways", "volatile",
        "mean_revert", "momentum", "oversold_bounce", "accumulation",
    ]

    for i in range(min(n_stocks, len(CN_UNIVERSE))):
        ticker = CN_UNIVERSE[i][0]
        pattern = patterns[i % len(patterns)]

        if pattern == "uptrend":
            returns = rng.normal(0.003, 0.015, n_bars)
        elif pattern == "downtrend":
            returns = rng.normal(-0.002, 0.015, n_bars)
        elif pattern == "sideways":
            returns = rng.normal(0.0, 0.01, n_bars)
        elif pattern == "volatile":
            returns = rng.normal(0.001, 0.03, n_bars)
        elif pattern == "mean_revert":
            returns = rng.normal(0.0, 0.02, n_bars)
            # Add mean-reversion cycles
            for j in range(0, n_bars, 20):
                returns[j:j+10] = rng.normal(-0.015, 0.01, min(10, n_bars - j))
                if j + 10 < n_bars:
                    returns[j+10:j+20] = rng.normal(0.015, 0.01, min(10, n_bars - j - 10))
        elif pattern == "momentum":
            returns = rng.normal(0.005, 0.012, n_bars)
        elif pattern == "oversold_bounce":
            returns = rng.normal(-0.005, 0.02, n_bars)
            # Big sell-off then bounce
            returns[n_bars//2 - 5: n_bars//2] = rng.normal(-0.04, 0.01, 5)
            returns[n_bars//2: n_bars//2 + 5] = rng.normal(0.03, 0.01, 5)
        else:  # accumulation
            returns = rng.normal(0.0, 0.005, n_bars)
            # Volume increases
            returns[-20:] = rng.normal(0.002, 0.005, 20)

        close = 100.0 * np.exp(np.cumsum(returns))
        open_ = np.empty(n_bars)
        open_[0] = close[0]
        open_[1:] = close[:-1] * (1 + rng.randn(n_bars - 1) * 0.003)
        high = np.maximum(close, open_) * (1 + np.abs(rng.randn(n_bars)) * 0.005)
        low = np.minimum(close, open_) * (1 - np.abs(rng.randn(n_bars)) * 0.005)

        # Volume patterns
        base_vol = rng.randint(5000, 20000)
        volume = (base_vol + rng.randn(n_bars) * base_vol * 0.3).clip(100)

        data[ticker] = {
            "close": close,
            "volume": volume.astype(np.float64),
            "open": open_,
            "high": high,
            "low": low,
        }

    return data


# ── Main ─────────────────────────────────────────────────────────────

def main():
    # Fix encoding on Windows
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace('-', '') not in ('utf8', 'utf16'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("\n  ═══════════════════════════════════════════════════════════════")
    print("  FinClaw — A-Share Strategy Parameter Optimiser")
    print("  ═══════════════════════════════════════════════════════════════\n")

    hold_days_grid = [1, 3, 5, 10]
    min_score_grid = [6, 8, 10, 12, 14]
    strategies = ["v1", "v2", "v3"]

    # Generate synthetic data once
    print("  Generating synthetic OHLCV data (20 stocks × 200 bars)...")
    data = generate_synthetic_universe(n_bars=200, n_stocks=20, seed=42)
    print(f"  Generated {len(data)} stocks.\n")

    results: list[dict] = []
    total_combos = len(strategies) * len(hold_days_grid) * len(min_score_grid)
    done = 0

    for strategy in strategies:
        for hold_days, min_score in product(hold_days_grid, min_score_grid):
            done += 1
            bt = backtest_cn_strategy(
                hold_days=hold_days,
                min_score=min_score,
                lookback_days=60,
                data_override=data,
                strategy=strategy,
            )
            s = bt["summary"]
            results.append({
                "strategy": strategy,
                "hold_days": hold_days,
                "min_score": min_score,
                "total_batches": s["total_batches"],
                "avg_return": s["avg_return"],
                "win_rate": s["win_rate"],
                "annualized": s["annualized"],
                "best_batch": s["best_batch"],
                "worst_batch": s["worst_batch"],
            })
            if done % 10 == 0 or done == total_combos:
                print(f"  Progress: {done}/{total_combos} ({done * 100 // total_combos}%)")

    # ── Sort by annualised return ────────────────────────────────
    results.sort(key=lambda r: r["annualized"], reverse=True)

    # ── Print full table ─────────────────────────────────────────
    print("\n  ── Full Results (sorted by annualised return) ──\n")
    print(f"  {'#':>3} {'Strat':<6} {'Hold':>5} {'MinS':>5} {'Batches':>8} {'AvgRet':>8} {'WinRate':>8} {'Annual':>10} {'Best':>8} {'Worst':>8}")
    print("  " + "─" * 80)

    for i, r in enumerate(results, 1):
        ann_str = f"{r['annualized']:>+9.1f}%" if r["total_batches"] > 0 else "     N/A "
        print(
            f"  {i:>3} {r['strategy']:<6} {r['hold_days']:>5} {r['min_score']:>5} "
            f"{r['total_batches']:>8} {r['avg_return']:>+7.2f}% {r['win_rate']:>7.1f}% "
            f"{ann_str} {r['best_batch']:>+7.2f}% {r['worst_batch']:>+7.2f}%"
        )

    # ── Per-strategy best ────────────────────────────────────────
    print("\n  ── Best Configuration per Strategy ──\n")
    for strat in strategies:
        strat_results = [r for r in results if r["strategy"] == strat and r["total_batches"] > 0]
        if not strat_results:
            print(f"  {strat}: No valid results (all batches empty).")
            continue
        best = max(strat_results, key=lambda r: r["annualized"])
        print(
            f"  {strat.upper()}: hold={best['hold_days']}d, min_score={best['min_score']} → "
            f"avg_ret={best['avg_return']:+.2f}%, win_rate={best['win_rate']:.1f}%, "
            f"annual={best['annualized']:+.1f}%"
        )

    # ── Overall winner ───────────────────────────────────────────
    valid = [r for r in results if r["total_batches"] > 0]
    if valid:
        winner = max(valid, key=lambda r: r["annualized"])
        print(f"\n  🏆 OVERALL BEST: strategy={winner['strategy']}, "
              f"hold_days={winner['hold_days']}, min_score={winner['min_score']}")
        print(f"     Avg return per batch: {winner['avg_return']:+.2f}%")
        print(f"     Win rate: {winner['win_rate']:.1f}%")
        print(f"     Annualised: {winner['annualized']:+.1f}%")

    # ── Strategy comparison at same params ───────────────────────
    print("\n  ── V1 vs V2 vs V3 at hold=5d, min_score=8 ──\n")
    for strat in strategies:
        match = [r for r in results if r["strategy"] == strat and r["hold_days"] == 5 and r["min_score"] == 8]
        if match:
            r = match[0]
            print(
                f"  {strat.upper():>3}: batches={r['total_batches']}, avg_ret={r['avg_return']:+.2f}%, "
                f"win={r['win_rate']:.1f}%, annual={r['annualized']:+.1f}%"
            )
        else:
            print(f"  {strat.upper():>3}: N/A")

    # ── Save results ─────────────────────────────────────────────
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "param_optimization_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "grid": {
                "hold_days": hold_days_grid,
                "min_score": min_score_grid,
                "strategies": strategies,
            },
            "results": results,
            "best_overall": winner if valid else None,
        }, f, indent=2)
    print(f"\n  ✓ Results saved to {output_path}")
    print()

    return results


if __name__ == "__main__":
    main()
