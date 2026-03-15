"""
Optimize grade weights and rebalance frequency.
Grid search over different weight ratios and rebalance periods.
"""
import asyncio, random, math, statistics
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v9 import AssetSelector, AssetGrade

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def fetch_crypto(asset, days=365):
    import aiohttp
    coin = {"BTC":"bitcoin","ETH":"ethereum","SOL":"solana"}[asset]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r:
            if r.status == 429:
                await asyncio.sleep(62)
                async with s.get(url, params={"vs_currency":"usd","days":str(days)}) as r2:
                    data = await r2.json()
            else:
                data = await r.json()
    hist = [{"date":datetime.fromtimestamp(ts/1000),"price":p} for ts,p in data.get("prices",[])]
    for i,(ts,v) in enumerate(data.get("total_volumes",[])):
        if i < len(hist): hist[i]["volume"] = v
    return hist

async def main():
    print("Loading scenarios...")
    scenarios = [
        {"n":"NVDA",    "h": sim(500, 252, 0.80, 0.50, 1395)},
        {"n":"AAPL",    "h": sim(180, 252, 0.15, 0.25, 1002)},
        {"n":"TSLA",    "h": sim(250, 252, 0.40, 0.65, 1525)},
        {"n":"META",    "h": sim(550, 252,-0.20, 0.35, 1004)},
        {"n":"AMZN",    "h": sim(180, 252, 0.30, 0.35, 1628)},
        {"n":"INTC",    "h": sim(40,  252,-0.50, 0.40, 1006)},
        {"n":"Moutai",  "h": sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)},
        {"n":"CATL",    "h": sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)},
        {"n":"CSI300",  "h": sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)},
    ]
    for asset in ["BTC","ETH","SOL"]:
        try:
            h = await fetch_crypto(asset, 365)
            if h and len(h) > 30:
                scenarios.append({"n":asset,"h":h})
            await asyncio.sleep(5)
        except:
            pass

    N = len(scenarios)
    selector = AssetSelector()

    # Get full backtest returns
    print("Running backtests...")
    returns = {}
    for sc in scenarios:
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run("T","v7",sc["h"])
        returns[sc["n"]] = r.total_return

    # Get grades at different lookback points
    grades_at = {}
    for lb in [60, 90, 120, 150]:
        grades_at[lb] = {}
        for sc in scenarios:
            h = sc["h"]
            p = [x["price"] for x in h[:min(lb,len(h))]]
            v = [x.get("volume",0) for x in h[:min(lb,len(h))]]
            if len(p) >= 60:
                score = selector.score_asset(p, v)
                grades_at[lb][sc["n"]] = score.grade
            else:
                grades_at[lb][sc["n"]] = AssetGrade.C

    # Grid search over weight configs and lookback
    weight_configs = [
        {"name": "conservative",  "w": {AssetGrade.A_PLUS:3, AssetGrade.A:2, AssetGrade.B:1.5, AssetGrade.C:1, AssetGrade.F:0.5}},
        {"name": "baseline",      "w": {AssetGrade.A_PLUS:5, AssetGrade.A:3, AssetGrade.B:2, AssetGrade.C:1, AssetGrade.F:0.5}},
        {"name": "aggressive",    "w": {AssetGrade.A_PLUS:8, AssetGrade.A:4, AssetGrade.B:2, AssetGrade.C:1, AssetGrade.F:0.3}},
        {"name": "ultra",         "w": {AssetGrade.A_PLUS:10, AssetGrade.A:5, AssetGrade.B:2, AssetGrade.C:0.5, AssetGrade.F:0.1}},
        {"name": "top-heavy",     "w": {AssetGrade.A_PLUS:12, AssetGrade.A:6, AssetGrade.B:1.5, AssetGrade.C:0.5, AssetGrade.F:0.2}},
        {"name": "skip-F",        "w": {AssetGrade.A_PLUS:5, AssetGrade.A:3, AssetGrade.B:2, AssetGrade.C:1, AssetGrade.F:0}},
    ]

    ew_ret = statistics.mean(returns[sc["n"]] for sc in scenarios)
    bh_ret = statistics.mean(sc["h"][-1]["price"]/sc["h"][0]["price"]-1 for sc in scenarios)

    print(f"\nB&H EW: {bh_ret:+.1%}  |  WT EW: {ew_ret:+.1%}  |  Alpha: {ew_ret-bh_ret:+.1%}")
    print(f"\n{'Config':<15} {'LB':>4} {'Portfolio Ret':>13} {'Alpha vs BH':>12} {'Alpha vs EW':>12}")
    print("-"*65)

    best_ret = -999; best_config = ""

    for cfg in weight_configs:
        for lb in [60, 90, 120, 150]:
            grades = grades_at[lb]
            w = cfg["w"]
            total_w = sum(w.get(grades[sc["n"]], 1) for sc in scenarios)
            if total_w == 0: total_w = 1
            alloc = {sc["n"]: w.get(grades[sc["n"]], 1)/total_w for sc in scenarios}

            port_ret = sum(alloc[sc["n"]] * returns[sc["n"]] for sc in scenarios)

            alpha_bh = port_ret - bh_ret
            alpha_ew = port_ret - ew_ret

            print(f"{cfg['name']:<15} {lb:>4} {port_ret:>+12.2%} {alpha_bh:>+11.2%} {alpha_ew:>+11.2%}")

            if port_ret > best_ret:
                best_ret = port_ret
                best_config = f"{cfg['name']} lb={lb}"

    print(f"\nBest: {best_config} -> {best_ret:+.2%}")

asyncio.run(main())
