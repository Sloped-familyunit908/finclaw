"""Analyze 源杰科技 trend characteristics + find similar stocks"""
import akshare as ak
import numpy as np
from datetime import datetime, timedelta

# Get 源杰科技 historical data
print("=== 源杰科技 688498 走势分析 ===")
try:
    df = ak.stock_zh_a_hist(symbol="688498", period="daily", start_date="20250301", end_date="20260320", adjust="qfq")
    df = df.sort_values('日期')
    
    prices = df['收盘'].values
    volumes = df['成交量'].values
    dates = df['日期'].values
    
    # Find key metrics
    min_price = prices.min()
    max_price = prices.max()
    min_idx = prices.argmin()
    max_idx = prices.argmax()
    
    print(f"  最低价: {min_price:.2f} ({dates[min_idx]})")
    print(f"  最高价: {max_price:.2f} ({dates[max_idx]})")
    print(f"  涨幅: {(max_price/min_price - 1)*100:.0f}%")
    
    # Analyze volume at key points
    avg_vol_before = volumes[:min_idx].mean() if min_idx > 5 else volumes[:5].mean()
    vol_at_breakout = volumes[min_idx:min_idx+10].mean() if min_idx+10 < len(volumes) else volumes[min_idx:].mean()
    print(f"  起涨前均量: {avg_vol_before:.0f}")
    print(f"  起涨时均量: {vol_at_breakout:.0f}")
    print(f"  量能放大: {vol_at_breakout/avg_vol_before:.1f}倍")
    
    # Calculate slope in different periods
    if len(prices) > 60:
        for period, name in [(30, "近30天"), (60, "近60天"), (120, "近120天"), (250, "近一年")]:
            if len(prices) >= period:
                p = prices[-period:]
                ret = (p[-1]/p[0] - 1) * 100
                # Calculate R-squared (trend clarity)
                x = np.arange(len(p))
                slope, intercept = np.polyfit(x, p, 1)
                pred = slope * x + intercept
                ss_res = np.sum((p - pred) ** 2)
                ss_tot = np.sum((p - p.mean()) ** 2)
                r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
                print(f"  {name}: 收益{ret:+.1f}%, 趋势R2={r2:.3f}, 斜率={slope:.2f}")
    
    # Check if our signals would have caught it
    # RSI at bottom
    if len(prices) > 14:
        # Simple RSI calc
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.convolve(gains, np.ones(14)/14, mode='valid')
        avg_loss = np.convolve(losses, np.ones(14)/14, mode='valid')
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - 100 / (1 + rs)
        
        if min_idx >= 14 and min_idx-14 < len(rsi):
            rsi_at_bottom = rsi[min_idx-14]
            print(f"  起涨点RSI: {rsi_at_bottom:.1f}")
    
except Exception as e:
    print(f"  Error: {e}")

# Now scan for stocks with similar characteristics
print("\n=== 寻找类似潜力股 ===")
print("特征: 底部放量 + 趋势刚起步 + R2开始升高")
try:
    # Get all A-share stocks
    all_stocks = ak.stock_zh_a_spot_em()
    
    # Filter: price 50-500, market cap > 50B, positive change
    candidates = all_stocks[
        (all_stocks['最新价'] > 50) & 
        (all_stocks['最新价'] < 500) &
        (all_stocks['涨跌幅'] > 0) &
        (all_stocks['成交额'] > 1e8)  # >1亿成交额
    ].copy()
    
    print(f"  筛选到 {len(candidates)} 只候选股")
    
    # Check each for trend quality
    results = []
    for _, row in candidates.head(50).iterrows():  # Check top 50 by volume
        code = row['代码']
        name = row['名称']
        price = row['最新价']
        change = row['涨跌幅']
        
        try:
            hist = ak.stock_zh_a_hist(symbol=code, period="daily", 
                                       start_date="20251001", end_date="20260320", adjust="qfq")
            if len(hist) < 60:
                continue
            
            closes = hist['收盘'].values
            vols = hist['成交量'].values
            
            # Trend metrics
            x = np.arange(len(closes))
            slope, _ = np.polyfit(x, closes, 1)
            pred = slope * x + closes[0]
            ss_res = np.sum((closes - pred) ** 2)
            ss_tot = np.sum((closes - closes.mean()) ** 2)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
            
            # Return over period
            total_ret = (closes[-1]/closes[0] - 1) * 100
            
            # Volume trend (recent vs old)
            recent_vol = vols[-20:].mean()
            old_vol = vols[:20].mean()
            vol_ratio = recent_vol / (old_vol + 1) 
            
            # Only keep stocks with clear uptrend + accelerating volume
            if r2 > 0.5 and total_ret > 30 and slope > 0 and vol_ratio > 1.2:
                results.append({
                    'code': code, 'name': name, 'price': price,
                    'ret': total_ret, 'r2': r2, 'slope': slope,
                    'vol_ratio': vol_ratio, 'change': change
                })
        except:
            continue
    
    # Sort by trend quality (R2 * return)
    results.sort(key=lambda x: x['r2'] * x['ret'], reverse=True)
    
    print(f"\n  找到 {len(results)} 只趋势清晰+加速放量的股票:")
    print(f"  {'代码':<10} {'名称':<10} {'现价':>8} {'半年涨幅':>8} {'趋势R2':>8} {'量能放大':>8}")
    for r in results[:15]:
        print(f"  {r['code']:<10} {r['name']:<10} {r['price']:>8.2f} {r['ret']:>+7.1f}% {r['r2']:>8.3f} {r['vol_ratio']:>7.1f}x")

except Exception as e:
    print(f"  Error: {e}")
