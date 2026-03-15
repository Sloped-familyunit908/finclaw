"""Quick test: all 8 strategies on US market"""
import asyncio, sys, os, logging, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

from whaletrader import scan_universe, run_strategy, UNIVERSES, STRATEGIES

async def test_all():
    print("Testing all 8 strategies on US market (1y)...")
    data = await scan_universe(UNIVERSES["us"], "1y", 1000000)
    print(f"{len(data)} stocks scanned.\n")

    for style in STRATEGIES:
        try:
            result = await run_strategy(style, data, 1000000)
            if result:
                n = len(result["holdings"])
                ret = result["total_ret"]
                ann = result["ann_ret"]
                print(f"  {style:<18} ret={ret:>+7.1%} ann={ann:>+6.1%}/y  {n} stocks  OK")
            else:
                print(f"  {style:<18} NO STOCKS SELECTED")
        except Exception as e:
            print(f"  {style:<18} ERROR: {e}")

asyncio.run(test_all())
