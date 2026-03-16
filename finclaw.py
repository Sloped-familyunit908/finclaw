#!/usr/bin/env python3
"""
FinClaw CLI - AI-Powered Financial Intelligence Engine
======================================================
Usage:
  finclaw scan --market us --style soros
  finclaw backtest --strategy momentum --ticker AAPL --start 2020-01-01 --end 2025-01-01
  finclaw signal --ticker MSFT --strategy mean_reversion
  finclaw optimize --strategy momentum --param-grid params.json --data AAPL
  finclaw report --input backtest_results.json --format html
  finclaw portfolio --tickers AAPL,MSFT,GOOGL --method risk_parity
  finclaw cache --stats
  finclaw info
"""
import asyncio, argparse, json, math, sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import FinClawConfig, ConfigValidationError

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance"); sys.exit(1)


# ═══ Lazy imports to keep startup fast ═══

def _load_backtester():
    from agents.backtester_v7 import BacktesterV7
    return BacktesterV7

def _load_selector():
    from agents.signal_engine_v9 import AssetSelector, AssetGrade
    return AssetSelector, AssetGrade

def _load_universes():
    from agents.universe import US_EXTENDED, A_SHARES_EXTENDED, HK_EXTENDED
    return {
        "us": US_EXTENDED,
        "china": A_SHARES_EXTENDED,
        "hk": HK_EXTENDED,
        "japan": {
            "7203.T": "Toyota", "6758.T": "Sony",
            "9984.T": "SoftBank", "6861.T": "Keyence",
            "8306.T": "MUFG", "6501.T": "Hitachi",
            "6902.T": "Denso", "7741.T": "HOYA",
        },
        "korea": {
            "005930.KS": "Samsung", "000660.KS": "SK Hynix",
            "373220.KS": "LG Energy", "005380.KS": "Hyundai",
            "051910.KS": "LG Chem", "207940.KS": "Samsung Bio",
        },
    }


# ═══ STRATEGY PRESETS ═══
STRATEGIES = {
    "druckenmiller": {"desc": "Top-3 momentum, max conviction", "risk": "VERY HIGH", "target_ann": "20-35%",
        "select": lambda data: sorted(data, key=lambda x: x.get("recent_1y",0), reverse=True)[:3], "alloc": "equal"},
    "soros": {"desc": "AI narrative + momentum, top-5", "risk": "HIGH", "target_ann": "25-30%",
        "select": lambda data: sorted([d for d in data if d.get("wt_ann",0)>0.10], key=lambda x: x.get("wt_ann",0), reverse=True)[:5] or sorted(data, key=lambda x: x.get("wt_ann",0), reverse=True)[:5], "alloc": "equal"},
    "lynch": {"desc": "High growth/vol ratio, top-6", "risk": "HIGH", "target_ann": "20-27%",
        "select": lambda data: sorted(data, key=lambda x: max(x.get("cagr_3y",0),0)/max(x.get("ann_vol",0.1),0.1), reverse=True)[:6], "alloc": "equal"},
    "buffett": {"desc": "Quality + dip recovery, top-8", "risk": "MEDIUM-HIGH", "target_ann": "20-30%",
        "select": lambda data: sorted(data, key=lambda x: x.get("cagr_3y",0)*0.4+(1-min(x.get("ann_vol",0.3),1))*0.3+max(-x.get("max_dd_peak",0)-0.2,0)*0.6, reverse=True)[:8], "alloc": "equal"},
    "dalio": {"desc": "All-weather, low corr, risk parity", "risk": "MEDIUM", "target_ann": "15-20%",
        "select": lambda data: sorted(data, key=lambda x: x.get("composite",0), reverse=True)[:12], "alloc": "risk_parity"},
    "momentum": {"desc": "Top-5 by momentum score", "risk": "HIGH", "target_ann": "20-30%",
        "select": lambda data: sorted(data, key=lambda x: x.get("recent_1y",0)*0.5+x.get("wt_ann",0)*0.5, reverse=True)[:5], "alloc": "equal"},
    "mean_reversion": {"desc": "Buy dips, mean reversion plays", "risk": "MEDIUM", "target_ann": "12-18%",
        "select": lambda data: sorted(data, key=lambda x: -x.get("recent_1y",0)+x.get("cagr_3y",0), reverse=True)[:8], "alloc": "equal"},
    "aggressive": {"desc": "Top-5 by WT return", "risk": "HIGH", "target_ann": "25-35%",
        "select": lambda data: sorted(data, key=lambda x: x.get("wt_ann",0), reverse=True)[:5], "alloc": "equal"},
    "balanced": {"desc": "Top-10 grade-weighted", "risk": "MEDIUM", "target_ann": "10-15%",
        "select": lambda data: sorted(data, key=lambda x: x.get("composite",0), reverse=True)[:10], "alloc": "grade"},
    "conservative": {"desc": "Top-15 low-vol, safe", "risk": "LOW", "target_ann": "8-12%",
        "select": lambda data: sorted(data, key=lambda x: x.get("composite",0)*0.3+(1-min(x.get("ann_vol",0.3),1))*0.7, reverse=True)[:15], "alloc": "equal"},
}


class FinClawError(Exception):
    """User-facing error with friendly message."""
    pass


def fetch_data(ticker, period="5y"):
    """Fetch price data via yfinance with cache."""
    try:
        from src.pipeline.cache import DataCache
        cache = DataCache()
        cache_key = f"{ticker}_{period}"
        cached = cache.get(cache_key)
        if cached:
            return cached
    except Exception:
        cache = None

    try:
        import logging, warnings
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
        if df.empty or len(df) < 60:
            return None
        data = [{"date": idx.isoformat(), "price": float(row["Close"]),
                 "volume": float(row["Volume"])} for idx, row in df.iterrows()]
        if cache:
            cache.set(cache_key, data)
        return data
    except ConnectionError:
        print(f"  ERROR: Network error fetching {ticker}. Check your internet connection.")
        return None
    except Exception as e:
        print(f"  ERROR: Failed to fetch data for {ticker}: {e}")
        return None


def _parse_data_for_backtest(data: list[dict]) -> list[dict]:
    """Convert cached data dicts to have datetime dates."""
    result = []
    for d in data:
        entry = dict(d)
        if isinstance(entry.get("date"), str):
            try:
                entry["date"] = datetime.fromisoformat(entry["date"])
            except (ValueError, TypeError):
                pass
        result.append(entry)
    return result


async def scan_universe(tickers, period="5y", capital=1000000):
    """Scan and grade all stocks in a universe."""
    AssetSelector, AssetGrade = _load_selector()
    BacktesterV7 = _load_backtester()
    selector = AssetSelector()
    all_data = []

    for ticker, name in tickers.items():
        h = fetch_data(ticker, period)
        if not h:
            continue
        h = _parse_data_for_backtest(h)

        bh = h[-1]["price"] / h[0]["price"] - 1
        years = max(len(h) / 252, 0.5)

        bt = BacktesterV7(initial_capital=capital // 10)
        r = await bt.run(ticker, "v7", h)

        prices = [x["price"] for x in h]
        rets = [prices[i] / prices[i-1] - 1 for i in range(1, len(prices))]
        ann_vol = (sum((rv - sum(rets)/len(rets))**2 for rv in rets) / (len(rets)-1))**0.5 * math.sqrt(252) if len(rets) > 1 else 0.3

        peak = prices[0]; max_dd = 0
        for p in prices:
            peak = max(peak, p)
            max_dd = min(max_dd, (p - peak) / peak)

        recent_1y = prices[-1] / prices[max(0, len(prices)-252)] - 1 if len(prices) > 252 else bh / max(years, 1)
        cagr_3y = (prices[-1] / prices[max(0, len(prices)-756)])**(1/min(3, years)) - 1 if len(prices) > 100 else 0

        try:
            score = selector.score_asset(
                [x["price"] for x in h[:min(150, len(h))]],
                [x.get("volume", 0) for x in h[:min(150, len(h))]])
            grade = score.grade; composite = score.composite
        except Exception:
            grade = AssetGrade.C; composite = 0

        all_data.append({
            "ticker": ticker, "name": name, "h": h,
            "bh": bh, "wt_ret": r.total_return,
            "wt_ann": (1 + r.total_return)**(1/years) - 1 if r.total_return > -1 else -1,
            "wt_dd": r.max_drawdown, "years": years,
            "grade": grade, "composite": composite,
            "ann_vol": ann_vol, "max_dd_peak": max_dd,
            "recent_1y": recent_1y, "cagr_3y": cagr_3y,
        })

    return all_data


async def run_strategy(style, data, capital):
    """Run a preset strategy and return results."""
    _, AssetGrade = _load_selector()
    BacktesterV7 = _load_backtester()
    strat = STRATEGIES[style]
    pool = strat["select"](data)
    if not pool:
        return None

    GRADE_W = {AssetGrade.A_PLUS: 12, AssetGrade.A: 6, AssetGrade.B: 2,
               AssetGrade.C: 0.5, AssetGrade.F: 0.1}

    if strat["alloc"] == "grade":
        total_w = sum(GRADE_W.get(d["grade"], 1) for d in pool)
        for d in pool: d["alloc"] = GRADE_W.get(d["grade"], 1) / total_w
    elif strat["alloc"] == "risk_parity":
        for d in pool: d["rp_w"] = 1.0 / max(d["ann_vol"], 0.10)
        total_rp = sum(d["rp_w"] for d in pool)
        for d in pool: d["alloc"] = d["rp_w"] / total_rp
    else:
        for d in pool: d["alloc"] = 1.0 / len(pool)

    total_pnl = 0
    avg_years = sum(d["years"] for d in pool) / len(pool)
    results_detail = []

    for d in pool:
        cap = capital * d["alloc"]
        bt = BacktesterV7(initial_capital=cap)
        r = await bt.run(d["ticker"], "v7", d["h"])
        pnl = cap * r.total_return
        total_pnl += pnl
        results_detail.append({
            "ticker": d["ticker"], "name": d["name"],
            "alloc": d["alloc"], "capital": cap,
            "wt_ret": r.total_return, "pnl": pnl,
            "dd": r.max_drawdown, "grade": d["grade"].value,
        })

    port_ret = total_pnl / capital
    ann_ret = (1 + port_ret) ** (1 / avg_years) - 1 if port_ret > -1 else -1

    return {
        "style": style, "desc": strat["desc"], "risk": strat["risk"],
        "total_ret": port_ret, "ann_ret": ann_ret, "pnl": total_pnl,
        "years": avg_years, "holdings": results_detail,
    }


# ═══ CLI COMMANDS ═══

async def cmd_scan(args, config):
    """Scan a market with a strategy."""
    capital = args.capital or config.backtest.initial_capital
    period = args.period or config.backtest.period
    style = args.style or config.default_strategy
    UNIVERSES = _load_universes()
    markets = [args.market] if args.market != "all" else ["us", "china", "hk", "japan", "korea"]

    if style not in STRATEGIES:
        print(f"  Unknown strategy: {style}. Use 'finclaw info' to see available strategies.")
        return

    print(f"\n  FinClaw Scan")
    print(f"  Market: {args.market} | Style: {style} | Capital: {capital:,.0f} | Period: {period}")
    print(f"  Strategy: {STRATEGIES[style]['desc']}")
    print("=" * 80)

    for market in markets:
        if market not in UNIVERSES:
            print(f"  Unknown market: {market}"); continue

        print(f"\n  Scanning {market.upper()} ({len(UNIVERSES[market])} stocks)...")
        data = await scan_universe(UNIVERSES[market], period, capital)
        result = await run_strategy(style, data, capital)

        if not result:
            print("  No stocks matched criteria."); continue

        print(f"\n  === {market.upper()} - {style.upper()} ===")
        print(f"\n  {'Ticker':<12} {'Name':<18} {'Grade':>5} {'Alloc':>6} {'Return':>8} {'P&L':>12}")
        print("  " + "-" * 70)

        for h in result["holdings"]:
            print(f"  {h['ticker']:<12} {h['name']:<18} {h['grade']:>5} {h['alloc']:>5.0%} "
                  f"{h['wt_ret']:>+7.1%} {h['pnl']:>+11,.0f}")

        print(f"\n  Portfolio: {result['total_ret']:>+.1%} ({result['ann_ret']:>+.1%}/year)")
        print(f"  P&L: {result['pnl']:>+,.0f} | Final: {capital + result['pnl']:>,.0f}")

    print("=" * 80)


async def cmd_backtest(args, config):
    """Backtest one or more tickers with a strategy."""
    BacktesterV7 = _load_backtester()
    tickers = [t.strip() for t in args.ticker.split(",")]
    period = args.period or config.backtest.period
    capital = args.capital or config.backtest.initial_capital
    strategy = args.strategy or config.default_strategy
    benchmark = getattr(args, "benchmark", None)
    report_fmt = getattr(args, "report", None)

    all_results = []

    for ticker in tickers:
        print(f"\n  FinClaw Backtest: {ticker} | Strategy: {strategy}")
        h = fetch_data(ticker, period)
        if not h:
            print(f"  ERROR: No data for {ticker}.")
            continue
        h = _parse_data_for_backtest(h)

        bh = h[-1]["price"] / h[0]["price"] - 1
        years = len(h) / 252

        bt = BacktesterV7(initial_capital=capital)
        r = await bt.run(ticker, "v7", h)
        ann = (1 + r.total_return)**(1/years) - 1 if r.total_return > -1 else -1

        print(f"  Period: {years:.1f} years | B&H: {bh:+.1%}")
        print(f"  WT Return: {r.total_return:+.1%} ({ann:+.1%}/year)")
        print(f"  Alpha: {r.total_return - bh:+.1%}")
        print(f"  MaxDD: {r.max_drawdown:+.1%}")
        print(f"  Trades: {r.total_trades} | Win Rate: {r.win_rate:.0%}")
        print(f"  P&L: {capital * r.total_return:+,.0f} | Final: {capital * (1 + r.total_return):,.0f}")

        # Benchmark comparison
        bench_ret = None
        if benchmark:
            bh_data = fetch_data(benchmark, period)
            if bh_data:
                bh_data = _parse_data_for_backtest(bh_data)
                bench_ret = bh_data[-1]["price"] / bh_data[0]["price"] - 1
                print(f"  Benchmark ({benchmark}): {bench_ret:+.1%} | Excess: {r.total_return - bench_ret:+.1%}")

        results = {
            "ticker": ticker, "strategy": strategy, "period": period,
            "total_return": r.total_return, "annualized_return": ann,
            "max_drawdown": r.max_drawdown, "total_trades": r.total_trades,
            "win_rate": r.win_rate, "buy_hold": bh,
            "sharpe_ratio": getattr(r, "sharpe_ratio", 0),
            "sortino_ratio": getattr(r, "sortino_ratio", 0),
            "profit_factor": getattr(r, "profit_factor", 0),
            "num_trades": r.total_trades,
            "benchmark": benchmark, "benchmark_return": bench_ret,
            "avg_trade_return": 0, "avg_win": 0, "avg_loss": 0,
            "equity_curve": [x["price"] for x in h],
            "monthly_returns": [],
            "trade_log": [],
        }
        all_results.append(results)

    if args.output:
        out_data = all_results if len(all_results) > 1 else all_results[0] if all_results else {}
        with open(args.output, "w") as f:
            json.dump(out_data, f, indent=2, default=str)
        print(f"\n  Results saved to {args.output}")

    # Generate HTML report if requested
    if report_fmt == "html" and all_results:
        try:
            from src.reports.html_report import generate_html_report
            for res in all_results:
                output_path = os.path.join(
                    config.report.output_dir,
                    f"backtest_{res['ticker']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                )
                os.makedirs(config.report.output_dir, exist_ok=True)
                generate_html_report(res, title=f"FinClaw - {res['ticker']}", output_path=output_path)
                print(f"  HTML report: {output_path}")
        except Exception as e:
            print(f"  Report generation failed: {e}")


async def cmd_signal(args, config):
    """Get trading signal for a ticker."""
    AssetSelector, AssetGrade = _load_selector()
    ticker = args.ticker
    strategy = args.strategy or config.default_strategy
    period = args.period or "1y"

    print(f"\n  FinClaw Signal: {ticker} | Strategy: {strategy}")
    h = fetch_data(ticker, period)
    if not h:
        print(f"  ERROR: No data for {ticker}.")
        return

    prices = [x["price"] for x in h]
    volumes = [x.get("volume", 0) for x in h]

    selector = AssetSelector()
    try:
        score = selector.score_asset(prices[-150:], volumes[-150:])
        print(f"  Grade: {score.grade.value}")
        print(f"  Composite: {score.composite:.3f}")
        print(f"  Momentum: {'BULLISH' if prices[-1] > prices[-20] else 'BEARISH'}")
        print(f"  Volatility: {_calc_vol(prices):.1%} annualized")

        # Simple signal
        momentum = prices[-1] / prices[-20] - 1
        vol = _calc_vol(prices)
        if score.composite > 0.6 and momentum > 0:
            signal = "STRONG BUY"
            color = "🟢"
        elif score.composite > 0.4 and momentum > 0:
            signal = "BUY"
            color = "🟢"
        elif score.composite < 0.3 or momentum < -0.1:
            signal = "SELL"
            color = "🔴"
        else:
            signal = "HOLD"
            color = "🟡"

        print(f"\n  Signal: {color} {signal}")
    except Exception as e:
        print(f"  Error computing signal: {e}")


def _calc_vol(prices: list[float]) -> float:
    if len(prices) < 2:
        return 0
    rets = [prices[i]/prices[i-1]-1 for i in range(1, len(prices))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean)**2 for r in rets) / (len(rets) - 1)
    return var**0.5 * math.sqrt(252)


async def cmd_optimize(args, config):
    """Optimize strategy parameters."""
    from src.optimization.optimizer import StrategyOptimizer

    ticker = args.data
    print(f"\n  FinClaw Optimize: {args.strategy} on {ticker}")

    h = fetch_data(ticker, config.backtest.period)
    if not h:
        print(f"  ERROR: No data for {ticker}.")
        return

    prices = [x["price"] for x in h]

    # Load param grid
    if args.param_grid and os.path.exists(args.param_grid):
        with open(args.param_grid) as f:
            param_grid = json.load(f)
    else:
        # Default param grid for momentum
        param_grid = {
            "lookback": [10, 20, 30, 50],
            "threshold": [0.02, 0.05, 0.10],
        }
        print(f"  Using default param grid: {param_grid}")

    # Create a simple strategy class for optimization
    class SimpleStrategy:
        def __init__(self, lookback=20, threshold=0.05):
            self.lookback = lookback
            self.threshold = threshold

        def signal(self, prices):
            if len(prices) < self.lookback + 1:
                return 0
            ret = prices[-1] / prices[-self.lookback] - 1
            if ret > self.threshold:
                return 1.0
            elif ret < -self.threshold:
                return -1.0
            return 0

    optimizer = StrategyOptimizer(SimpleStrategy)
    report = optimizer.optimize(
        param_grid=param_grid,
        data=prices,
        metric=args.metric or "sharpe_ratio",
        method=args.method or "grid",
    )

    print(f"\n  Best Params: {report.best_params}")
    print(f"  Best {args.metric or 'sharpe_ratio'}: {report.best_metric:.4f}")
    print(f"  Combinations tested: {report.total_combinations}")

    if len(report.all_results) > 1:
        print(f"\n  Top 5 Results:")
        print(f"  {'Params':<40} {'Sharpe':>8} {'Return':>8} {'MaxDD':>8}")
        print("  " + "-" * 65)
        for r in report.all_results[:5]:
            print(f"  {str(r.params):<40} {r.sharpe_ratio:>8.3f} {r.total_return:>+7.1%} {r.max_drawdown:>7.1%}")


async def cmd_report(args, config):
    """Generate HTML report from backtest results."""
    from src.reports.html_report import generate_html_report

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"  ERROR: File not found: {input_path}")
        return

    with open(input_path) as f:
        data = json.load(f)

    output = args.output or os.path.join(
        config.report.output_dir,
        f"report_{data.get('ticker', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    )

    title = f"FinClaw Backtest - {data.get('ticker', 'Unknown')} ({data.get('strategy', '')})"
    html = generate_html_report(data, title=title, output_path=output)

    print(f"\n  Report generated: {output}")
    print(f"  Size: {len(html):,} bytes")


async def cmd_portfolio(args, config):
    """Portfolio analysis with allocation methods."""
    from src.portfolio.rebalancer import PortfolioRebalancer, Position

    tickers = [t.strip() for t in args.tickers.split(",")]
    method = args.method or "equal"
    capital = args.capital or config.backtest.initial_capital

    print(f"\n  FinClaw Portfolio: {', '.join(tickers)} | Method: {method}")

    # Fetch data and compute allocations
    prices_data = {}
    for ticker in tickers:
        h = fetch_data(ticker, config.backtest.period)
        if h:
            prices_data[ticker] = h

    if not prices_data:
        print("  ERROR: No data for any tickers.")
        return

    tickers = list(prices_data.keys())

    if method == "equal":
        weights = {t: 1.0 / len(tickers) for t in tickers}
    elif method == "risk_parity":
        vols = {}
        for t, h in prices_data.items():
            prices = [x["price"] for x in h]
            vols[t] = _calc_vol(prices) or 0.2
        inv_vols = {t: 1.0/v for t, v in vols.items()}
        total = sum(inv_vols.values())
        weights = {t: iv/total for t, iv in inv_vols.items()}
    elif method == "momentum":
        moms = {}
        for t, h in prices_data.items():
            prices = [x["price"] for x in h]
            moms[t] = prices[-1] / prices[max(0, len(prices)-252)] - 1 if len(prices) > 252 else 0
        pos_moms = {t: max(m, 0.01) for t, m in moms.items()}
        total = sum(pos_moms.values())
        weights = {t: m/total for t, m in pos_moms.items()}
    else:
        weights = {t: 1.0 / len(tickers) for t in tickers}

    print(f"\n  {'Ticker':<10} {'Weight':>8} {'Capital':>12} {'1Y Return':>10} {'Vol':>8}")
    print("  " + "-" * 55)
    for t in tickers:
        h = prices_data[t]
        prices = [x["price"] for x in h]
        ret_1y = prices[-1] / prices[max(0, len(prices)-252)] - 1 if len(prices) > 252 else 0
        vol = _calc_vol(prices)
        alloc = capital * weights[t]
        print(f"  {t:<10} {weights[t]:>7.1%} {alloc:>11,.0f} {ret_1y:>+9.1%} {vol:>7.1%}")

    print(f"\n  Total Capital: {capital:,.0f}")


async def cmd_cache(args, config):
    """Cache management."""
    from src.pipeline.cache import DataCache
    cache = DataCache()

    if args.stats:
        stats = cache.stats()
        print(f"\n  FinClaw Cache Statistics")
        print(f"  Entries: {stats.total_entries}")
        print(f"  Size: {stats.size_bytes / 1024:.1f} KB")
        print(f"  Hits: {stats.hits} | Misses: {stats.misses}")
        print(f"  Hit Rate: {stats.hit_rate:.1%}")
        print(f"  Expired Purged: {stats.expired_purged}")
    elif args.clear:
        cache.clear()
        print("  Cache cleared.")
    elif args.purge:
        n = cache.purge_expired()
        print(f"  Purged {n} expired entries.")
    elif args.keys:
        keys = cache.keys()
        print(f"\n  Cached keys ({len(keys)}):")
        for k in keys[:50]:
            print(f"    {k}")
    else:
        stats = cache.stats()
        print(f"  Cache: {stats.total_entries} entries, {stats.size_bytes/1024:.1f}KB")


def cmd_info(args, config):
    """Show available strategies and markets."""
    UNIVERSES = _load_universes()
    print("\n  FinClaw v2.1.0 - AI-Powered Financial Intelligence Engine\n")
    print(f"  {'Strategy':<18} {'Risk':<15} {'Target':>12} {'Description'}")
    print("  " + "-" * 75)
    for name, s in STRATEGIES.items():
        print(f"  {name:<18} {s['risk']:<15} {s['target_ann']:>12} {s['desc']}")

    print(f"\n  Markets: " + ", ".join(f"{k}({len(v)})" for k, v in UNIVERSES.items()) + ", all")
    total = sum(len(v) for v in UNIVERSES.values())
    print(f"  Total stocks: {total}")

    print(f"\n  Config: {config.default_strategy} strategy, {config.default_universe} market")
    print(f"  Capital: {config.backtest.initial_capital:,.0f} | Period: {config.backtest.period}")


def main():
    try:
        config = FinClawConfig.load()
    except ConfigValidationError as e:
        print(f"\n  {e}")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="FinClaw - AI-Powered Financial Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", "-C", help="Config file path")
    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan market with strategy")
    p_scan.add_argument("--market", "-m", default="us", choices=["us","china","hk","japan","korea","all"])
    p_scan.add_argument("--style", "-s", default=None)
    p_scan.add_argument("--capital", "-c", type=float, default=None)
    p_scan.add_argument("--period", "-p", default=None)

    # backtest
    p_bt = sub.add_parser("backtest", help="Backtest a ticker")
    p_bt.add_argument("--ticker", "-t", required=True)
    p_bt.add_argument("--strategy", "-s", default=None)
    p_bt.add_argument("--start", default=None)
    p_bt.add_argument("--end", default=None)
    p_bt.add_argument("--period", "-p", default=None)
    p_bt.add_argument("--capital", "-c", type=float, default=None)
    p_bt.add_argument("--output", "-o", help="Save results JSON")
    p_bt.add_argument("--benchmark", "-b", default=None, help="Benchmark ticker (e.g. SPY)")
    p_bt.add_argument("--report", default=None, choices=["html"], help="Generate report")

    # signal
    p_sig = sub.add_parser("signal", help="Get trading signal")
    p_sig.add_argument("--ticker", "-t", required=True)
    p_sig.add_argument("--strategy", "-s", default=None)
    p_sig.add_argument("--period", "-p", default=None)

    # optimize
    p_opt = sub.add_parser("optimize", help="Optimize strategy parameters")
    p_opt.add_argument("--strategy", "-s", default="momentum")
    p_opt.add_argument("--param-grid", help="JSON file with param grid")
    p_opt.add_argument("--data", "-d", required=True, help="Ticker for data")
    p_opt.add_argument("--metric", default="sharpe_ratio")
    p_opt.add_argument("--method", default="grid", choices=["grid", "random"])

    # report
    p_rep = sub.add_parser("report", help="Generate HTML report")
    p_rep.add_argument("--input", "-i", required=True, help="Backtest results JSON")
    p_rep.add_argument("--format", "-f", default="html", choices=["html"])
    p_rep.add_argument("--output", "-o", help="Output file path")

    # portfolio
    p_port = sub.add_parser("portfolio", help="Portfolio analysis")
    p_port.add_argument("--tickers", "-t", required=True, help="Comma-separated tickers")
    p_port.add_argument("--method", "-m", default="equal", choices=["equal", "risk_parity", "momentum"])
    p_port.add_argument("--capital", "-c", type=float, default=None)

    # cache
    p_cache = sub.add_parser("cache", help="Cache management")
    p_cache.add_argument("--stats", action="store_true")
    p_cache.add_argument("--clear", action="store_true")
    p_cache.add_argument("--purge", action="store_true", help="Purge expired entries")
    p_cache.add_argument("--keys", action="store_true", help="List cached keys")

    # info
    sub.add_parser("info", help="Show strategies and markets")

    # test
    sub.add_parser("test", help="Run test suite")

    args = parser.parse_args()

    if args.config:
        config = FinClawConfig.load(args.config)

    try:
        if args.command == "scan":
            asyncio.run(cmd_scan(args, config))
        elif args.command == "backtest":
            asyncio.run(cmd_backtest(args, config))
        elif args.command == "signal":
            asyncio.run(cmd_signal(args, config))
        elif args.command == "optimize":
            asyncio.run(cmd_optimize(args, config))
        elif args.command == "report":
            asyncio.run(cmd_report(args, config))
        elif args.command == "portfolio":
            asyncio.run(cmd_portfolio(args, config))
        elif args.command == "cache":
            asyncio.run(cmd_cache(args, config))
        elif args.command == "info":
            cmd_info(args, config)
        elif args.command == "test":
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            sys.exit(result.returncode)
        else:
            parser.print_help()
            print("\n  Quick start:")
            print("    finclaw info")
            print("    finclaw scan --market us --style soros")
            print("    finclaw backtest --ticker AAPL --strategy momentum")
            print("    finclaw signal --ticker MSFT")
            print("    finclaw optimize --strategy momentum --data AAPL")
            print("    finclaw portfolio --tickers AAPL,MSFT,GOOGL --method risk_parity")
            print("    finclaw report --input results.json --format html")
            print("    finclaw cache --stats")
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\n  ERROR: {e}")
        print("  Run with --help for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
