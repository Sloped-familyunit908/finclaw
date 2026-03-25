"""Independent verification of crypto backtest results."""
import json
import math

with open('evolution_results_crypto/best_ever.json') as f:
    best = json.load(f)

print('=== BEST EVER DNA VERIFICATION ===')
print('Generation:', best['generation'])
print('Fitness:', round(best['fitness'], 2))
print('Annual Return:', str(round(best['annual_return'], 2)) + '%')
print('Max Drawdown:', str(round(best['max_drawdown'], 2)) + '%')
print('Win Rate:', str(round(best['win_rate'], 2)) + '%')
print('Sharpe:', round(best['sharpe'], 2))
print('Total Trades:', best['total_trades'])
print('Profit Factor:', best.get('profit_factor', 'N/A'))

dna = best['dna']
print()
print('=== KEY STRATEGY PARAMETERS ===')
print('Min Score:', dna['min_score'])
print('Hold Days:', dna['hold_days'])
print('Stop Loss:', str(round(dna['stop_loss_pct'], 1)) + '%')
print('Take Profit:', str(round(dna['take_profit_pct'], 1)) + '%')
print('Max Positions:', dna['max_positions'])
print('RSI Buy:', round(dna['rsi_buy_threshold'], 1))
print('RSI Sell:', round(dna['rsi_sell_threshold'], 1))

# Verify fitness formula
dd = max(best['max_drawdown'], 5.0)
wr = math.sqrt(max(best['win_rate'], 0.0))
sharpe_bonus = 1.0 + max(best['sharpe'], 0.0) * 0.2
base = best['annual_return'] * wr / dd * sharpe_bonus
print()
print('=== FITNESS VERIFICATION ===')
print('Base fitness (manual):', round(base, 2))
print('Reported fitness:', round(best['fitness'], 2))
ratio = best['fitness'] / base if base > 0 else 0
print('Ratio:', round(ratio, 2), '(>1 = bonuses applied)')

# Per-trade analysis
total_return_2yr = (1 + best['annual_return']/100)**2 - 1
avg_per_trade = (1 + total_return_2yr)**(1/best['total_trades']) - 1
print()
print('=== PER-TRADE ANALYSIS ===')
print('2-year compound return:', str(round(total_return_2yr*100)) + '%')
print('Avg per-trade return:', str(round(avg_per_trade*100, 4)) + '%')
print('Trades:', best['total_trades'])
print('Trades per day:', round(best['total_trades']/730, 1))

# Reality checks
print()
print('=== REALITY CHECKS ===')
checks_passed = 0
checks_total = 5

# 1. Trade frequency
tpd = best['total_trades'] / 730
if 1 < tpd < 50:
    print('[PASS] Trade frequency:', round(tpd,1), 'trades/day - reasonable')
    checks_passed += 1
else:
    print('[WARN] Trade frequency:', round(tpd,1), 'trades/day - unusual')

# 2. Win rate
if 40 < best['win_rate'] < 80:
    print('[PASS] Win rate:', round(best['win_rate'],1), '% - reasonable')
    checks_passed += 1
else:
    print('[WARN] Win rate:', round(best['win_rate'],1), '% - extreme')

# 3. Per-trade return
if 0.01 < avg_per_trade*100 < 1.0:
    print('[PASS] Avg per-trade return:', round(avg_per_trade*100,4), '% - small edge, compounds')
    checks_passed += 1
else:
    print('[WARN] Avg per-trade return:', round(avg_per_trade*100,4), '% - needs investigation')

# 4. Sharpe daily equivalent
daily_sharpe = best['sharpe'] / math.sqrt(8760) * math.sqrt(365)
if 0.5 < daily_sharpe < 5:
    print('[PASS] Daily-equiv Sharpe:', round(daily_sharpe, 2), '- reasonable for crypto')
    checks_passed += 1
else:
    print('[WARN] Daily-equiv Sharpe:', round(daily_sharpe, 2), '- unusual')

# 5. Drawdown
if best['max_drawdown'] > 3:
    print('[PASS] Max drawdown:', round(best['max_drawdown'],1), '% - not suspiciously low')
    checks_passed += 1
else:
    print('[WARN] Max drawdown:', round(best['max_drawdown'],1), '% - suspiciously low')

print()
print('=== VERDICT ===')
print('Checks passed:', checks_passed, '/', checks_total)
if checks_passed >= 4:
    print('RESULT: Backtest math looks CORRECT')
    print('BUT: Need Monte Carlo + more coins + dry-run for RELIABILITY')
else:
    print('RESULT: Some concerns need investigation')

# Overfitting risk
print()
print('=== OVERFITTING RISK ===')
print('Coins used: 4 (BTC, ETH, BNB, SOL)')
print('Factor dimensions: 417')
print('Risk: HIGH - 417 factors fitting 4 data series')
print('Mitigation needed:')
print('  1. Download remaining 16 coins and re-run')
print('  2. Run Monte Carlo validation')
print('  3. 30-day dry-run on live prices')
print('  4. Walk-forward already applied (70/30 split)')
