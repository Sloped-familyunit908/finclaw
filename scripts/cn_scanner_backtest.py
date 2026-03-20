"""
CN Scanner Strategy - Full Backtest with Local Data
====================================================
Verify the 896% annual return claim with real data.
Use T+1 open price, include all costs.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "a_shares")

def load_csv(path):
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    with open(path, 'r') as f:
        f.readline()
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

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - 100 / (1 + rs)

def score_stock(closes, volumes, opens, highs, lows):
    """Simplified cn_scanner scoring - key signals only."""
    if len(closes) < 60:
        return 0
    
    score = 0
    c = closes
    v = volumes
    
    # 1. Volume breakout
    vol_ma20 = v[-20:].mean()
    vol_ma5 = v[-5:].mean()
    if vol_ma5 > vol_ma20 * 1.5:
        score += 2
    
    # 2. MA alignment (5>10>20)
    ma5 = c[-5:].mean()
    ma10 = c[-10:].mean()
    ma20 = c[-20:].mean()
    if ma5 > ma10 > ma20:
        score += 2
    
    # 3. RSI not overbought
    rsi = calculate_rsi(c)
    if 30 < rsi < 70:
        score += 1
    if rsi < 35:
        score += 2  # oversold bonus
    
    # 4. Price above MA20
    if c[-1] > ma20:
        score += 1
    
    # 5. MACD positive
    ema12 = c[-12:].mean()  # simplified
    ema26 = c[-26:].mean() if len(c) >= 26 else c.mean()
    if ema12 > ema26:
        score += 1
    
    # 6. Momentum (5d return positive)
    ret5d = (c[-1] / c[-6] - 1) * 100 if len(c) >= 6 else 0
    if 0 < ret5d < 15:  # positive but not too much (avoid chasing)
        score += 1
    
    # 7. Bottom reversal (recent low + bounce)
    low20 = lows[-20:].min()
    if c[-1] > low20 * 1.05 and c[-1] < low20 * 1.15:
        score += 2  # bounced 5-15% from recent low
    
    # 8. Increasing volume trend
    if len(v) >= 10:
        vol_recent = v[-5:].mean()
        vol_prev = v[-10:-5].mean()
        if vol_recent > vol_prev * 1.2:
            score += 1
    
    return score

def run_backtest():
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Loading {len(csv_files)} stocks...")
    
    # Load all data
    stocks = {}
    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        dates, opens, highs, lows, closes, volumes = load_csv(path)
        code = fname.replace('_', '.').replace('.csv', '')
        
        # Filter: must have enough data, not penny, decent volume
        if len(closes) < 120 or closes[-1] < 3:
            continue
        avg_amount = volumes[-60:].mean() * closes[-1]
        if avg_amount < 5e6:
            continue
        
        stocks[code] = {
            'dates': dates, 'opens': opens, 'highs': highs,
            'lows': lows, 'closes': closes, 'volumes': volumes
        }
    
    print(f"Quality stocks: {len(stocks)}")
    
    # Get all unique dates
    all_dates = set()
    for s in stocks.values():
        all_dates.update(s['dates'])
    all_dates = sorted(all_dates)
    
    # Only use dates from 2025-01 onwards for backtest (2024 data for lookback)
    trade_dates = [d for d in all_dates if d >= '2025-01-01']
    print(f"Trading period: {trade_dates[0]} to {trade_dates[-1]} ({len(trade_dates)} days)")
    
    # Simulate cn_scanner batch strategy
    # Every 3 days: score all stocks, pick top 2, buy at T+1 open, hold 3 days, sell at T+3 close
    capital = 1000000  # 100万
    equity_curve = [capital]
    trades = []
    holdings = []
    
    HOLD_DAYS = 3
    TOP_N = 2
    COMMISSION = 0.001  # 0.1% per trade (buy+sell = 0.2% round trip)
    SL_PCT = 0.02  # 2% stop loss
    TP_PCT = 0.20  # 20% take profit
    
    i = 0
    while i < len(trade_dates) - HOLD_DAYS - 1:
        today = trade_dates[i]
        
        # Score all stocks on this date
        scored = []
        for code, data in stocks.items():
            if today not in data['dates']:
                continue
            idx = data['dates'].index(today)
            if idx < 60:
                continue
            
            closes_to_now = data['closes'][:idx+1]
            volumes_to_now = data['volumes'][:idx+1]
            opens_to_now = data['opens'][:idx+1]
            highs_to_now = data['highs'][:idx+1]
            lows_to_now = data['lows'][:idx+1]
            
            s = score_stock(closes_to_now, volumes_to_now, opens_to_now, highs_to_now, lows_to_now)
            if s >= 6:
                scored.append((code, s, idx))
        
        # Pick top N
        scored.sort(key=lambda x: -x[1])
        picks = scored[:TOP_N]
        
        if not picks:
            i += HOLD_DAYS
            equity_curve.append(capital)
            continue
        
        # Buy at T+1 open
        buy_date_idx = i + 1
        if buy_date_idx >= len(trade_dates):
            break
        buy_date = trade_dates[buy_date_idx]
        
        # Sell at T+1+HOLD_DAYS close (or SL/TP hit)
        position_capital = capital / len(picks)
        period_return = 0
        
        for code, score, data_idx in picks:
            data = stocks[code]
            
            # Find buy_date in this stock's data
            if buy_date not in data['dates']:
                continue
            buy_idx = data['dates'].index(buy_date)
            buy_price = data['opens'][buy_idx]  # T+1 OPEN price!
            
            if buy_price <= 0:
                continue
            
            # Hold for HOLD_DAYS, check SL/TP each day
            sell_price = buy_price
            sell_reason = "hold"
            actual_hold = HOLD_DAYS
            
            for d in range(HOLD_DAYS):
                check_idx = buy_idx + d
                if check_idx >= len(data['closes']):
                    break
                
                day_low = data['lows'][check_idx]
                day_high = data['highs'][check_idx]
                day_close = data['closes'][check_idx]
                
                # Stop loss check
                if day_low <= buy_price * (1 - SL_PCT):
                    sell_price = buy_price * (1 - SL_PCT)
                    sell_reason = "stop_loss"
                    actual_hold = d + 1
                    break
                
                # Take profit check
                if day_high >= buy_price * (1 + TP_PCT):
                    sell_price = buy_price * (1 + TP_PCT)
                    sell_reason = "take_profit"
                    actual_hold = d + 1
                    break
                
                sell_price = day_close
            else:
                sell_reason = "time_exit"
            
            # Calculate return
            ret = (sell_price / buy_price - 1)
            ret_after_cost = ret - COMMISSION * 2  # buy + sell commission
            
            trade_pnl = position_capital * ret_after_cost
            period_return += trade_pnl
            
            trades.append({
                'date': buy_date, 'code': code, 'score': score,
                'buy': buy_price, 'sell': sell_price,
                'ret': ret_after_cost * 100, 'reason': sell_reason,
                'hold_days': actual_hold
            })
        
        capital += period_return
        equity_curve.append(capital)
        i += HOLD_DAYS
    
    # Results
    print(f"\n{'='*60}")
    print(f"CN SCANNER BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Period: {trade_dates[0]} to {trade_dates[-1]}")
    print(f"Starting capital: 1,000,000")
    print(f"Final capital: {capital:,.0f}")
    
    total_ret = (capital / 1000000 - 1) * 100
    trading_days = len(trade_dates)
    annual_ret = ((capital / 1000000) ** (250/trading_days) - 1) * 100 if trading_days > 0 else 0
    
    print(f"Total return: {total_ret:+.1f}%")
    print(f"Annualized return: {annual_ret:+.0f}%")
    
    # Trade stats
    if trades:
        rets = [t['ret'] for t in trades]
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r <= 0]
        
        print(f"\nTrades: {len(trades)}")
        print(f"Win rate: {len(wins)/len(trades)*100:.1f}%")
        print(f"Avg return/trade: {np.mean(rets):+.2f}%")
        print(f"Avg win: {np.mean(wins):+.2f}%" if wins else "No wins")
        print(f"Avg loss: {np.mean(losses):+.2f}%" if losses else "No losses")
        print(f"Best trade: {max(rets):+.2f}%")
        print(f"Worst trade: {min(rets):+.2f}%")
        print(f"Profit factor: {sum(wins)/abs(sum(losses)):.2f}" if losses and sum(losses) != 0 else "N/A")
        
        # Exit reasons
        reasons = {}
        for t in trades:
            r = t['reason']
            reasons[r] = reasons.get(r, 0) + 1
        print(f"\nExit reasons:")
        for r, c in sorted(reasons.items()):
            print(f"  {r}: {c} ({c/len(trades)*100:.0f}%)")
        
        # Max drawdown
        eq = np.array(equity_curve)
        peak = np.maximum.accumulate(eq)
        dd = (peak - eq) / peak * 100
        max_dd = dd.max()
        print(f"\nMax drawdown: {max_dd:.1f}%")
        print(f"Sharpe (approx): {annual_ret / max(max_dd, 1):.2f}")
        print(f"Calmar: {annual_ret / max(max_dd, 1):.2f}")
        
        # Day 1 analysis
        d1_rets = [t['ret'] for t in trades if t['hold_days'] <= 1]
        if d1_rets:
            d1_loss_rate = len([r for r in d1_rets if r < 0]) / len(d1_rets) * 100
            print(f"\nDay 1 exits: {len(d1_rets)}")
            print(f"Day 1 loss rate: {d1_loss_rate:.0f}%")

if __name__ == "__main__":
    run_backtest()
