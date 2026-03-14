"""
WhaleTrader - Advanced Backtest Suite
More strategies, more agents, reputation tracking, constitutional risk.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.backtester import Backtester, compare_strategies
from agents.debate_arena import DebateArena
from agents.registry import get_agent
from agents.memory import AgentMemory, MemoryManager
from agents.risk_constitution import ConstitutionalGuardian, RiskConstitution


BANNER = r"""
 __      ___         _     _____              _
 \ \    / / |_  __ _| |___|_   _| _ __ _ __| |___ _ _
  \ \/\/ /| ' \/ _` | / -_) | || '_/ _` / _` / -_) '_|
   \_/\_/ |_||_\__,_|_\___| |_||_| \__,_\__,_\___|_|

   ADVANCED BACKTEST SUITE v0.2.0
   Multi-Strategy | Agent Reputation | Constitutional Risk
"""


async def fetch_history(asset: str, days: int = 365) -> list[dict]:
    """Fetch historical data"""
    import aiohttp
    from datetime import datetime
    
    symbol_map = {
        "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
        "ADA": "cardano", "DOT": "polkadot", "AVAX": "avalanche-2",
        "LINK": "chainlink", "BNB": "binancecoin", "XRP": "ripple",
        "DOGE": "dogecoin",
    }
    
    coin_id = symbol_map.get(asset.upper(), asset.lower())
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": str(days)}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status == 429:
                print(f"  ⚠ Rate limited, waiting 30s...")
                await asyncio.sleep(30)
                async with session.get(url, params=params) as resp2:
                    data = await resp2.json()
            elif resp.status != 200:
                raise Exception(f"CoinGecko error: {resp.status}")
            else:
                data = await resp.json()
    
    history = []
    for ts, price in data.get("prices", []):
        dt = datetime.fromtimestamp(ts / 1000)
        history.append({"date": dt, "price": price})
    
    volumes = data.get("total_volumes", [])
    for i, (ts, vol) in enumerate(volumes):
        if i < len(history):
            history[i]["volume"] = vol
    
    return history


async def run_advanced_backtest():
    """Run comprehensive multi-strategy, multi-asset backtest"""
    print(BANNER)
    
    backtester = Backtester(
        initial_capital=10000.0,
        commission_pct=0.001,
        slippage_pct=0.0005,
    )
    
    # ── Strategy Configurations ──
    strategies = [
        {
            "name": "Baseline: RSI Only",
            "agents": None,
            "arena": None,
            "desc": "Simple RSI momentum — no AI",
        },
        {
            "name": "2-Agent: Value+Quant",
            "agents": ["value", "quant"],
            "rounds": 1,
            "desc": "Warren + Ada debate",
        },
        {
            "name": "3-Agent: V+Q+Macro",
            "agents": ["value", "quant", "macro"],
            "rounds": 2,
            "desc": "Warren + Ada + George",
        },
        {
            "name": "4-Agent: V+Q+M+Sentiment",
            "agents": ["value", "quant", "macro", "sentiment"],
            "rounds": 2,
            "desc": "Full team minus risk",
        },
        {
            "name": "5-Agent: Full Team",
            "agents": ["value", "quant", "macro", "sentiment", "risk"],
            "rounds": 2,
            "desc": "All agents including Guardian",
        },
    ]
    
    assets = ["BTC", "ETH", "SOL"]
    all_results = []
    memory_manager = MemoryManager()
    
    for asset in assets:
        print(f"\n{'='*65}")
        print(f"  📊 {asset} — Fetching 200-day history...")
        
        try:
            history = await fetch_history(asset, days=200)
            print(f"  Got {len(history)} data points")
            start_price = history[0]['price']
            end_price = history[-1]['price']
            hodl_return = (end_price / start_price - 1) * 100
            print(f"  {history[0]['date'].strftime('%Y-%m-%d')} ${start_price:,.0f} → "
                  f"{history[-1]['date'].strftime('%Y-%m-%d')} ${end_price:,.0f} "
                  f"(HODL: {hodl_return:+.1f}%)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

        for strat in strategies:
            name = f"{strat['name']} ({asset})"
            print(f"\n  Running: {name}...")
            
            arena = None
            agents = None
            
            if strat.get("agents"):
                agents = [get_agent(a) for a in strat["agents"]]
                arena = DebateArena(
                    ai_client=None,
                    max_rounds=strat.get("rounds", 1),
                )
            
            try:
                result = await backtester.run(
                    asset=asset,
                    strategy_name=name,
                    price_history=history,
                    arena=arena,
                    agents=agents,
                    decision_interval=1,
                )
                all_results.append(result)
                
                alpha = result.total_return - result.benchmark_return
                print(f"  → Return: {result.total_return:+.2%} | "
                      f"Alpha: {alpha:+.2%} | "
                      f"Sharpe: {result.sharpe_ratio:.2f} | "
                      f"MaxDD: {result.max_drawdown:.2%} | "
                      f"Trades: {result.total_trades}")
                
                # Update agent memories
                if agents:
                    for agent in agents:
                        memory = memory_manager.get_memory(agent.name)
                        for trade in result.trades:
                            memory.record_prediction(
                                asset=asset,
                                signal=trade.signal_source,
                                confidence=trade.debate_confidence,
                                price=trade.entry_price,
                            )
                            memory.resolve_prediction(
                                len(memory.predictions) - 1,
                                trade.exit_price,
                            )
            except Exception as e:
                print(f"  ❌ Error: {e}")

        # Rate limit
        print(f"\n  ⏳ Rate limit pause...")
        await asyncio.sleep(3)

    # ── Print Comparison ──
    if all_results:
        comparison = await compare_strategies(backtester, all_results)
        print(comparison)

        # ── Group by strategy type ──
        print(f"\n{'='*65}")
        print(f"  📈 STRATEGY EFFECTIVENESS (averaged across assets)")
        print(f"{'='*65}")
        
        strat_groups: dict[str, list] = {}
        for r in all_results:
            # Extract base strategy name (remove asset suffix)
            base = r.strategy_name.rsplit(" (", 1)[0]
            if base not in strat_groups:
                strat_groups[base] = []
            strat_groups[base].append(r)
        
        print(f"\n  {'Strategy':<30} {'Avg Return':>12} {'Avg Alpha':>12} {'Avg Sharpe':>12} {'Avg MaxDD':>12}")
        print(f"  {'-'*80}")
        
        for name, results in strat_groups.items():
            avg_ret = sum(r.total_return for r in results) / len(results)
            avg_alpha = sum(r.total_return - r.benchmark_return for r in results) / len(results)
            avg_sharpe = sum(r.sharpe_ratio for r in results) / len(results)
            avg_dd = sum(r.max_drawdown for r in results) / len(results)
            
            best = "🏆" if avg_alpha == max(
                sum(r.total_return - r.benchmark_return for r in g) / len(g)
                for g in strat_groups.values()
            ) else "  "
            
            print(f"  {best}{name:<28} {avg_ret:>+11.2%} {avg_alpha:>+11.2%} "
                  f"{avg_sharpe:>12.2f} {avg_dd:>12.2%}")

        # ── Agent Reputation ──
        print(f"\n{'='*65}")
        print(f"  🏅 AGENT REPUTATION AFTER BACKTEST")
        print(f"{'='*65}")
        for agent_name in ["Warren", "Ada", "George", "Sentinel", "Guardian"]:
            memory = memory_manager.get_memory(agent_name)
            if memory.total_predictions > 0:
                print(memory.get_reputation_card())

        # ── Constitutional Risk Report ──
        print(f"\n{'='*65}")
        print(f"  🛡️ CONSTITUTIONAL RISK FRAMEWORK")
        print(f"{'='*65}")
        constitution = RiskConstitution()
        guardian = ConstitutionalGuardian(constitution)
        
        # Simulate risk checks with actual backtest results
        best_result = max(all_results, key=lambda r: r.total_return - r.benchmark_return)
        guardian.peak_equity = 10000
        guardian.current_equity = 10000 * (1 + best_result.total_return)
        
        print(f"\n  Constitution Rules:")
        print(f"  • Max Position Size:    {constitution.max_position_pct:.0%}")
        print(f"  • Max Drawdown Halt:    {constitution.max_drawdown_halt:.0%}")
        print(f"  • Max Daily Loss:       {constitution.max_daily_loss:.0%}")
        print(f"  • Min Debate Confidence: {constitution.min_debate_confidence:.0%}")
        print(f"  • Min Agents Agreeing:  {constitution.min_agents_agreeing}")
        print(f"  • Max Leverage:         {constitution.max_leverage:.0f}x")
        print(f"  • Required Risk/Reward: {constitution.required_risk_reward:.1f}:1")
        
        # Test risk checks
        print(f"\n  Simulated Risk Checks:")
        
        check1 = guardian.check_trade("buy", 0.95, 0.20, 10000, 3)
        print(f"  BUY  95% conf, 20% size, 3 agents → {check1.explanation}")
        
        check2 = guardian.check_trade("buy", 0.40, 0.15, 10000, 1)
        print(f"  BUY  40% conf, 15% size, 1 agent  → {check2.explanation}")
        
        check3 = guardian.check_trade("sell", 0.70, 0.30, 10000, 2)
        print(f"  SELL 70% conf, 30% size, 2 agents → {check3.explanation}")

    print(f"\n{'='*65}")
    print("  WhaleTrader Advanced Backtest Suite complete.")
    print(f"  Tested {len(strategies)} strategies × {len(assets)} assets = {len(all_results)} runs")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    asyncio.run(run_advanced_backtest())
