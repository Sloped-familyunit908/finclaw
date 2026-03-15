"""Test MCP server endpoints"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging, warnings
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

from mcp_server import handle_scan, handle_backtest, handle_macro, handle_info

class R:
    def __init__(self): self.p=0;self.f=0;self.e=[]
    def ok(self,n): self.p+=1;print(f"  [PASS] {n}")
    def fail(self,n,m): self.f+=1;self.e.append(f"{n}:{m}");print(f"  [FAIL] {n}:{m}")

async def main():
    r = R()
    print("="*60)
    print("  FinClaw MCP Server Tests")
    print("="*60)

    # info
    print("\n--- info ---")
    result = handle_info()
    if "strategies" in result and len(result["strategies"]) == 8:
        r.ok("info has 8 strategies")
    else:
        r.fail("info", "missing strategies")
    if "markets" in result and len(result["markets"]) == 3:
        r.ok("info has 3 markets")
    else:
        r.fail("info", "missing markets")

    # macro
    print("\n--- macro ---")
    result = handle_macro()
    checks = ["overall_regime","sentiment","monetary","commodities","currency","economy","kondratieff","favored_sectors"]
    for c in checks:
        if c in result:
            r.ok(f"macro has {c}")
        else:
            r.fail(f"macro", f"missing {c}")
    if result["sentiment"]["vix"] > 0:
        r.ok(f"macro vix={result['sentiment']['vix']}")
    else:
        r.fail("macro vix", "invalid")

    # backtest
    print("\n--- backtest ---")
    result = await handle_backtest("AAPL", "1y")
    if "error" not in result:
        for field in ["ticker","finclaw_return","alpha","max_drawdown","total_trades","win_rate"]:
            if field in result:
                r.ok(f"backtest has {field}")
            else:
                r.fail(f"backtest", f"missing {field}")
    else:
        r.fail("backtest", result["error"])

    # backtest bad ticker
    result = await handle_backtest("ZZZZZ_FAKE", "1y")
    if "error" in result:
        r.ok("backtest bad ticker returns error")
    else:
        r.fail("backtest bad ticker", "should return error")

    # scan
    print("\n--- scan ---")
    result = await handle_scan("us", "conservative", 100000, "1y")
    if result and len(result) > 0:
        r.ok(f"scan returned {len(result)} market(s)")
        if "holdings" in result[0] and len(result[0]["holdings"]) > 0:
            r.ok(f"scan has {len(result[0]['holdings'])} holdings")
            h = result[0]["holdings"][0]
            for field in ["ticker","name","allocation","return","pnl"]:
                if field in h:
                    r.ok(f"holding has {field}")
                else:
                    r.fail(f"holding", f"missing {field}")
        else:
            r.fail("scan", "no holdings")
    else:
        r.fail("scan", "empty result")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {r.p} passed, {r.f} failed")
    print(f"{'='*60}")
    if r.e:
        for e in r.e: print(f"  - {e}")
        return 1
    print("\nALL MCP TESTS PASSED!")
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
