"""
WhaleTrader - Backtest Runner
Run multi-strategy backtesting with real historical data.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.backtester import Backtester, compare_strategies
from agents.debate_arena import DebateArena
from agents.registry import get_agent


BANNER = r"""
 __      ___         _     _____              _
 \ \    / / |_  __ _| |___|_   _| _ __ _ __| |___ _ _
  \ \/\/ /| ' \/ _` | / -_) | || '_/ _` / _` / -_) '_|
   \_/\_/ |_||_\__,_|_\___| |_||_| \__,_\__,_\___|_|

   BACKTESTING ENGINE v0.1.0
   Multi-Strategy | Multi-Agent | Debate-Verified
"""


async def fetch_history_for_backtest(asset: str, days: int = 200) -> list[dict]:
    """Fetch historical price data for backtesting"""
    import aiohttp
    
    symbol_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "ADA": "cardano",
        "DOT": "polkadot",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "MATIC": "matic-network",
    }
    
    coin_id = symbol_map.get(asset.upper(), asset.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise Exception(f"CoinGecko API error: {resp.status}")
            data = await resp.json()
    
    # Convert to price history format
    history = []
    for ts, price in data.get("prices", []):
        from datetime import datetime
        dt = datetime.fromtimestamp(ts / 1000)
        history.append({
            "date": dt,
            "price": price,
        })
    
    # Add volume data
    volumes = data.get("total_volumes", [])
    for i, (ts, vol) in enumerate(volumes):
        if i < len(history):
            history[i]["volume"] = vol
    
    return history


async def run_backtest_suite():
    """Run comprehensive backtesting"""
    print(BANNER)
    
    backtester = Backtester(
        initial_capital=10000.0,
        commission_pct=0.001,
        slippage_pct=0.0005,
    )
    
    assets = ["BTC", "ETH", "SOL"]
    all_results = []
    
    for asset in assets:
        print(f"\n{'='*65}")
        print(f"  Fetching {asset} historical data (200 days)...")
        
        try:
            history = await fetch_history_for_backtest(asset, days=200)
            print(f"  Got {len(history)} data points")
            print(f"  First: {history[0]['date'].strftime('%Y-%m-%d')} @ ${history[0]['price']:,.2f}")
            print(f"  Last:  {history[-1]['date'].strftime('%Y-%m-%d')} @ ${history[-1]['price']:,.2f}")
        except Exception as e:
            print(f"  Error fetching data: {e}")
            continue

        # ── Strategy 1: Simple RSI (no AI) ──
        print(f"\n  Running Strategy 1: RSI Only (baseline)...")
        result1 = await backtester.run(
            asset=asset,
            strategy_name=f"RSI-Only ({asset})",
            price_history=history,
            decision_interval=1,
        )
        all_results.append(result1)
        print(f"  → Return: {result1.total_return:+.2%} | Sharpe: {result1.sharpe_ratio:.2f} | Trades: {result1.total_trades}")

        # ── Strategy 2: 2-Agent Debate (Value + Quant) ──
        print(f"\n  Running Strategy 2: 2-Agent Debate (Warren + Ada)...")
        arena2 = DebateArena(ai_client=None, max_rounds=1)
        agents2 = [get_agent("value"), get_agent("quant")]
        result2 = await backtester.run(
            asset=asset,
            strategy_name=f"2-Agent Debate ({asset})",
            price_history=history,
            arena=arena2,
            agents=agents2,
            decision_interval=1,
        )
        all_results.append(result2)
        print(f"  → Return: {result2.total_return:+.2%} | Sharpe: {result2.sharpe_ratio:.2f} | Trades: {result2.total_trades}")

        # ── Strategy 3: 3-Agent Debate (Value + Quant + Macro) ──
        print(f"\n  Running Strategy 3: 3-Agent Debate (Warren + Ada + George)...")
        arena3 = DebateArena(ai_client=None, max_rounds=2)
        agents3 = [get_agent("value"), get_agent("quant"), get_agent("macro")]
        result3 = await backtester.run(
            asset=asset,
            strategy_name=f"3-Agent Debate ({asset})",
            price_history=history,
            arena=arena3,
            agents=agents3,
            decision_interval=1,
        )
        all_results.append(result3)
        print(f"  → Return: {result3.total_return:+.2%} | Sharpe: {result3.sharpe_ratio:.2f} | Trades: {result3.total_trades}")

        # Rate limit
        await asyncio.sleep(2)

    # ── Print Comparison ──
    if all_results:
        comparison = await compare_strategies(backtester, all_results)
        print(comparison)

        # Print detailed report for the best strategy
        best = max(all_results, key=lambda r: r.sharpe_ratio)
        print(f"\n{'='*65}")
        print(f"  DETAILED REPORT — BEST STRATEGY")
        print(f"{'='*65}")
        print(best.summary())

    print(f"\n{'='*65}")
    print("  WhaleTrader backtesting complete.")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    asyncio.run(run_backtest_suite())
