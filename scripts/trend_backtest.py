"""
Historical Trend Discovery Backtest
=====================================
Scan ALL A-share stocks over the past year to find:
1. Which stocks had strong trends
2. When did the trend signal first appear
3. How much return was left after signal triggered
4. Validate our trend discovery strategy on real data
"""
import sys
import os
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.trend_discovery import TrendDiscovery, TrendCandidate

def calculate_rsi_series(prices, period=14):
    """Calculate full RSI series."""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    
    rsi = np.full(len(prices), 50.0)
    if len(gains) < period:
        return rsi
    
    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / (avg_loss + 1e-10)
        rsi[i + 1] = 100 - 100 / (1 + rs)
    
    return rsi

def analyze_historical(code, name, prices, volumes, td):
    """Analyze a stock's trend history over the past year."""
    if len(prices) < 120:
        return None
    
    min_price = prices.min()
    max_price = prices.max()
    total_return = (max_price / min_price - 1) * 100
    
    if total_return < 50:
        return None  # Skip stocks that didn't move much
    
    # Find when trend signal would have first triggered
    rsi = calculate_rsi_series(prices)
    
    # Scan through time to find first "emerging_trend" signal
    first_signal_idx = None
    first_signal_type = None
    
    for i in range(60, len(prices)):
        window = prices[:i+1]
        vol_window = volumes[:i+1]
        
        candidate = td.analyze_stock(window, vol_window, code, name)
        
        if candidate.signal in ("emerging_trend", "strong_trend") and first_signal_idx is None:
            first_signal_idx = i
            first_signal_type = candidate.signal
            break
    
    if first_signal_idx is None:
        return None
    
    # Calculate return AFTER signal
    price_at_signal = prices[first_signal_idx]
    price_at_peak = prices[first_signal_idx:].max()
    price_at_end = prices[-1]
    
    return_to_peak = (price_at_peak / price_at_signal - 1) * 100
    return_to_end = (price_at_end / price_at_signal - 1) * 100
    
    # What % of the total move was captured
    total_move = max_price - min_price
    captured = price_at_peak - price_at_signal
    capture_pct = (captured / total_move * 100) if total_move > 0 else 0
    
    return {
        "code": code,
        "name": name,
        "total_return": total_return,
        "signal_idx": first_signal_idx,
        "signal_type": first_signal_type,
        "signal_price": price_at_signal,
        "peak_price": price_at_peak,
        "end_price": price_at_end,
        "return_after_signal": return_to_peak,
        "return_to_end": return_to_end,
        "capture_pct": capture_pct,
        "rsi_at_signal": rsi[first_signal_idx],
    }

def main():
    import akshare as ak
    
    td = TrendDiscovery(rsi_oversold_threshold=25, r2_emerging_min=0.35)
    
    print("=" * 80)
    print("Historical Trend Discovery Backtest - Past Year A-Shares")
    print("=" * 80)
    
    # Get stock list - focus on stocks > 50 yuan to find quality names
    print("\nFetching stock list...")
    try:
        all_stocks = ak.stock_zh_a_spot_em()
    except:
        time.sleep(5)
        all_stocks = ak.stock_zh_a_spot_em()
    
    # Filter for meaningful stocks
    candidates = all_stocks[
        (all_stocks['最新价'] > 30) &
        (all_stocks['成交额'] > 5e7)
    ].copy()
    
    print(f"Scanning {len(candidates)} stocks...")
    
    results = []
    errors = 0
    
    for idx, (_, row) in enumerate(candidates.iterrows()):
        code = row['代码']
        name = row['名称']
        
        if idx % 50 == 0:
            print(f"  Progress: {idx}/{len(candidates)}...")
        
        try:
            hist = ak.stock_zh_a_hist(
                symbol=code, period="daily",
                start_date="20250301", end_date="20260320", adjust="qfq"
            )
            if len(hist) < 120:
                continue
            
            prices = hist['收盘'].values.astype(float)
            volumes = hist['成交量'].values.astype(float)
            
            result = analyze_historical(code, name, prices, volumes, td)
            if result:
                results.append(result)
            
            time.sleep(0.3)  # Rate limit
            
        except Exception as e:
            errors += 1
            if errors > 20:
                print(f"  Too many errors ({errors}), stopping scan")
                break
            time.sleep(1)
            continue
    
    # Sort by return after signal (how much we'd have made)
    results.sort(key=lambda x: x['return_after_signal'], reverse=True)
    
    print(f"\n{'=' * 80}")
    print(f"Results: Found {len(results)} stocks with trend signals (out of {len(candidates)} scanned)")
    print(f"{'=' * 80}")
    
    print(f"\n{'代码':<10} {'名称':<10} {'总涨幅':>8} {'信号后涨幅':>10} {'捕获%':>6} {'信号RSI':>7} {'类型':<15}")
    print("-" * 75)
    
    for r in results[:30]:
        print(f"{r['code']:<10} {r['name']:<10} {r['total_return']:>+7.0f}% {r['return_after_signal']:>+9.0f}% {r['capture_pct']:>5.0f}% {r['rsi_at_signal']:>7.1f} {r['signal_type']}")
    
    # Summary stats
    if results:
        avg_capture = np.mean([r['capture_pct'] for r in results])
        avg_return = np.mean([r['return_after_signal'] for r in results])
        win_rate = len([r for r in results if r['return_after_signal'] > 0]) / len(results) * 100
        
        print(f"\n=== Summary ===")
        print(f"Stocks found: {len(results)}")
        print(f"Avg return after signal: {avg_return:+.1f}%")
        print(f"Avg trend captured: {avg_capture:.0f}%")
        print(f"Win rate: {win_rate:.0f}%")
        print(f"Best: {results[0]['name']} +{results[0]['return_after_signal']:.0f}%")

if __name__ == "__main__":
    main()
