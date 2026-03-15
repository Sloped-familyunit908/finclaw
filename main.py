"""
FinClaw - Main Entry Point
"""

import asyncio
import argparse
import json
from datetime import datetime

from src.data.prices import build_market_data
from src.agents.value import ValueAgent
from src.agents.momentum import MomentumAgent
from src.exchange.paper import PaperTradingEngine, OrderSide


BANNER = """
╦ ╦╦ ╦╔═╗╦  ╔═╗╔╦╗╦═╗╔═╗╔╦╗╔═╗╦═╗
║║║╠═╣╠═╣║  ║╣  ║ ╠╦╝╠═╣ ║║║╣ ╠╦╝
╚╩╝╩ ╩╩ ╩╩═╝╚═╝ ╩ ╩╚═╩ ╩═╩╝╚═╝╩╚═
    AI-Powered Quantitative Trading Engine
    Built with 🦞 by Lobster Labs
"""


async def analyze_asset(asset: str, agents: list, verbose: bool = True):
    """Run all agents on a single asset"""
    print(f"\n{'='*60}")
    print(f"📊 Analyzing {asset}...")
    print(f"{'='*60}")

    # 1. Fetch market data
    print(f"\n📡 Fetching market data for {asset}...")
    try:
        market_data = await build_market_data(asset)
        print(f"   Price: ${market_data.current_price:,.2f}")
        print(f"   24h:   {market_data.change_24h:+.2%}")
        print(f"   7d:    {market_data.change_7d:+.2%}")
        print(f"   30d:   {market_data.change_30d:+.2%}")
        if market_data.rsi_14:
            print(f"   RSI:   {market_data.rsi_14:.1f}")
    except Exception as e:
        print(f"   ❌ Failed to fetch data: {e}")
        return None

    # 2. Run all agents in parallel
    print(f"\n🤖 Running {len(agents)} agents...")
    analyses = []
    for agent in agents:
        try:
            print(f"   🔄 {agent.name} analyzing...")
            analysis = await agent.analyze(asset, market_data)
            analyses.append(analysis)
            print(f"   ✅ {agent.name}: {analysis.signal.value.upper()} "
                  f"(confidence: {analysis.confidence:.0%})")
        except Exception as e:
            print(f"   ❌ {agent.name} failed: {e}")

    # 3. Debate Arena
    if len(analyses) > 1:
        print(f"\n🏟️  Debate Arena")
        print(f"{'─'*40}")
        for analysis in analyses:
            other_analyses = [a for a in analyses if a.agent_name != analysis.agent_name]
            try:
                debate_response = await analysis.agent_name  # placeholder
                if verbose:
                    print(f"\n{analysis.agent_name}:")
                    print(f"  {analysis.reasoning[:200]}...")
            except:
                pass

    # 4. Consensus
    if analyses:
        signal_weights = {
            "strong_buy": 2, "buy": 1, "hold": 0, "sell": -1, "strong_sell": -2
        }
        weighted_score = sum(
            signal_weights[a.signal.value] * a.confidence
            for a in analyses
        )
        avg_confidence = sum(a.confidence for a in analyses) / len(analyses)

        print(f"\n📋 Consensus")
        print(f"{'─'*40}")
        print(f"   Weighted Score: {weighted_score:+.2f}")
        print(f"   Avg Confidence: {avg_confidence:.0%}")

        if weighted_score > 1:
            consensus = "STRONG BUY 🟢🟢"
        elif weighted_score > 0.3:
            consensus = "BUY 🟢"
        elif weighted_score > -0.3:
            consensus = "HOLD 🟡"
        elif weighted_score > -1:
            consensus = "SELL 🔴"
        else:
            consensus = "STRONG SELL 🔴🔴"

        print(f"   Decision: {consensus}")

    return analyses


async def main():
    parser = argparse.ArgumentParser(description="FinClaw - AI Trading Engine")
    parser.add_argument("--assets", type=str, default="BTC,ETH,SOL",
                        help="Comma-separated asset symbols")
    parser.add_argument("--mode", type=str, default="paper",
                        choices=["paper", "live", "backtest"],
                        help="Trading mode")
    parser.add_argument("--capital", type=float, default=10000,
                        help="Initial capital for paper trading")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start web dashboard")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Verbose output")

    args = parser.parse_args()

    print(BANNER)
    print(f"Mode: {args.mode.upper()}")
    print(f"Assets: {args.assets}")
    print(f"Capital: ${args.capital:,.2f}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize agents (AI client will be configured later)
    agents = [
        ValueAgent(ai_client=None),
        MomentumAgent(ai_client=None),
    ]
    print(f"\nAgents loaded: {', '.join(a.name for a in agents)}")

    # Initialize paper trading engine
    engine = PaperTradingEngine(initial_capital=args.capital)
    print(f"Trading engine: {engine}")

    # Analyze each asset
    assets = [a.strip().upper() for a in args.assets.split(",")]

    for asset in assets:
        await analyze_asset(asset, agents, verbose=args.verbose)

    # Show portfolio summary
    print(f"\n{'='*60}")
    print(f"💼 Portfolio Summary")
    print(f"{'='*60}")
    summary = engine.get_portfolio_summary()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
