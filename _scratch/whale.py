"""
WhaleTrader - Python CLI
Complete working demo with real data + debate arena.
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.prices import build_market_data
from agents.registry import get_agent, list_agents
from agents.debate_arena import DebateArena


BANNER = r"""
 __      ___         _     _____              _
 \ \    / / |_  __ _| |___|_   _| _ __ _ __| |___ _ _
  \ \/\/ /| ' \/ _` | / -_) | || '_/ _` / _` / -_) '_|
   \_/\_/ |_||_\__,_|_\___| |_||_| \__,_\__,_\___|_|

   AI-Powered Quantitative Trading Engine v0.1.0
   Rust Engine | Python Strategies | TypeScript Dashboard
"""


def print_header(text, char="=", width=65):
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}")


def print_statement(stmt):
    """Pretty-print a debate statement"""
    phase_icons = {
        "analysis": "analyze",
        "position": "position",
        "challenge": "challenge",
        "defense": "defense",
        "consensus": "verdict",
    }
    
    signal_colors = {
        "strong_buy": "STRONG BUY",
        "buy": "BUY",
        "hold": "HOLD",
        "sell": "SELL",
        "strong_sell": "STRONG SELL",
    }

    signal_display = signal_colors.get(stmt.signal, stmt.signal.upper())
    phase_display = phase_icons.get(stmt.phase.value, stmt.phase.value)

    # Agent profile lookup for avatar
    agent_avatars = {
        "Warren": "old_man",
        "George": "globe",
        "Ada": "ruler",
        "Sentinel": "satellite",
        "Guardian": "shield",
        "Arena Moderator": "gavel",
    }

    print(f"\n  [{phase_display.upper()}] {stmt.agent_name} ({stmt.agent_role})")
    print(f"  Signal: {signal_display} | Confidence: {stmt.confidence:.0%}")
    if stmt.target_agent:
        print(f"  Responding to: {stmt.target_agent}")
    print(f"  ---")
    # Wrap content at ~70 chars
    words = stmt.content.split()
    line = "  "
    for word in words:
        if len(line) + len(word) > 72:
            print(line)
            line = "  " + word
        else:
            line += " " + word if line.strip() else "  " + word
    if line.strip():
        print(line)


async def run_analysis(asset: str, agent_names: list[str] = None):
    """Run a complete analysis with debate"""
    
    if agent_names is None:
        agent_names = ["value", "quant", "sentiment"]

    print_header(f"Analyzing {asset}", "=")

    # 1. Fetch real market data
    print("\n  Fetching live market data...")
    try:
        md = await build_market_data(asset)
        print(f"  Price:       ${md.current_price:,.2f}")
        print(f"  24h Change:  {md.change_24h:+.2%}")
        print(f"  7d Change:   {md.change_7d:+.2%}")
        print(f"  30d Change:  {md.change_30d:+.2%}")
        print(f"  Volume 24h:  ${md.volume_24h:,.0f}")
        if md.market_cap:
            print(f"  Market Cap:  ${md.market_cap:,.0f}")
        if md.rsi_14:
            print(f"  RSI(14):     {md.rsi_14:.1f}")
        if md.sma_20:
            print(f"  SMA(20):     ${md.sma_20:,.2f}")
        if md.sma_50:
            print(f"  SMA(50):     ${md.sma_50:,.2f}")
        if md.sma_200:
            print(f"  SMA(200):    ${md.sma_200:,.2f}")
    except Exception as e:
        print(f"  Failed to fetch data: {e}")
        return

    # 2. Prepare market data dict for agents
    market_dict = {
        "asset": asset,
        "price": md.current_price,
        "change_24h": f"{md.change_24h:+.2%}",
        "change_7d": f"{md.change_7d:+.2%}",
        "change_30d": f"{md.change_30d:+.2%}",
        "volume_24h": md.volume_24h,
        "market_cap": md.market_cap,
        "rsi_14": md.rsi_14,
        "sma_20": md.sma_20,
        "sma_50": md.sma_50,
        "sma_200": md.sma_200,
        "macd": md.macd,
        "bollinger_upper": md.bollinger_upper,
        "bollinger_lower": md.bollinger_lower,
    }

    # 3. Load agents
    agents = [get_agent(name) for name in agent_names]
    print(f"\n  Agents loaded: {', '.join(a.name for a in agents)}")

    # 4. Run Debate Arena
    print_header("DEBATE ARENA", "*")
    print("  AI agents are debating their positions...\n")

    arena = DebateArena(ai_client=None, max_rounds=2)

    async def on_statement(stmt):
        """Real-time callback for each debate statement"""
        print_statement(stmt)

    result = await arena.run_debate(
        asset=asset,
        agents=agents,
        market_data=market_dict,
        on_statement=on_statement,
    )

    # 5. Show Final Result
    print_header("CONSENSUS DECISION", "#")
    print(f"\n  Asset:       {result.asset}")
    print(f"  Signal:      {result.final_signal.upper()}")
    print(f"  Confidence:  {result.final_confidence:.0%}")
    print(f"  Agents:      {', '.join(result.participating_agents)}")
    if result.dissenting_agents:
        print(f"  Dissenters:  {', '.join(result.dissenting_agents)}")
    print(f"  Debate Time: {result.duration_ms:.0f}ms")
    print(f"\n  Reasoning:")
    print(f"  {result.consensus_reasoning}")

    return result


async def main():
    print(BANNER)

    assets = ["BTC", "ETH", "SOL"]
    agent_roster = ["value", "quant"]  # Start with 2 agents for demo

    all_results = []

    for asset in assets:
        try:
            result = await run_analysis(asset, agent_roster)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"\n  Error analyzing {asset}: {e}")

        # Small delay between API calls (CoinGecko rate limit)
        await asyncio.sleep(1.5)

    # Summary
    if all_results:
        print_header("PORTFOLIO SIGNALS SUMMARY", "=")
        print(f"\n  {'Asset':<8} {'Signal':<14} {'Confidence':<12} {'Dissenters'}")
        print(f"  {'-'*50}")
        for r in all_results:
            dissenters = ', '.join(r.dissenting_agents) if r.dissenting_agents else 'None'
            print(f"  {r.asset:<8} {r.final_signal.upper():<14} {r.final_confidence:<12.0%} {dissenters}")

    print(f"\n{'='*65}")
    print("  WhaleTrader analysis complete. Built with Lobster Labs")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    asyncio.run(main())
