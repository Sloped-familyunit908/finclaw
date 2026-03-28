"""
FinClaw MCP Server — Model Context Protocol Integration
=========================================================
Allows any AI assistant (Claude, GPT, Gemini) to call FinClaw
via the MCP protocol.

Tools exposed:
  - finclaw_scan: Scan market with strategy
  - finclaw_backtest: Backtest a single ticker
  - finclaw_macro: Get current macro environment
  - finclaw_info: List available strategies
"""
import asyncio
import json
import sys
import os
import logging
import warnings

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_project_dir = os.path.dirname(_scripts_dir)
sys.path.insert(0, _project_dir)

# Import from legacy CLI module (scripts/finclaw.py)
# Use importlib to avoid name collision with the finclaw package
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "finclaw_cli", os.path.join(_scripts_dir, "finclaw.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

scan_universe = _mod.scan_universe
run_strategy = _mod.run_strategy
fetch_data = _mod.fetch_data
_load_universes = _mod._load_universes
STRATEGIES = _mod.STRATEGIES
UNIVERSES = _load_universes()
from agents.backtester_v7 import BacktesterV7
from agents.deep_macro import DeepMacroAnalyzer


async def handle_scan(market="us", style="soros", capital=1000000, period="1y"):
    """Scan a market with a strategy. Returns JSON with picks and performance."""
    if market == "all":
        markets = ["us", "china", "hk"]
    else:
        markets = [market]

    all_results = []
    for mkt in markets:
        if mkt not in UNIVERSES:
            continue
        data = await scan_universe(UNIVERSES[mkt], period, capital)
        result = await run_strategy(style, data, capital)
        if result:
            all_results.append({
                "market": mkt,
                "strategy": style,
                "total_return": round(result["total_ret"] * 100, 1),
                "annual_return": round(result["ann_ret"] * 100, 1),
                "pnl": round(result["pnl"]),
                "final_value": round(capital + result["pnl"]),
                "holdings": [
                    {
                        "ticker": h["ticker"],
                        "name": h["name"],
                        "allocation": round(h["alloc"] * 100),
                        "return": round(h["wt_ret"] * 100, 1),
                        "pnl": round(h["pnl"]),
                    }
                    for h in result["holdings"]
                ],
            })

    return all_results


async def handle_backtest(ticker, period="1y", capital=100000):
    """Backtest a single ticker. Returns JSON with performance metrics."""
    h = fetch_data(ticker, period)
    if not h:
        return {"error": f"No data for {ticker}"}

    bh = h[-1]["price"] / h[0]["price"] - 1
    years = len(h) / 252

    bt = BacktesterV7(initial_capital=capital)
    r = await bt.run(ticker, "v7", h)
    ann = (1 + r.total_return) ** (1 / years) - 1 if r.total_return > -1 else -1

    return {
        "ticker": ticker,
        "period": period,
        "years": round(years, 1),
        "buy_and_hold": round(bh * 100, 1),
        "finclaw_return": round(r.total_return * 100, 1),
        "annual_return": round(ann * 100, 1),
        "alpha": round((r.total_return - bh) * 100, 1),
        "max_drawdown": round(r.max_drawdown * 100, 1),
        "total_trades": r.total_trades,
        "win_rate": round(r.win_rate * 100),
        "pnl": round(capital * r.total_return),
        "final_value": round(capital * (1 + r.total_return)),
    }


def handle_macro():
    """Get current macro environment. Returns JSON."""
    dm = DeepMacroAnalyzer()
    snap = dm.analyze()

    favored = sorted(snap.sector_adjustments.items(), key=lambda x: x[1], reverse=True)

    return {
        "overall_regime": snap.overall_regime,
        "confidence": round(snap.confidence * 100),
        "sentiment": {
            "vix": round(snap.vix, 1),
            "vix_regime": snap.vix_regime,
            "bitcoin": snap.btc_trend,
            "bitcoin_risk_signal": snap.btc_as_risk,
        },
        "monetary": {
            "us_10y_yield": round(snap.us_10y, 2),
            "yield_curve": snap.yield_curve,
            "rate_direction": snap.rate_direction,
        },
        "commodities": {
            "oil": snap.oil_trend,
            "gold": snap.gold_trend,
            "copper": snap.copper_trend,
            "cycle": snap.commodity_cycle,
        },
        "currency": {
            "dxy": snap.dxy_trend,
            "dollar_regime": snap.dollar_regime,
            "usd_cny": snap.usdcny_trend,
            "usd_jpy": snap.usdjpy_trend,
        },
        "economy": {
            "phase": snap.economic_phase.value,
            "sp500": snap.sp500_trend,
            "small_vs_large": snap.russell_vs_sp,
        },
        "kondratieff": {
            "season": snap.kondratieff.value,
            "interpretation": "AI technology boom phase",
        },
        "favored_sectors": [
            {"sector": s, "adjustment": round(v, 3)}
            for s, v in favored[:7] if v > 0
        ],
        "avoided_sectors": [
            {"sector": s, "adjustment": round(v, 3)}
            for s, v in favored if v < -0.01
        ],
    }


def handle_info():
    """List available strategies and markets."""
    return {
        "strategies": {
            name: {
                "description": s["desc"],
                "risk": s["risk"],
                "target_annual": s["target_ann"],
            }
            for name, s in STRATEGIES.items()
        },
        "markets": {
            "us": {"stocks": len(UNIVERSES["us"]), "description": "US stocks (NASDAQ/NYSE)"},
            "china": {"stocks": len(UNIVERSES["china"]), "description": "China A-shares (Shanghai/Shenzhen)"},
            "hk": {"stocks": len(UNIVERSES["hk"]), "description": "Hong Kong stocks (HKEX)"},
        },
    }


# ═══ CLI mode for testing ═══
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="FinClaw MCP Server")
    parser.add_argument("tool", choices=["scan", "backtest", "macro", "info"])
    parser.add_argument("--market", "-m", default="us")
    parser.add_argument("--style", "-s", default="soros")
    parser.add_argument("--ticker", "-t", default="NVDA")
    parser.add_argument("--period", "-p", default="1y")
    parser.add_argument("--capital", "-c", type=float, default=100000)
    args = parser.parse_args()

    if args.tool == "scan":
        result = await handle_scan(args.market, args.style, args.capital, args.period)
    elif args.tool == "backtest":
        result = await handle_backtest(args.ticker, args.period, args.capital)
    elif args.tool == "macro":
        result = handle_macro()
    elif args.tool == "info":
        result = handle_info()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
