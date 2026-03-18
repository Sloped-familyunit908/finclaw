"""Backtest comparison: v1 vs v2 scoring strategy."""
import numpy as np
from src.cn_scanner import backtest_cn_strategy, format_backtest_output

np.random.seed(2024)
n = 200
data = {}

patterns = [
    ('600519.SS', 'oversold_bounce'),
    ('000858.SZ', 'steady_uptrend'),
    ('300750.SZ', 'volatile_range'),
    ('601318.SS', 'decline_then_recover'),
    ('002594.SZ', 'strong_momentum'),
    ('600036.SS', 'consolidation'),
    ('002230.SZ', 'sharp_pullback'),
    ('688981.SS', 'volume_breakout_pattern'),
    ('300059.SZ', 'ma_crossover'),
    ('601899.SS', 'mixed_signals'),
]

for ticker, pattern in patterns:
    vol = np.ones(n) * 10000.0
    if pattern == 'oversold_bounce':
        close = np.ones(n) * 100.0
        close[60:100] = np.linspace(100, 70, 40)
        close[100:140] = np.linspace(71, 95, 40)
        close[140:] = 95 + np.cumsum(np.random.randn(60) * 0.3)
        vol[95:105] = 25000
    elif pattern == 'steady_uptrend':
        close = np.linspace(80, 130, n) + np.random.randn(n) * 1.5
    elif pattern == 'volatile_range':
        close = 100 + 15 * np.sin(np.linspace(0, 8 * np.pi, n)) + np.random.randn(n) * 2
    elif pattern == 'decline_then_recover':
        close = np.concatenate([np.linspace(120, 80, 100), np.linspace(81, 110, 100)])
    elif pattern == 'strong_momentum':
        close = 80 + np.cumsum(np.abs(np.random.randn(n) * 0.3))
    elif pattern == 'consolidation':
        close = 100 + np.random.randn(n) * 2
    elif pattern == 'sharp_pullback':
        close = np.concatenate([np.linspace(90, 120, 160), np.linspace(119, 105, 40)])
        vol[160:] = np.linspace(10000, 5000, 40)
    elif pattern == 'volume_breakout_pattern':
        close = np.ones(n) * 100.0
        close[150:] = np.linspace(100, 115, 50)
        vol[150:] = 25000
    elif pattern == 'ma_crossover':
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        close = np.maximum(close, 50)
    else:  # mixed_signals
        close = 100 + np.cumsum(np.random.randn(n) * 0.8)
        close = np.maximum(close, 30)

    close = np.maximum(close, 1.0)
    data[ticker] = {'close': close, 'volume': vol}

print("=" * 90)
print("  V1 vs V2 Strategy Backtest Comparison")
print("=" * 90)

results_lines = []
for min_s in [4, 6]:
    for hold in [3, 5]:
        r_v1 = backtest_cn_strategy(hold_days=hold, min_score=min_s, lookback_days=60,
                                     data_override=data, strategy='v1')
        r_v2 = backtest_cn_strategy(hold_days=hold, min_score=min_s, lookback_days=60,
                                     data_override=data, strategy='v2')

        s1 = r_v1['summary']
        s2 = r_v2['summary']

        line = f"\n  Hold={hold}d | MinScore={min_s}"
        print(line)
        results_lines.append(line)

        hdr = "  {:>10} {:>10} {:>10} {:>10} {:>10} {:>10} {:>12}".format(
            "", "Batches", "AvgRet", "WinRate", "Best", "Worst", "Annual")
        print(hdr)
        results_lines.append(hdr)

        v1_line = "  {:>10} {:>10} {:>+9.2f}% {:>9.1f}% {:>+9.2f}% {:>+9.2f}% {:>+11.1f}%".format(
            "V1", s1["total_batches"], s1["avg_return"], s1["win_rate"],
            s1["best_batch"], s1["worst_batch"], s1["annualized"])
        print(v1_line)
        results_lines.append(v1_line)

        v2_line = "  {:>10} {:>10} {:>+9.2f}% {:>9.1f}% {:>+9.2f}% {:>+9.2f}% {:>+11.1f}%".format(
            "V2", s2["total_batches"], s2["avg_return"], s2["win_rate"],
            s2["best_batch"], s2["worst_batch"], s2["annualized"])
        print(v2_line)
        results_lines.append(v2_line)

print()
print("=" * 90)

# Save results
with open("_scratch/v1_vs_v2_backtest_comparison.txt", "w") as f:
    f.write("V1 vs V2 Strategy Backtest Comparison\n")
    f.write("=" * 90 + "\n")
    for line in results_lines:
        f.write(line + "\n")
    f.write("=" * 90 + "\n")

print("\nResults saved to _scratch/v1_vs_v2_backtest_comparison.txt")
