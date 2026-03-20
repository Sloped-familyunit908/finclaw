"""
IMMINENT BREAKOUT Scanner - Find stocks about to explode in 2-3 days
=====================================================================
Key signals for imminent breakout:
1. Squeezed volatility (BB width at minimum) = about to move
2. Volume drying up then just starting to pick up = accumulation ending
3. Price sitting right at key MA (5/10/20) support = spring loaded
4. RSI around 40-55 (not overbought, not oversold - neutral zone ready to go)
5. Recent consolidation after a move up = flag pattern
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

def imminent_breakout_score(dates, opens, highs, lows, closes, volumes):
    """Score a stock for imminent breakout potential (2-5 days)."""
    n = len(closes)
    if n < 60:
        return 0, {}
    
    score = 0
    details = {}
    
    # 1. BOLLINGER SQUEEZE - volatility at minimum = about to explode
    ma20 = closes[-20:].mean()
    std20 = closes[-20:].std()
    bb_width = (std20 / ma20) * 100  # as % of price
    
    # Compare to historical BB width
    bb_widths = []
    for i in range(20, min(n, 120)):
        w = closes[n-i-20:n-i].std() / closes[n-i-20:n-i].mean() * 100
        bb_widths.append(w)
    
    if bb_widths:
        bb_percentile = sum(1 for w in bb_widths if bb_width < w) / len(bb_widths) * 100
        if bb_percentile > 80:  # Current BB width is in bottom 20% = squeezed
            score += 20
            details['bb_squeeze'] = f"BB width at {100-bb_percentile:.0f} percentile (TIGHT!)"
        elif bb_percentile > 60:
            score += 10
            details['bb_squeeze'] = f"BB width narrowing ({100-bb_percentile:.0f} pct)"
    
    # 2. VOLUME PATTERN - dry then picking up (accumulation)
    vol_5d = volumes[-5:].mean()
    vol_10d = volumes[-10:-5].mean() if n >= 10 else volumes.mean()
    vol_20d = volumes[-20:].mean()
    
    # Volume was low (drying up) but just starting to increase
    if vol_10d < vol_20d * 0.7 and vol_5d > vol_10d * 1.1:
        score += 15
        details['volume'] = f"Vol dried up then picking up ({vol_5d/vol_10d:.1f}x last 5d)"
    elif vol_5d < vol_20d * 0.6:
        score += 10
        details['volume'] = f"Volume very low (accumulation phase)"
    
    # 3. PRICE AT KEY SUPPORT
    ma5 = closes[-5:].mean()
    ma10 = closes[-10:].mean()
    ma20_val = ma20
    price = closes[-1]
    
    # Price sitting right on MA support (within 2%)
    for ma_val, ma_name in [(ma5, 'MA5'), (ma10, 'MA10'), (ma20_val, 'MA20')]:
        dist = abs(price - ma_val) / ma_val * 100
        if dist < 2 and price >= ma_val:
            score += 10
            details['support'] = f"Price at {ma_name} support ({dist:.1f}% above)"
            break
    
    # 4. MA ALIGNMENT - must be bullish (5>10>20)
    if ma5 > ma10 > ma20_val:
        score += 10
        details['ma_align'] = "Bullish MA alignment (5>10>20)"
    elif ma5 > ma10:
        score += 5
        details['ma_align'] = "Short-term bullish (5>10)"
    
    # 5. RSI IN LAUNCH ZONE (40-60 = neutral, ready to go either way)
    rsi = calc_rsi(closes)
    if 40 <= rsi <= 55:
        score += 15
        details['rsi'] = f"RSI {rsi:.0f} - perfect launch zone"
    elif 55 < rsi <= 65:
        score += 8
        details['rsi'] = f"RSI {rsi:.0f} - slightly warm but ok"
    elif 30 <= rsi < 40:
        score += 10
        details['rsi'] = f"RSI {rsi:.0f} - oversold, could bounce"
    
    # 6. CONSOLIDATION PATTERN (flag/pennant after up move)
    # Recent 5 days range is very small compared to prior move
    range_5d = (highs[-5:].max() - lows[-5:].min()) / closes[-5].mean() * 100
    range_20d = (highs[-20:].max() - lows[-20:].min()) / closes[-20].mean() * 100
    
    if range_5d < range_20d * 0.3 and closes[-5] > closes[-20]:
        score += 15
        details['pattern'] = f"Flag/consolidation (5d range {range_5d:.1f}% vs 20d {range_20d:.1f}%)"
    
    # 7. RECENT TREND IS UP (20d positive)
    ret_20d = (closes[-1] / closes[-20] - 1) * 100
    if 5 < ret_20d < 30:
        score += 5
        details['trend'] = f"20d return +{ret_20d:.0f}% (healthy uptrend, not overheated)"
    
    # 8. TODAY'S ACTION (last candle clues)
    body = abs(closes[-1] - opens[-1])
    wick_upper = highs[-1] - max(closes[-1], opens[-1])
    wick_lower = min(closes[-1], opens[-1]) - lows[-1]
    
    # Small body with long lower wick = hammer = bullish
    if wick_lower > body * 2 and body > 0:
        score += 5
        details['candle'] = "Hammer candle (bullish reversal signal)"
    
    # Doji (tiny body) = decision point
    if body < (highs[-1] - lows[-1]) * 0.1 and highs[-1] != lows[-1]:
        score += 3
        details['candle'] = "Doji - decision point, usually precedes move"
    
    details['rsi_val'] = rsi
    details['bb_width'] = bb_width
    details['ret_20d'] = ret_20d
    details['price'] = closes[-1]
    
    return score, details

def main():
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    
    results = []
    
    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        dates, opens, highs, lows, closes, volumes = load_csv(path)
        code = fname.replace('_', '.').replace('.csv', '')
        
        # Filter
        if len(closes) < 60 or closes[-1] < 3:
            continue
        avg_amount = volumes[-20:].mean() * closes[-1]
        if avg_amount < 1e7:
            continue
        # Skip if already up too much today (chasing)
        if len(closes) >= 2:
            today_ret = (closes[-1] / closes[-2] - 1) * 100
            if today_ret > 7:  # already ran today, too late
                continue
        
        score, details = imminent_breakout_score(dates, opens, highs, lows, closes, volumes)
        
        if score >= 50:
            results.append({
                'code': code, 'score': score,
                'price': closes[-1], 'details': details,
            })
    
    results.sort(key=lambda x: -x['score'])
    
    print("=" * 80)
    print("IMMINENT BREAKOUT SCANNER - Stocks about to move in 2-3 days")
    print("=" * 80)
    print(f"Scanned: {len(csv_files)} | Quality: filtered | Threshold: score >= 50")
    print()
    
    print(f"{'Code':<13} {'Score':>5} {'Price':>8} {'RSI':>5} {'BB%':>5} {'20d%':>6}  Signals")
    print("-" * 90)
    
    for r in results[:30]:
        d = r['details']
        signals = ' | '.join([v for k, v in d.items() if k not in ('rsi_val', 'bb_width', 'ret_20d', 'price')])
        rsi = d.get('rsi_val', 0)
        bb = d.get('bb_width', 0)
        ret20 = d.get('ret_20d', 0)
        print(f"{r['code']:<13} {r['score']:>5} {r['price']:>8.2f} {rsi:>5.0f} {bb:>4.1f}% {ret20:>+5.0f}%  {signals[:60]}")
    
    print(f"\n=== TOP 5 IMMINENT BREAKOUT CANDIDATES ===")
    for i, r in enumerate(results[:5]):
        d = r['details']
        print(f"\n#{i+1} {r['code']} (Score: {r['score']})")
        print(f"   Price: {r['price']:.2f}")
        for k, v in d.items():
            if k not in ('rsi_val', 'bb_width', 'ret_20d', 'price'):
                print(f"   {v}")

if __name__ == "__main__":
    main()
