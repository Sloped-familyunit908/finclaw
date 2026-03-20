"""
Backtest the Imminent Breakout Scanner
========================================
For every historical day, run the scanner, then check:
- Did the stock actually go up in the next 2-3-5 days?
- What was the average return?
- What was the win rate?
- How to improve signal accuracy?
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
                    d, o, h, l, c, v = parts[0], float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])
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

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
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

def breakout_score_at(closes, highs, lows, opens, volumes, idx):
    """Calculate breakout score using data up to idx (no future data)."""
    if idx < 60:
        return 0
    c = closes[:idx+1]
    h = highs[:idx+1]
    l = lows[:idx+1]
    o = opens[:idx+1]
    v = volumes[:idx+1]
    n = len(c)
    
    score = 0
    
    # BB squeeze
    ma20 = c[-20:].mean()
    std20 = c[-20:].std()
    if ma20 > 0 and std20 > 0:
        bb_width = std20 / ma20 * 100
        bb_hist = []
        for i in range(20, min(n, 100)):
            seg = c[n-i-20:n-i]
            if len(seg) >= 20 and seg.mean() > 0:
                w = seg.std() / seg.mean() * 100
                if not np.isnan(w):
                    bb_hist.append(w)
        if bb_hist:
            pct = sum(1 for w in bb_hist if bb_width < w) / len(bb_hist) * 100
            if pct > 80:
                score += 20
            elif pct > 60:
                score += 10
    
    # Volume pattern
    if n >= 20:
        vol5 = v[-5:].mean()
        vol10 = v[-10:-5].mean()
        vol20 = v[-20:].mean()
        if vol10 > 0 and vol20 > 0:
            if vol10 < vol20 * 0.7 and vol5 > vol10 * 1.1:
                score += 15
            elif vol5 < vol20 * 0.6:
                score += 10
    
    # MA support
    ma5 = c[-5:].mean()
    ma10 = c[-10:].mean()
    if c[-1] > 0:
        for mv in [ma5, ma10, ma20]:
            if mv > 0:
                dist = abs(c[-1] - mv) / mv * 100
                if dist < 2 and c[-1] >= mv:
                    score += 10
                    break
    
    # MA alignment
    if ma5 > ma10 > ma20:
        score += 10
    elif ma5 > ma10:
        score += 5
    
    # RSI
    rsi = calc_rsi(c)
    if 40 <= rsi <= 55:
        score += 15
    elif 55 < rsi <= 65:
        score += 8
    elif 30 <= rsi < 40:
        score += 10
    
    # Consolidation
    if n >= 20:
        range5 = (h[-5:].max() - l[-5:].min()) / c[-5].mean() * 100
        range20 = (h[-20:].max() - l[-20:].min()) / c[-20].mean() * 100
        if range20 > 0 and range5 < range20 * 0.3 and c[-5] > c[-20]:
            score += 15
    
    # Recent trend
    ret20 = (c[-1] / c[-20] - 1) * 100
    if 5 < ret20 < 30:
        score += 5
    
    return score

def main():
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Loading {len(csv_files)} stocks...")
    
    # Load all data
    stocks = {}
    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        dates, opens, highs, lows, closes, volumes = load_csv(path)
        code = fname.replace('_', '.').replace('.csv', '')
        if len(closes) < 120 or closes[-1] < 3:
            continue
        if volumes[-20:].mean() * closes[-1] < 1e7:
            continue
        stocks[code] = (dates, opens, highs, lows, closes, volumes)
    
    print(f"Quality stocks: {len(stocks)}")
    
    # Backtest: scan on each day, check future returns
    # Sample every 5 trading days to speed up
    all_signals = []
    
    sample_codes = list(stocks.keys())
    print(f"Running historical backtest...")
    
    for si, code in enumerate(sample_codes):
        if si % 200 == 0:
            print(f"  Progress: {si}/{len(sample_codes)}...")
        dates, opens, highs, lows, closes, volumes = stocks[code]
        
        # Scan from day 120 to day N-5 (need 5 days forward for checking)
        for idx in range(120, len(closes) - 5, 5):  # every 5 days
            score = breakout_score_at(closes, highs, lows, opens, volumes, idx)
            
            if score >= 50:
                # Buy at T+1 open
                buy_price = opens[idx + 1]
                if buy_price <= 0:
                    continue
                
                # Check returns at day 1, 2, 3, 5
                rets = {}
                for d in [1, 2, 3, 5]:
                    if idx + 1 + d < len(closes):
                        sell_price = closes[idx + 1 + d]
                        rets[f'd{d}'] = (sell_price / buy_price - 1) * 100
                
                # Max gain in next 5 days
                future_highs = highs[idx+1:idx+6]
                max_gain = (future_highs.max() / buy_price - 1) * 100 if len(future_highs) > 0 else 0
                
                all_signals.append({
                    'code': code, 'date': dates[idx], 'score': score,
                    'buy_price': buy_price, 'rets': rets, 'max_gain': max_gain
                })
    
    print(f"\nTotal signals: {len(all_signals)}")
    
    if not all_signals:
        print("No signals found!")
        return
    
    # Analysis by score threshold
    print(f"\n{'='*70}")
    print(f"IMMINENT BREAKOUT BACKTEST RESULTS")
    print(f"{'='*70}")
    
    for threshold in [50, 55, 60, 65, 70]:
        sigs = [s for s in all_signals if s['score'] >= threshold]
        if not sigs:
            continue
        
        d1 = [s['rets'].get('d1', 0) for s in sigs if 'd1' in s['rets']]
        d2 = [s['rets'].get('d2', 0) for s in sigs if 'd2' in s['rets']]
        d3 = [s['rets'].get('d3', 0) for s in sigs if 'd3' in s['rets']]
        d5 = [s['rets'].get('d5', 0) for s in sigs if 'd5' in s['rets']]
        max_g = [s['max_gain'] for s in sigs]
        
        w1 = len([r for r in d1 if r > 0]) / max(len(d1), 1) * 100
        w3 = len([r for r in d3 if r > 0]) / max(len(d3), 1) * 100
        w5 = len([r for r in d5 if r > 0]) / max(len(d5), 1) * 100
        
        print(f"\nScore >= {threshold}: {len(sigs)} signals")
        print(f"  Day 1: avg {np.mean(d1):+.2f}%, win {w1:.0f}%")
        print(f"  Day 3: avg {np.mean(d3):+.2f}%, win {w3:.0f}%")
        print(f"  Day 5: avg {np.mean(d5):+.2f}%, win {w5:.0f}%")
        print(f"  Max gain in 5d: avg {np.mean(max_g):+.2f}%, median {np.median(max_g):+.2f}%")
    
    # Best performing score range
    print(f"\n{'='*70}")
    print(f"SIGNAL QUALITY ANALYSIS")
    print(f"{'='*70}")
    
    high_score = [s for s in all_signals if s['score'] >= 65]
    med_score = [s for s in all_signals if 55 <= s['score'] < 65]
    low_score = [s for s in all_signals if 50 <= s['score'] < 55]
    
    for name, group in [("High (>=65)", high_score), ("Med (55-64)", med_score), ("Low (50-54)", low_score)]:
        if group:
            d3_rets = [s['rets'].get('d3', 0) for s in group if 'd3' in s['rets']]
            win = len([r for r in d3_rets if r > 0]) / max(len(d3_rets), 1) * 100
            print(f"  {name}: {len(group)} signals, 3d avg {np.mean(d3_rets):+.2f}%, win {win:.0f}%")

if __name__ == "__main__":
    main()
