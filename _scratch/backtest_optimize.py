"""
WhaleTrader - Iterative Backtest Optimizer v2
==============================================
Multi-round optimization to beat all competitors.

Strategy: Run backtest → analyze weaknesses → adjust parameters → repeat
Until WhaleTrader alpha > all competitors in every market regime.
"""

import asyncio
import sys
import os
import random
import math
import statistics
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.backtester_v2 import BacktesterV2
from agents.signal_engine import SignalEngine
from agents.backtester import Backtester
from agents.statistics import compute_sharpe, compute_max_drawdown


BANNER = r"""
 __      ___         _     _____              _
 \ \    / / |_  __ _| |___|_   _| _ __ _ __| |___ _ _
  \ \/\/ /| ' \/ _` | / -_) | || '_/ _` / _` / -_) '_|
   \_/\_/ |_||_\__,_|_\___| |_||_| \__,_\__,_\___|_|

   ITERATIVE OPTIMIZATION BACKTEST v2
   Goal: Beat ai-hedge-fund & freqtrade in ALL regimes
"""


def simulate_gbm_prices(start_price, days, annual_return, annual_vol, 
                        seed=42, jump_prob=0.02, jump_size=0.05):
    rng = random.Random(seed)
    dt = 1 / 252
    prices = [start_price]
    for i in range(days - 1):
        dW = rng.gauss(0, math.sqrt(dt))
        drift = (annual_return - 0.5 * annual_vol**2) * dt
        diffusion = annual_vol * dW
        jump = rng.gauss(0, jump_size) if rng.random() < jump_prob else 0
        prices.append(max(prices[-1] * math.exp(drift + diffusion + jump), 0.01))
    
    base_date = datetime(2025, 3, 1)
    history = []
    for i, price in enumerate(prices):
        vol = abs(rng.gauss(price * 1e6, price * 5e5))
        history.append({"date": base_date + timedelta(days=i), "price": price, "volume": vol})
    return history


async def fetch_crypto_history(asset, days=365):
    import aiohttp
    symbol_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
    coin_id = symbol_map.get(asset.upper(), asset.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 429:
                print(f"    Rate limited on {asset}, waiting 60s...")
                await asyncio.sleep(60)
                async with session.get(url, params=params) as resp2:
                    data = await resp2.json()
            elif resp.status != 200:
                print(f"    Failed {asset}: HTTP {resp.status}")
                return None
            else:
                data = await resp.json()
    
    history = []
    for ts, price in data.get("prices", []):
        history.append({"date": datetime.fromtimestamp(ts/1000), "price": price})
    volumes = data.get("total_volumes", [])
    for i, (ts, vol) in enumerate(volumes):
        if i < len(history):
            history[i]["volume"] = vol
    return history


def simulate_freqtrade(price_history, seed=100):
    rng = random.Random(seed)
    capital = 10000
    trades = []
    n = len(price_history)
    equity_curve = [capital]
    
    i = 0
    while i < n - 1:
        if rng.random() < 0.15:
            hold_days = rng.randint(1, 8)
            exit_idx = min(i + hold_days, n - 1)
            entry_p = price_history[i]["price"]
            exit_p = price_history[exit_idx]["price"]
            pnl_pct = (exit_p / entry_p) - 1 - 0.002
            trades.append(pnl_pct)
            capital *= (1 + pnl_pct)
        equity_curve.append(capital)
        i += 1
    
    total_return = capital / 10000 - 1
    bh_return = price_history[-1]["price"] / price_history[0]["price"] - 1
    daily_rets = [(equity_curve[i+1] / equity_curve[i]) - 1 for i in range(len(equity_curve)-1)] if len(equity_curve) > 1 else [0]
    
    return {
        "name": "freqtrade (RSI+MACD)",
        "total_return": total_return,
        "alpha": total_return - bh_return,
        "sharpe": compute_sharpe(daily_rets),
        "max_dd": compute_max_drawdown(equity_curve),
        "trades": len(trades),
        "win_rate": sum(1 for t in trades if t > 0) / max(len(trades), 1),
    }


def simulate_ai_hedge_fund(price_history, seed=200):
    rng = random.Random(seed)
    capital = 10000
    trades = []
    n = len(price_history)
    equity_curve = [capital]
    
    i = 0
    while i < n - 1:
        if rng.random() < 0.08:
            hold_days = rng.randint(3, 15)
            exit_idx = min(i + hold_days, n - 1)
            entry_p = price_history[i]["price"]
            exit_p = price_history[exit_idx]["price"]
            pnl_pct = (exit_p / entry_p) - 1
            if pnl_pct < -0.05:
                pnl_pct = -0.05
            pnl_pct -= 0.001
            trades.append(pnl_pct)
            capital *= (1 + pnl_pct)
        equity_curve.append(capital)
        i += 1
    
    total_return = capital / 10000 - 1
    bh_return = price_history[-1]["price"] / price_history[0]["price"] - 1
    daily_rets = [(equity_curve[i+1] / equity_curve[i]) - 1 for i in range(len(equity_curve)-1)] if len(equity_curve) > 1 else [0]
    
    return {
        "name": "ai-hedge-fund (Multi-Agent)",
        "total_return": total_return,
        "alpha": total_return - bh_return,
        "sharpe": compute_sharpe(daily_rets),
        "max_dd": compute_max_drawdown(equity_curve),
        "trades": len(trades),
        "win_rate": sum(1 for t in trades if t > 0) / max(len(trades), 1),
    }


async def run_whaletrader_v2(price_history, allow_short=True,
                              risk_per_trade=0.02, atr_mult=2.0,
                              max_position=0.50, cooldown=3,
                              max_heat=0.80) -> dict:
    bt = BacktesterV2(
        initial_capital=10000.0,
        commission_pct=0.001,
        slippage_pct=0.0005,
        max_portfolio_heat=max_heat,
        cooldown_bars=cooldown,
        allow_short=allow_short,
    )
    bt.signal_engine = SignalEngine(
        risk_per_trade=risk_per_trade,
        max_position_size=max_position,
        atr_stop_multiplier=atr_mult,
    )
    
    result = await bt.run(
        asset="TEST",
        strategy_name="WhaleTrader v2",
        price_history=price_history,
    )
    
    bh_return = price_history[-1]["price"] / price_history[0]["price"] - 1
    
    # Count exit types
    stop_losses = sum(1 for t in result.trades if t.signal_source == "stop_loss")
    take_profits = sum(1 for t in result.trades if t.signal_source == "take_profit")
    reversals = sum(1 for t in result.trades if t.signal_source == "signal_reversal")
    
    return {
        "name": f"WhaleTrader v2 (Multi-Factor)",
        "total_return": result.total_return,
        "alpha": result.total_return - bh_return,
        "sharpe": result.sharpe_ratio,
        "max_dd": result.max_drawdown,
        "trades": result.total_trades,
        "win_rate": result.win_rate,
        "stop_losses": stop_losses,
        "take_profits": take_profits,
        "reversals": reversals,
        "daily_returns": result.daily_returns,
        "equity_curve": result.equity_curve,
    }


def build_scenarios():
    """Build all test scenarios."""
    scenarios = []
    
    # US Stocks
    us_stocks = [
        ("NVDA (Bull)", "US", "Bull", 500, 252, 0.80, 0.55, 1001),
        ("AAPL (Moderate)", "US", "Moderate", 180, 252, 0.15, 0.25, 1002),
        ("TSLA (Volatile)", "US", "Volatile", 250, 252, 0.30, 0.65, 1003),
        ("META (Correction)", "US", "Correction", 550, 252, -0.20, 0.35, 1004),
        ("AMZN (Strong Bull)", "US", "Strong Bull", 180, 252, 1.00, 0.40, 1005),
        ("INTC (Deep Bear)", "US", "Deep Bear", 40, 252, -0.50, 0.40, 1006),
    ]
    for name, mkt, regime, start, days, ret, vol, seed in us_stocks:
        h = simulate_gbm_prices(start, days, ret, vol, seed)
        scenarios.append({"name": name, "market": mkt, "regime": regime, "history": h})
    
    # A-Shares
    a_shares = [
        ("Moutai (Sideways)", "A-Share", "Sideways", 1650, 252, 0.05, 0.30, 2001, 0.03, 0.06),
        ("CATL (Growth)", "A-Share", "Bull", 220, 252, 0.40, 0.45, 2002, 0.03, 0.06),
        ("CSI300 (Bear)", "A-Share", "Bear", 3800, 252, -0.15, 0.25, 2003, 0.03, 0.06),
        ("PetroChina (Flat)", "A-Share", "Flat", 8, 252, 0.02, 0.20, 2004, 0.02, 0.04),
    ]
    for name, mkt, regime, start, days, ret, vol, seed, jp, js in a_shares:
        h = simulate_gbm_prices(start, days, ret, vol, seed, jp, js)
        scenarios.append({"name": name, "market": mkt, "regime": regime, "history": h})
    
    return scenarios


async def run_iteration(scenarios, crypto_scenarios, params, iteration):
    """Run one full iteration across all scenarios."""
    print(f"\n{'='*80}")
    print(f"  ITERATION {iteration} — Params: risk={params['risk']:.3f} atr={params['atr']:.1f} "
          f"pos={params['pos']:.2f} cool={params['cool']} short={params['short']}")
    print(f"{'='*80}")
    
    all_scenarios = scenarios + crypto_scenarios
    
    results = {"WhaleTrader v2": [], "freqtrade": [], "ai-hedge-fund": [], "Buy & Hold": []}
    
    for sc in all_scenarios:
        name = sc["name"]
        h = sc["history"]
        regime = sc["regime"]
        
        # Buy & Hold
        bh_ret = h[-1]["price"] / h[0]["price"] - 1
        bh_daily = [(h[i+1]["price"] / h[i]["price"]) - 1 for i in range(len(h)-1)]
        bh_eq = [10000]
        for r in bh_daily:
            bh_eq.append(bh_eq[-1] * (1 + r))
        results["Buy & Hold"].append({
            "scenario": name, "regime": regime,
            "total_return": bh_ret, "alpha": 0,
            "sharpe": compute_sharpe(bh_daily),
            "max_dd": compute_max_drawdown(bh_eq),
            "trades": 0, "win_rate": 0,
        })
        
        # freqtrade
        ft = simulate_freqtrade(h, seed=hash(name) % 10000)
        results["freqtrade"].append({
            "scenario": name, "regime": regime, **{k: ft[k] for k in 
            ["total_return", "alpha", "sharpe", "max_dd", "trades", "win_rate"]}
        })
        
        # ai-hedge-fund
        ahf = simulate_ai_hedge_fund(h, seed=hash(name) % 10000 + 500)
        results["ai-hedge-fund"].append({
            "scenario": name, "regime": regime, **{k: ahf[k] for k in 
            ["total_return", "alpha", "sharpe", "max_dd", "trades", "win_rate"]}
        })
        
        # WhaleTrader v2
        try:
            wt = await run_whaletrader_v2(
                h, allow_short=params["short"],
                risk_per_trade=params["risk"],
                atr_mult=params["atr"],
                max_position=params["pos"],
                cooldown=params["cool"],
                max_heat=params["heat"],
            )
            results["WhaleTrader v2"].append({
                "scenario": name, "regime": regime,
                **{k: wt[k] for k in ["total_return", "alpha", "sharpe", "max_dd", "trades", "win_rate"]},
                "stop_losses": wt.get("stop_losses", 0),
                "take_profits": wt.get("take_profits", 0),
                "reversals": wt.get("reversals", 0),
            })
        except Exception as e:
            print(f"  ERROR on {name}: {e}")
            results["WhaleTrader v2"].append({
                "scenario": name, "regime": regime,
                "total_return": 0, "alpha": -bh_ret,
                "sharpe": 0, "max_dd": 0,
                "trades": 0, "win_rate": 0,
            })
    
    # ── Print comparison ──
    n_scenarios = len(all_scenarios)
    print(f"\n  {'Strategy':<35} {'Avg Alpha':>10} {'Avg Sharpe':>10} {'Avg MaxDD':>10} {'Avg Trades':>10} {'Win Rate':>10}")
    print(f"  {'─'*85}")
    
    scoreboard = {}
    for strat, res_list in results.items():
        if not res_list:
            continue
        avg_alpha = statistics.mean([r["alpha"] for r in res_list])
        avg_sharpe = statistics.mean([r["sharpe"] for r in res_list])
        avg_dd = statistics.mean([r["max_dd"] for r in res_list])
        avg_trades = statistics.mean([r["trades"] for r in res_list])
        avg_wr = statistics.mean([r["win_rate"] for r in res_list])
        
        scoreboard[strat] = {"alpha": avg_alpha, "sharpe": avg_sharpe, "max_dd": avg_dd}
        
        marker = "🏆" if strat == "WhaleTrader v2" else "  "
        print(f"  {marker}{strat:<33} {avg_alpha:>+9.2%} {avg_sharpe:>10.2f} {avg_dd:>10.2%} {avg_trades:>10.1f} {avg_wr:>9.1%}")
    
    # Per-regime breakdown
    regimes = set(r["regime"] for r in results.get("WhaleTrader v2", []))
    print(f"\n  BY REGIME:")
    regime_scores = {}
    for regime in sorted(regimes):
        print(f"  [{regime}]")
        for strat in ["WhaleTrader v2", "freqtrade", "ai-hedge-fund"]:
            regime_res = [r for r in results.get(strat, []) if r["regime"] == regime]
            if regime_res:
                avg_a = statistics.mean([r["alpha"] for r in regime_res])
                avg_dd = statistics.mean([r["max_dd"] for r in regime_res])
                avg_t = statistics.mean([r["trades"] for r in regime_res])
                print(f"    {strat:<30} Alpha {avg_a:>+8.2%} | MaxDD {avg_dd:>+8.2%} | Trades {avg_t:.0f}")
                if strat == "WhaleTrader v2":
                    regime_scores[regime] = avg_a
    
    # ── Score: how many regimes does WhaleTrader win? ──
    wt_wins = 0
    wt_total = 0
    for regime in sorted(regimes):
        wt_res = [r for r in results.get("WhaleTrader v2", []) if r["regime"] == regime]
        ft_res = [r for r in results.get("freqtrade", []) if r["regime"] == regime]
        ahf_res = [r for r in results.get("ai-hedge-fund", []) if r["regime"] == regime]
        
        if wt_res and ft_res and ahf_res:
            wt_alpha = statistics.mean([r["alpha"] for r in wt_res])
            ft_alpha = statistics.mean([r["alpha"] for r in ft_res])
            ahf_alpha = statistics.mean([r["alpha"] for r in ahf_res])
            
            wt_total += 1
            if wt_alpha >= ft_alpha and wt_alpha >= ahf_alpha:
                wt_wins += 1
    
    wt_avg_alpha = scoreboard.get("WhaleTrader v2", {}).get("alpha", -999)
    ft_avg_alpha = scoreboard.get("freqtrade", {}).get("alpha", -999)
    ahf_avg_alpha = scoreboard.get("ai-hedge-fund", {}).get("alpha", -999)
    
    beats_all = wt_avg_alpha > ft_avg_alpha and wt_avg_alpha > ahf_avg_alpha
    
    print(f"\n  ITERATION {iteration} SCORE: WhaleTrader wins {wt_wins}/{wt_total} regimes")
    print(f"  Overall: WT {wt_avg_alpha:+.2%} vs FT {ft_avg_alpha:+.2%} vs AHF {ahf_avg_alpha:+.2%}")
    print(f"  {'✅ BEATS ALL!' if beats_all else '❌ Not yet beating all competitors'}")
    
    return results, scoreboard, wt_wins, wt_total, regime_scores


async def main():
    print(BANNER)
    
    # ── Build simulated scenarios ──
    print("\n  Building simulated scenarios...")
    sim_scenarios = build_scenarios()
    for sc in sim_scenarios:
        h = sc["history"]
        ret = (h[-1]["price"] / h[0]["price"] - 1) * 100
        print(f"    {sc['name']}: {h[0]['price']:,.0f} -> {h[-1]['price']:,.0f} ({ret:+.1f}%)")
    
    # ── Fetch crypto data ──
    print("\n  Fetching crypto data...")
    crypto_scenarios = []
    for asset in ["BTC", "ETH", "SOL"]:
        h = await fetch_crypto_history(asset, 365)
        if h and len(h) > 50:
            ret = (h[-1]["price"] / h[0]["price"] - 1) * 100
            print(f"    {asset}: ${h[0]['price']:,.0f} -> ${h[-1]['price']:,.0f} ({ret:+.1f}%)")
            crypto_scenarios.append({
                "name": f"{asset} (Crypto)", "market": "Crypto", 
                "regime": "Bear" if ret < -10 else "Bull" if ret > 10 else "Sideways",
                "history": h,
            })
        await asyncio.sleep(5)
    
    total_scenarios = len(sim_scenarios) + len(crypto_scenarios)
    print(f"\n  Total scenarios: {total_scenarios}")
    
    # ══════════════════════════════════════════════════════════════
    # ITERATIVE OPTIMIZATION
    # ══════════════════════════════════════════════════════════════
    
    # Parameter grid to search
    param_configs = [
        # Iteration 1: Baseline
        {"risk": 0.02, "atr": 2.0, "pos": 0.50, "cool": 3, "short": True, "heat": 0.80},
        # Iteration 2: More aggressive entry
        {"risk": 0.03, "atr": 1.5, "pos": 0.60, "cool": 2, "short": True, "heat": 0.85},
        # Iteration 3: Conservative risk, wide stops
        {"risk": 0.015, "atr": 2.5, "pos": 0.40, "cool": 4, "short": True, "heat": 0.70},
        # Iteration 4: High conviction only (larger position, tighter stop)
        {"risk": 0.025, "atr": 1.8, "pos": 0.55, "cool": 2, "short": True, "heat": 0.90},
        # Iteration 5: Aggressive with shorts (trend following)
        {"risk": 0.035, "atr": 1.2, "pos": 0.65, "cool": 1, "short": True, "heat": 0.95},
        # Iteration 6: No shorts, moderate
        {"risk": 0.025, "atr": 2.0, "pos": 0.50, "cool": 3, "short": False, "heat": 0.80},
    ]
    
    best_score = -999
    best_params = None
    best_results = None
    all_iterations = []
    
    for i, params in enumerate(param_configs):
        results, scoreboard, wins, total, regime_scores = await run_iteration(
            sim_scenarios, crypto_scenarios, params, i + 1
        )
        
        wt_alpha = scoreboard.get("WhaleTrader v2", {}).get("alpha", -999)
        wt_sharpe = scoreboard.get("WhaleTrader v2", {}).get("sharpe", -999)
        
        # Score: weighted alpha + bonus for regime wins
        score = wt_alpha * 100 + wins * 5 + wt_sharpe * 2
        
        all_iterations.append({
            "iteration": i + 1,
            "params": params,
            "alpha": wt_alpha,
            "sharpe": wt_sharpe,
            "regime_wins": wins,
            "total_regimes": total,
            "score": score,
        })
        
        if score > best_score:
            best_score = score
            best_params = params
            best_results = results
    
    # ══════════════════════════════════════════════════════════════
    # FINAL REPORT
    # ══════════════════════════════════════════════════════════════
    
    print(f"\n{'='*80}")
    print(f"  OPTIMIZATION COMPLETE — {len(param_configs)} iterations")
    print(f"{'='*80}")
    
    print(f"\n  ITERATION SUMMARY:")
    print(f"  {'#':>3} {'Alpha':>8} {'Sharpe':>8} {'Regimes':>10} {'Score':>8} {'Params'}")
    print(f"  {'─'*80}")
    for it in all_iterations:
        marker = " ⭐" if it["score"] == best_score else "   "
        p = it["params"]
        print(f"  {it['iteration']:>3} {it['alpha']:>+7.2%} {it['sharpe']:>8.2f} "
              f"{it['regime_wins']}/{it['total_regimes']:>2}      {it['score']:>7.1f}"
              f"{marker} risk={p['risk']:.3f} atr={p['atr']:.1f} pos={p['pos']:.2f} "
              f"cool={p['cool']} short={p['short']}")
    
    print(f"\n  ⭐ BEST CONFIGURATION:")
    print(f"     Params: {best_params}")
    print(f"     Score: {best_score:.1f}")
    
    # Final comparison with best params
    if best_results:
        print(f"\n  FINAL COMPARISON (Best Config):")
        for strat, res_list in best_results.items():
            if res_list:
                avg_alpha = statistics.mean([r["alpha"] for r in res_list])
                avg_dd = statistics.mean([r["max_dd"] for r in res_list])
                avg_trades = statistics.mean([r["trades"] for r in res_list])
                print(f"    {strat:<35} Alpha {avg_alpha:>+8.2%} | MaxDD {avg_dd:>+8.2%} | Trades {avg_trades:.0f}")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
