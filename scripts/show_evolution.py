import json, os
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_PROJECT_DIR, 'evolution_results', 'latest.json')) as f:
    d = json.load(f)
print(f"Generation: {d['generation']}")
for i, r in enumerate(d['results'][:5]):
    dna = r['dna']
    print(f"#{i+1} return={r['annual_return']:.0f}% dd={r['max_drawdown']:.0f}% wr={r['win_rate']:.0f}% sharpe={r['sharpe']:.1f} hold={dna['hold_days']}d tp={dna['take_profit_pct']:.1f}% sl={dna['stop_loss_pct']:.1f}% fitness={r['fitness']:.0f}")
print(f"\nBest DNA weights:")
best = d['results'][0]['dna']
print(f"  momentum={best['w_momentum']:.1%} reversion={best['w_mean_reversion']:.1%} volume={best['w_volume']:.1%} trend={best['w_trend']:.1%} pattern={best['w_pattern']:.1%}")
print(f"  RSI buy={best['rsi_buy_threshold']:.0f} sell={best['rsi_sell_threshold']:.0f}")
print(f"  R2 min={best['r2_min']:.2f} slope min={best['slope_min']:.2f}")
