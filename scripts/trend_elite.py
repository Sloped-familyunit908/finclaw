"""
Trend Discovery - ELITE Selection
===================================
From 805 signals, select only the TOP ones with:
1. Highest slope/time ratio (about to explode)
2. R2 accelerating (trend getting stronger)
3. RSI was recently oversold (spring loaded)
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.strategies.trend_discovery import TrendDiscovery

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
                        closes.append(c)
                        volumes.append(v)
                except:
                    continue
    return dates, np.array(opens), np.array(closes), np.array(volumes)

def calc_slope_per_day(closes, window):
    """Return daily price gain from linear fit, normalized by price."""
    if len(closes) < window:
        return 0
    p = closes[-window:]
    x = np.arange(len(p))
    slope, _ = np.polyfit(x, p, 1)
    return slope / p[0] * 100  # daily % gain

def calc_r2(closes, window):
    if len(closes) < window:
        return 0
    p = closes[-window:]
    x = np.arange(len(p))
    slope, intercept = np.polyfit(x, p, 1)
    pred = slope * x + intercept
    ss_res = np.sum((p - pred) ** 2)
    ss_tot = np.sum((p - p.mean()) ** 2)
    return max(0, 1 - ss_res / ss_tot) if ss_tot > 0 else 0

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

def main():
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    
    candidates = []
    
    for fname in csv_files:
        path = os.path.join(DATA_DIR, fname)
        dates, opens, closes, volumes = load_csv(path)
        code = fname.replace('_', '.').replace('.csv', '')
        
        if len(closes) < 120 or closes[-1] < 3:
            continue
        avg_amount = volumes[-60:].mean() * closes[-1]
        if avg_amount < 1e7:  # > 1000万成交额 (stricter)
            continue
        
        # Calculate elite metrics
        slope_30d = calc_slope_per_day(closes, 30)
        slope_60d = calc_slope_per_day(closes, 60)
        r2_30d = calc_r2(closes, 30)
        r2_60d = calc_r2(closes, 60)
        r2_120d = calc_r2(closes, 120)
        rsi = calc_rsi(closes)
        rsi_min_60d = min([calc_rsi(closes[:i]) for i in range(max(len(closes)-60, 15), len(closes))]) if len(closes) > 75 else rsi
        
        ret_30d = (closes[-1] / closes[-30] - 1) * 100 if len(closes) >= 30 else 0
        ret_60d = (closes[-1] / closes[-60] - 1) * 100 if len(closes) >= 60 else 0
        ret_120d = (closes[-1] / closes[-120] - 1) * 100 if len(closes) >= 120 else 0
        
        # Volume acceleration
        vol_recent = volumes[-10:].mean()
        vol_old = volumes[-30:-10].mean() if len(volumes) >= 30 else volumes.mean()
        vol_accel = vol_recent / (vol_old + 1)
        
        # R2 acceleration (trend getting clearer)
        r2_accel = r2_30d - r2_60d  # positive = trend strengthening recently
        
        # ELITE SCORE: combines slope efficiency + trend clarity + momentum
        # Slope per day * R2 = "efficient trend" (high slope + clear direction)
        elite_score = slope_30d * r2_30d * 100
        
        # Bonus for R2 accelerating (trend just forming = early stage)
        if r2_accel > 0.1:
            elite_score *= 1.3
        
        # Bonus for RSI was recently oversold (spring loaded)
        if rsi_min_60d < 25:
            elite_score *= 1.2
        
        # Penalty for already overbought
        if rsi > 80:
            elite_score *= 0.5
        
        # Must have positive slope and decent R2
        if slope_30d > 0 and r2_30d > 0.3 and ret_30d > 5:
            candidates.append({
                'code': code, 'price': closes[-1],
                'elite_score': elite_score,
                'slope_30d': slope_30d, 'slope_60d': slope_60d,
                'r2_30d': r2_30d, 'r2_60d': r2_60d, 'r2_120d': r2_120d,
                'r2_accel': r2_accel,
                'rsi': rsi, 'rsi_min_60d': rsi_min_60d,
                'ret_30d': ret_30d, 'ret_60d': ret_60d, 'ret_120d': ret_120d,
                'vol_accel': vol_accel,
            })
    
    # Sort by elite score
    candidates.sort(key=lambda x: -x['elite_score'])
    
    total_with_signal = len(candidates)
    
    print(f"{'='*90}")
    print(f"TREND DISCOVERY - ELITE SELECTION")
    print(f"{'='*90}")
    print(f"Stocks scanned: {len(csv_files)}")
    print(f"With positive trend: {total_with_signal}")
    print(f"ELITE TOP 20 (sorted by slope*R2 efficiency):")
    print()
    print(f"{'Code':<13} {'Price':>7} {'Elite':>6} {'Slope/d':>8} {'R2_30':>6} {'R2_60':>6} {'R2accel':>7} {'RSI':>5} {'30d%':>6} {'60d%':>6} {'120d%':>6} {'VolAcc':>6}")
    print("-" * 100)
    
    for r in candidates[:20]:
        print(f"{r['code']:<13} {r['price']:>7.2f} {r['elite_score']:>6.0f} {r['slope_30d']:>7.2f}% {r['r2_30d']:>6.3f} {r['r2_60d']:>6.3f} {r['r2_accel']:>+6.2f} {r['rsi']:>5.0f} {r['ret_30d']:>+5.0f}% {r['ret_60d']:>+5.0f}% {r['ret_120d']:>+5.0f}% {r['vol_accel']:>5.1f}x")
    
    # Stage analysis
    print(f"\n{'='*90}")
    print("STAGE ANALYSIS - Where are they in their trend?")
    print('='*90)
    
    for r in candidates[:20]:
        stage = ""
        if r['r2_30d'] > 0.7 and r['r2_60d'] < 0.5:
            stage = "EARLY (trend just forming!)"
        elif r['r2_30d'] > 0.7 and r['r2_60d'] > 0.7 and r['r2_120d'] < 0.5:
            stage = "ACCELERATING (getting stronger)"
        elif r['r2_30d'] > 0.7 and r['r2_60d'] > 0.7 and r['r2_120d'] > 0.7:
            stage = "MATURE (may be near peak)"
        elif r['r2_accel'] > 0.15:
            stage = "EMERGING (R2 rising fast)"
        else:
            stage = "STEADY"
        
        explosive = ""
        if r['slope_30d'] > r['slope_60d'] * 1.5:
            explosive = " ** ACCELERATING SLOPE!"
        
        print(f"  {r['code']:<13} {stage}{explosive}")
    
    # Summary recommendation
    early = [r for r in candidates[:20] if r['r2_accel'] > 0.1 and r['rsi'] < 70]
    print(f"\nBEST OPPORTUNITIES (early stage + not overbought): {len(early)}")
    for r in early[:10]:
        print(f"  {r['code']} price={r['price']:.2f} slope={r['slope_30d']:.2f}%/day R2_accel={r['r2_accel']:+.2f} RSI={r['rsi']:.0f}")

if __name__ == "__main__":
    main()
