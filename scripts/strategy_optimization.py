"""
A股选股策略多维度优化分析
- 持仓时间对比: 1/3/5/10/20 天
- 选股门槛对比: 5/7/8/10/12 分
- V1 vs V2 全面对比
- 寻找最优参数组合
"""
import sys, warnings, json, time
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

from src.cn_scanner import backtest_cn_strategy

HOLD_DAYS = [1, 3, 5, 10, 20]
MIN_SCORES_V1 = [4, 5, 6, 7]
MIN_SCORES_V2 = [5, 7, 8, 10, 12]

results = []

# V2 多维度测试
print("Running V2 multi-dimensional backtest...")
print(f"Hold days: {HOLD_DAYS}")
print(f"Min scores: {MIN_SCORES_V2}")
print()

for hold in HOLD_DAYS:
    for ms in MIN_SCORES_V2:
        try:
            r = backtest_cn_strategy(
                hold_days=hold, min_score=ms, period='6mo',
                lookback_days=60, top=50, strategy='v2'
            )
            s = r['summary']
            results.append({
                'strategy': 'v2', 'hold': hold, 'min_score': ms,
                'batches': s['total_batches'],
                'avg_ret': s['avg_return'],
                'win_rate': s['win_rate'],
                'best': s['best_batch'],
                'worst': s['worst_batch'],
                'annual': s['annualized'],
            })
            print(f"  V2 hold={hold}d score>={ms}: batches={s['total_batches']} avg={s['avg_return']:+.2f}% win={s['win_rate']:.0f}% annual={s['annualized']:+.1f}%")
        except Exception as e:
            print(f"  V2 hold={hold}d score>={ms}: ERROR {e}")

# V1 多维度测试
print()
print("Running V1 multi-dimensional backtest...")
for hold in HOLD_DAYS:
    for ms in MIN_SCORES_V1:
        try:
            r = backtest_cn_strategy(
                hold_days=hold, min_score=ms, period='6mo',
                lookback_days=60, top=50, strategy='v1'
            )
            s = r['summary']
            results.append({
                'strategy': 'v1', 'hold': hold, 'min_score': ms,
                'batches': s['total_batches'],
                'avg_ret': s['avg_return'],
                'win_rate': s['win_rate'],
                'best': s['best_batch'],
                'worst': s['worst_batch'],
                'annual': s['annualized'],
            })
            print(f"  V1 hold={hold}d score>={ms}: batches={s['total_batches']} avg={s['avg_return']:+.2f}% win={s['win_rate']:.0f}% annual={s['annualized']:+.1f}%")
        except Exception as e:
            print(f"  V1 hold={hold}d score>={ms}: ERROR {e}")

# 输出排行榜
print()
print("=" * 100)
print("RANKING: Top 15 parameter combinations by annualized return")
print("=" * 100)
valid = [r for r in results if r['batches'] > 0 and r['annual'] != 0]
valid.sort(key=lambda x: -x['annual'])

print(f"{'Rank':<5}{'Strat':<6}{'Hold':<6}{'Score':<7}{'Batches':<9}{'AvgRet':>8}{'WinRate':>9}{'Annual':>9}{'Best':>8}{'Worst':>8}")
print("-" * 75)
for i, r in enumerate(valid[:15]):
    print(f"{i+1:<5}{r['strategy']:<6}{r['hold']:<6}{r['min_score']:<7}{r['batches']:<9}{r['avg_ret']:>+7.2f}%{r['win_rate']:>8.0f}%{r['annual']:>+8.1f}%{r['best']:>+7.2f}%{r['worst']:>+7.2f}%")

print()
print("RANKING: Top 10 by Win Rate (min 3 batches)")
print("=" * 100)
valid_wr = [r for r in valid if r['batches'] >= 3]
valid_wr.sort(key=lambda x: (-x['win_rate'], -x['annual']))
print(f"{'Rank':<5}{'Strat':<6}{'Hold':<6}{'Score':<7}{'Batches':<9}{'AvgRet':>8}{'WinRate':>9}{'Annual':>9}")
print("-" * 60)
for i, r in enumerate(valid_wr[:10]):
    print(f"{i+1:<5}{r['strategy']:<6}{r['hold']:<6}{r['min_score']:<7}{r['batches']:<9}{r['avg_ret']:>+7.2f}%{r['win_rate']:>8.0f}%{r['annual']:>+8.1f}%")

# Save results
with open('strategy_optimization_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print()
print(f"Results saved to strategy_optimization_results.json ({len(results)} combinations)")
