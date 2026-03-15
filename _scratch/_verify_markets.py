"""Verify all markets"""
import asyncio, sys, os, logging, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
from whaletrader import scan_universe, run_strategy, UNIVERSES, STRATEGIES

async def test():
    for market in ["us", "china", "hk"]:
        print(f"\n--- {market.upper()} ---")
        data = await scan_universe(UNIVERSES[market], "1y", 1000000)
        print(f"  {len(data)} stocks")
        result = await run_strategy("soros", data, 1000000)
        if result:
            print(f"  soros: {result['total_ret']:+.1%} ({len(result['holdings'])} stocks)")
        result2 = await run_strategy("conservative", data, 1000000)
        if result2:
            print(f"  conservative: {result2['total_ret']:+.1%} ({len(result2['holdings'])} stocks)")

asyncio.run(test())
