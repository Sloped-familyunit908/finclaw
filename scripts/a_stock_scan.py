"""A-share stock scanner - FinClaw"""
import sys, numpy as np, warnings
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')
import yfinance as yf
from src.ta import rsi, macd, bollinger_bands

TICKERS = [
    ('600519.SS','MaoTai'), ('000858.SZ','WuLiangYe'), ('002594.SZ','BYD'),
    ('300750.SZ','CATL'), ('601899.SS','ZiJin'), ('600036.SS','CMB'),
    ('000333.SZ','Midea'), ('300059.SZ','EastMoney'), ('002230.SZ','iFlytek'),
    ('600900.SS','CYPC'), ('601318.SS','PingAn'), ('002415.SZ','Hikvision'),
    ('600031.SS','Sany'), ('601668.SS','CSCEC'), ('600809.SS','FenJiu'),
    ('000725.SZ','BOE'), ('002475.SZ','Luxshare'), ('688981.SS','SMIC'),
    ('002714.SZ','MuYuan'), ('601633.SS','GWM'),
]

results = []
for tk, nm in TICKERS:
    try:
        df = yf.Ticker(tk).history(period='3mo')
        if df.empty or len(df) < 20:
            continue
        c = np.array(df['Close'].tolist())
        v = df['Volume'].tolist()
        r = float(rsi(c)[-1])
        ml, sl, hl = macd(c)
        h = float(hl[-1])
        bb = bollinger_bands(c)
        pb = float(bb['pct_b'][-1]) * 100
        c1 = float((c[-1]/c[-2]-1)*100)
        c5 = float((c[-1]/c[-5]-1)*100)
        vr = v[-1] / (sum(v[-20:])/20) if sum(v[-20:]) > 0 else 0

        sc = 0
        if r < 30: sc += 4
        elif r < 40: sc += 3
        elif r < 50: sc += 1
        if h > 0: sc += 2
        if pb < 20: sc += 3
        elif pb < 40: sc += 1
        if 0 < c5 < 8: sc += 2
        if 1.2 < vr < 3: sc += 1

        sig = '** BUY' if sc >= 6 else '=> WATCH' if sc >= 4 else '   hold'
        results.append((sc, nm, tk, c[-1], r, h, pb, c1, c5, vr, sig))
    except Exception as e:
        print(f"ERR {nm}: {e}")

results.sort(key=lambda x: -x[0])

print("A-Share Stock Scanner -- FinClaw")
print("=" * 95)
print(f"{'Rank':<5}{'Name':<13}{'Code':<12}{'Price':>9}{'RSI':>7}{'MACD_H':>8}{'B%':>7}{'1D%':>7}{'5D%':>7}{'VR':>6}{'Scr':>4} Signal")
print("-" * 95)
for i, (sc, nm, tk, pr, rs, hh, pb, c1, c5, vr, sg) in enumerate(results):
    print(f"{i+1:<5}{nm:<13}{tk:<12}{pr:>9.2f}{rs:>7.1f}{hh:>+8.2f}{pb:>7.1f}{c1:>+7.2f}{c5:>+7.2f}{vr:>6.1f}{sc:>4} {sg}")

print()
top = [x for x in results if x[0] >= 5]
if top:
    print("RECOMMENDED (Score >= 5):")
    for sc, nm, tk, pr, rs, hh, pb, c1, c5, vr, sg in top:
        reasons = []
        if rs < 40: reasons.append(f"RSI oversold({rs:.0f})")
        if hh > 0: reasons.append("MACD golden cross")
        if pb < 30: reasons.append("near Bollinger lower")
        if 0 < c5 < 8: reasons.append(f"mild uptrend({c5:+.1f}%)")
        reason_str = ", ".join(reasons) if reasons else "high composite score"
        print(f"  {nm} ({tk}) Score={sc} -- {reason_str}")
else:
    print("No strong buy signals found in current scan.")
