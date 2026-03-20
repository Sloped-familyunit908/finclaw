"""
Trend Discovery scan using LOCAL data (no API needed).
Scans downloaded CSV files for trend stocks.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.strategies.trend_discovery import TrendDiscovery

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "a_shares")

def load_csv(path):
    """Load a stock CSV into numpy arrays."""
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    with open(path, 'r') as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 7:
                try:
                    d, code, o, h, l, c, v = parts[0], parts[1], float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])
                    if c > 0 and v >= 0:
                        dates.append(d)
                        closes.append(c)
                        volumes.append(v)
                except:
                    continue
    return np.array(dates), np.array(closes), np.array(volumes)

def main():
    td = TrendDiscovery(rsi_oversold_threshold=25, r2_emerging_min=0.35)
    
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    print(f"Scanning {len(csv_files)} stocks from local data...")
    
    # Current scan - what looks good RIGHT NOW
    current_results = []
    # Historical scan - what had big trends in the past year
    historical_results = []
    
    for i, fname in enumerate(csv_files):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(csv_files)}...")
        
        path = os.path.join(DATA_DIR, fname)
        dates, closes, volumes = load_csv(path)
        
        if len(closes) < 120:
            continue
        
        code = fname.replace('_', '.').replace('.csv', '')
        
        # === CURRENT ANALYSIS: Is this a trend stock NOW? ===
        candidate = td.analyze_stock(closes, volumes, code, "")
        if candidate.signal in ("emerging_trend", "strong_trend"):
            # Calculate recent return
            ret_60d = (closes[-1] / closes[-60] - 1) * 100 if len(closes) >= 60 else 0
            ret_120d = (closes[-1] / closes[-120] - 1) * 100 if len(closes) >= 120 else 0
            current_results.append({
                "code": code, "score": candidate.score,
                "signal": candidate.signal, "price": closes[-1],
                "r2_30d": candidate.r2_30d, "r2_60d": candidate.r2_60d,
                "ret_60d": ret_60d, "ret_120d": ret_120d,
                "rsi_min": candidate.rsi_min_60d,
            })
        
        # === HISTORICAL: What were the biggest movers this year? ===
        min_price = closes.min()
        max_price = closes.max()
        total_ret = (max_price / min_price - 1) * 100
        
        if total_ret > 100:  # Only stocks that doubled
            min_idx = closes.argmin()
            max_idx = closes.argmax()
            
            # Only count if max is AFTER min (uptrend, not crash-bounce)
            if max_idx > min_idx:
                # When would our strategy have caught it?
                first_signal_idx = None
                for j in range(max(60, min_idx), min(max_idx, len(closes))):
                    c = td.analyze_stock(closes[:j+1], volumes[:j+1], code, "")
                    if c.signal in ("emerging_trend", "strong_trend"):
                        first_signal_idx = j
                        break
                
                if first_signal_idx:
                    price_at_signal = closes[first_signal_idx]
                    return_after = (max_price / price_at_signal - 1) * 100
                    capture = (max_price - price_at_signal) / (max_price - min_price) * 100
                    
                    historical_results.append({
                        "code": code, "total_ret": total_ret,
                        "min_price": min_price, "max_price": max_price,
                        "signal_date": dates[first_signal_idx] if first_signal_idx < len(dates) else "?",
                        "min_date": dates[min_idx],
                        "max_date": dates[max_idx],
                        "return_after": return_after,
                        "capture_pct": capture,
                        "price_at_signal": price_at_signal,
                    })
    
    # === REPORT ===
    print(f"\n{'='*80}")
    print(f"TREND DISCOVERY RESULTS ({len(csv_files)} stocks scanned)")
    print(f"{'='*80}")
    
    # Current trends
    current_results.sort(key=lambda x: x['score'], reverse=True)
    print(f"\n=== RIGHT NOW: {len(current_results)} stocks with active trends ===")
    print(f"{'Code':<15} {'Score':>5} {'Signal':<15} {'Price':>8} {'R2_60d':>6} {'60d%':>7} {'120d%':>7}")
    print("-" * 70)
    for r in current_results[:20]:
        print(f"{r['code']:<15} {r['score']:>5.0f} {r['signal']:<15} {r['price']:>8.2f} {r['r2_60d']:>6.3f} {r['ret_60d']:>+6.0f}% {r['ret_120d']:>+6.0f}%")
    
    # Historical
    historical_results.sort(key=lambda x: x['return_after'], reverse=True)
    print(f"\n=== PAST YEAR: {len(historical_results)} stocks doubled+ (and we could have caught) ===")
    print(f"{'Code':<15} {'Total':>7} {'After Signal':>12} {'Captured':>8} {'Bottom':>10} {'Signal':>10} {'Top':>10}")
    print("-" * 80)
    for r in historical_results[:20]:
        print(f"{r['code']:<15} {r['total_ret']:>+6.0f}% {r['return_after']:>+11.0f}% {r['capture_pct']:>7.0f}% {r['min_date']:>10} {r['signal_date']:>10} {r['max_date']:>10}")
    
    # Summary
    if historical_results:
        avg_capture = np.mean([r['capture_pct'] for r in historical_results])
        avg_return = np.mean([r['return_after'] for r in historical_results])
        win_count = len([r for r in historical_results if r['return_after'] > 0])
        print(f"\n=== STRATEGY PERFORMANCE ===")
        print(f"Stocks that doubled: {len(historical_results)}")
        print(f"Avg return after signal: {avg_return:+.1f}%")
        print(f"Avg trend captured: {avg_capture:.0f}%")
        print(f"Win rate: {win_count}/{len(historical_results)} ({win_count/len(historical_results)*100:.0f}%)")
        if historical_results[0]['return_after'] > 0:
            print(f"Best catch: {historical_results[0]['code']} +{historical_results[0]['return_after']:.0f}%")

if __name__ == "__main__":
    main()
