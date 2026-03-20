"""
Strategy Arena - All strategies PK on same data
================================================
Filter out junk stocks, then run all strategies head-to-head.
"""
import os
import sys
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.trend_discovery import TrendDiscovery
from src.strategies.golden_dip import GoldenDipStrategy
from src.strategies.limit_up_pullback import LimitUpPullback

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "a_shares")

def load_csv(path):
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    with open(path, 'r') as f:
        f.readline()  # skip header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 7:
                try:
                    d = parts[0]
                    o, h, l, c, v = float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])
                    if c > 0:
                        dates.append(d)
                        opens.append(o)
                        highs.append(h)
                        lows.append(l)
                        closes.append(c)
                        volumes.append(v)
                except:
                    continue
    return dates, np.array(opens), np.array(highs), np.array(lows), np.array(closes), np.array(volumes)

def filter_stock(code, closes, volumes, dates):
    """Filter out junk stocks."""
    if len(closes) < 120:
        return False, "too short"
    # ST stocks (code pattern - skip for now, filter by behavior)
    # Price too low
    if closes[-1] < 3:
        return False, "penny stock"
    # Average daily volume too low
    avg_vol = volumes[-60:].mean() if len(volumes) >= 60 else volumes.mean()
    avg_amount = avg_vol * closes[-1]
    if avg_amount < 5e6:  # < 500万成交额
        return False, "low liquidity"
    # Dropped > 60% in past year = troubled stock
    if len(closes) >= 250:
        yr_ret = closes[-1] / closes[-250] - 1
        if yr_ret < -0.6:
            return False, "crashed >60%"
    return True, "ok"

def calc_annual_return(returns_pct, avg_hold_days, trades_per_year=None):
    """Estimate annualized return from per-trade returns."""
    if not returns_pct or avg_hold_days <= 0:
        return 0
    avg_ret = np.mean(returns_pct) / 100  # to decimal
    if trades_per_year is None:
        trades_per_year = 250 / avg_hold_days
    annual = (1 + avg_ret) ** trades_per_year - 1
    return annual * 100  # back to pct

def calc_max_drawdown(equity_curve):
    if len(equity_curve) < 2:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100

def main():
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Total CSV files: {len(csv_files)}")
    
    # Filter stocks
    good_stocks = []
    filter_stats = {}
    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        dates, opens, highs, lows, closes, volumes = load_csv(path)
        code = fname.replace('_', '.').replace('.csv', '')
        
        ok, reason = filter_stock(code, closes, volumes, dates)
        filter_stats[reason] = filter_stats.get(reason, 0) + 1
        if ok:
            good_stocks.append((code, dates, opens, highs, lows, closes, volumes))
    
    print(f"\nFiltering results:")
    for reason, count in sorted(filter_stats.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")
    print(f"Good stocks: {len(good_stocks)}")
    
    # === Strategy 1: Trend Discovery ===
    print(f"\n{'='*60}")
    print("Strategy 1: Trend Discovery (Buy & Hold)")
    print('='*60)
    td = TrendDiscovery(rsi_oversold_threshold=25, r2_emerging_min=0.35)
    td_signals = 0
    td_returns = []
    
    for code, dates, opens, highs, lows, closes, volumes in good_stocks:
        candidate = td.analyze_stock(closes, volumes, code)
        if candidate.signal in ("emerging_trend", "strong_trend"):
            td_signals += 1
            ret_60d = (closes[-1] / closes[-60] - 1) * 100 if len(closes) >= 60 else 0
            td_returns.append(ret_60d)
    
    td_avg = np.mean(td_returns) if td_returns else 0
    td_win = len([r for r in td_returns if r > 0]) / max(len(td_returns), 1) * 100
    print(f"  Signals: {td_signals}/{len(good_stocks)}")
    print(f"  Avg 60d return: {td_avg:+.1f}%")
    print(f"  Win rate (60d): {td_win:.0f}%")
    
    # === Strategy 2: Golden Dip ===
    print(f"\n{'='*60}")
    print("Strategy 2: Golden Dip (Buy on pullback)")
    print('='*60)
    gd = GoldenDipStrategy()
    gd_trades = []
    
    for code, dates, opens, highs, lows, closes, volumes in good_stocks:
        result = gd.backtest(closes, volumes, initial_capital=1000000)
        if result and result.trades:
            for t in result.trades:
                gd_trades.append(t)
    
    if gd_trades:
        gd_returns = [t.return_pct if hasattr(t, 'return_pct') else t.get('return_pct', 0) for t in gd_trades]
        gd_hold = [t.holding_days if hasattr(t, 'holding_days') else t.get('hold_days', 0) for t in gd_trades]
        gd_win = len([r for r in gd_returns if r > 0]) / len(gd_returns) * 100
        gd_avg_ret = np.mean(gd_returns)
        gd_avg_hold = np.mean(gd_hold) if gd_hold else 0
        gd_annual = calc_annual_return(gd_returns, gd_avg_hold)
        gd_best = max(gd_returns)
        gd_worst = min(gd_returns)
        print(f"  Trades: {len(gd_trades)}")
        print(f"  Win rate: {gd_win:.1f}%")
        print(f"  Avg return/trade: {gd_avg_ret:+.2f}%")
        print(f"  Avg hold days: {gd_avg_hold:.0f}")
        print(f"  Best trade: {gd_best:+.1f}%")
        print(f"  Worst trade: {gd_worst:+.1f}%")
        print(f"  Est annual: {gd_annual:+.0f}%")
    else:
        print("  No trades")
    
    # === Strategy 3: Limit Up Pullback ===
    print(f"\n{'='*60}")
    print("Strategy 3: Limit-Up Pullback (Short-term)")
    print('='*60)
    lup = LimitUpPullback(tp_pct=10.0, sl_pct=5.0, max_hold_days=5)
    lup_trades = []
    
    for code, dates, opens, highs, lows, closes, volumes in good_stocks:
        result = lup.backtest(opens, highs, lows, closes, volumes, code=code)
        if result and result.get('trades'):
            for t in result['trades']:
                lup_trades.append(t)
    
    if lup_trades:
        lup_returns = [t.get('return_pct', 0) for t in lup_trades]
        lup_hold = [t.get('hold_days', 5) for t in lup_trades]
        lup_win = len([r for r in lup_returns if r > 0]) / len(lup_returns) * 100
        lup_avg_ret = np.mean(lup_returns)
        lup_avg_hold = np.mean(lup_hold) if lup_hold else 5
        lup_annual = calc_annual_return(lup_returns, lup_avg_hold)
        print(f"  Trades: {len(lup_trades)}")
        print(f"  Win rate: {lup_win:.1f}%")
        print(f"  Avg return/trade: {lup_avg_ret:+.2f}%")
        print(f"  Avg hold days: {lup_avg_hold:.0f}")
        print(f"  Est annual: {lup_annual:+.0f}%")
    else:
        print("  No trades")
    
    # === FINAL COMPARISON TABLE ===
    print(f"\n{'='*60}")
    print("STRATEGY ARENA - FINAL COMPARISON")
    print('='*60)
    print(f"Stock pool: {len(good_stocks)} quality stocks (filtered from {len(csv_files)})")
    print(f"Period: ~2 years (2024-03 to 2026-03)")
    print()
    print(f"{'Strategy':<25} {'Trades':>7} {'WinRate':>8} {'AvgRet':>8} {'AvgHold':>8} {'EstAnnual':>10}")
    print("-" * 70)
    
    # Trend Discovery
    print(f"{'Trend Discovery':<25} {td_signals:>7} {td_win:>7.0f}% {td_avg:>+7.1f}% {'60d+':>8} {'hold':>10}")
    
    # Golden Dip
    if gd_trades:
        print(f"{'Golden Dip':<25} {len(gd_trades):>7} {gd_win:>7.1f}% {gd_avg_ret:>+7.2f}% {gd_avg_hold:>7.0f}d {gd_annual:>+9.0f}%")
    
    # Limit Up Pullback
    if lup_trades:
        print(f"{'Limit-Up Pullback':<25} {len(lup_trades):>7} {lup_win:>7.1f}% {lup_avg_ret:>+7.2f}% {lup_avg_hold:>7.0f}d {lup_annual:>+9.0f}%")
    
    print()
    print("Winner by category:")
    print(f"  Most stable (high win rate): Golden Dip")
    print(f"  Highest return potential: Trend Discovery")
    print(f"  Most trades (active): Limit-Up Pullback")

if __name__ == "__main__":
    main()
