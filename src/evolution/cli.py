"""
CLI command: ``finclaw evolve`` — evolve trading strategies automatically.

Usage:
  finclaw evolve --symbol AAPL --generations 20
  finclaw evolve --symbol NVDA --strategy golden-cross --start 2023-01-01
"""

from __future__ import annotations

import argparse
import sys
from typing import Any


def build_evolve_parser(parent_subparsers: Any | None = None) -> argparse.ArgumentParser:
    """Build the argparse parser for the ``evolve`` subcommand.

    Parameters
    ----------
    parent_subparsers:
        If provided, adds the parser as a subcommand to an existing
        argparse subparsers group. Otherwise creates a standalone parser.
    """
    if parent_subparsers is not None:
        parser = parent_subparsers.add_parser(
            "evolve",
            help="Evolve trading strategies automatically",
            description="EvoSkill-inspired strategy evolution via backtest failures",
        )
    else:
        parser = argparse.ArgumentParser(
            prog="finclaw evolve",
            description="EvoSkill-inspired strategy evolution via backtest failures",
        )

    parser.add_argument("--symbol", required=True, help="Ticker symbol (e.g. AAPL, BTC-USDT)")
    parser.add_argument("--generations", type=int, default=10, help="Number of evolution generations (default: 10)")
    parser.add_argument("--frontier-size", type=int, default=3, help="Frontier size — top-N strategies to keep (default: 3)")
    parser.add_argument("--strategy", type=str, default=None, help="Seed strategy name from built-in library (default: golden-cross)")
    parser.add_argument("--strategy-file", type=str, default=None, help="Path to a YAML strategy file to use as seed")
    parser.add_argument("--start", type=str, default=None, help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default=None, help="Output file for the best evolved strategy")
    parser.add_argument("--verbose", action="store_true", help="Print detailed output per generation")
    parser.add_argument("--no-improvement-limit", type=int, default=5, help="Stop after this many generations without improvement")

    return parser


def cmd_evolve(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the ``finclaw evolve`` command.

    Returns the evolution result dict for testing or further processing.
    """
    import numpy as np

    from src.strategy.library import BUILTIN_STRATEGIES, get_strategy
    from src.strategy.expression import OHLCVData
    from src.evolution.engine import EvolutionEngine, EvolutionConfig

    # ---- Load seed strategy ----
    if args.strategy_file:
        with open(args.strategy_file) as f:
            seed_yaml = f.read()
    elif args.strategy:
        seed_yaml = BUILTIN_STRATEGIES.get(args.strategy)
        if seed_yaml is None:
            print(f"  ERROR: Unknown strategy '{args.strategy}'")
            print(f"  Available: {', '.join(BUILTIN_STRATEGIES.keys())}")
            return {}
    else:
        seed_yaml = BUILTIN_STRATEGIES.get("golden-cross", list(BUILTIN_STRATEGIES.values())[0])

    # ---- Fetch data ----
    print(f"  🦀 Fetching data for {args.symbol}...")
    data = _fetch_ohlcv(args.symbol, start=args.start, end=args.end)
    if data is None:
        print(f"  ERROR: Could not fetch data for {args.symbol}")
        return {}

    # ---- Configure engine ----
    config = EvolutionConfig(
        max_generations=args.generations,
        frontier_size=args.frontier_size,
        no_improvement_limit=args.no_improvement_limit,
    )
    engine = EvolutionEngine(config=config)

    # ---- Run evolution ----
    print(f"  🧬 Evolving strategy for {args.symbol} over {args.generations} generations...")
    print(f"  📊 Frontier size: {args.frontier_size} | Seed: {args.strategy or 'golden-cross'}")
    print()

    def on_gen(gen: int, score: Any, strategy: str) -> None:
        if args.verbose or gen == 0:
            print(f"  Gen {gen:3d} | Sharpe {score.sharpe_ratio:+.2f} | Return {score.total_return:+.2%} | "
                  f"DD {score.max_drawdown:.2%} | Trades {score.total_trades:3d} | "
                  f"Composite {score.composite():.4f}")

    result = engine.run(seed_yaml, data, on_generation=on_gen)

    # ---- Print results ----
    best = result["best_score"]
    print()
    print(f"  ✅ Evolution complete after {result['generations_run']} generations")
    print(f"  🏆 Best strategy:")
    print(f"      Sharpe Ratio:  {best.sharpe_ratio:+.2f}")
    print(f"      Total Return:  {best.total_return:+.2%}")
    print(f"      Max Drawdown:  {best.max_drawdown:.2%}")
    print(f"      Win Rate:      {best.win_rate:.2%}")
    print(f"      Total Trades:  {best.total_trades}")
    print(f"      Composite:     {best.composite():.4f}")

    # ---- Save output ----
    if args.output:
        with open(args.output, "w") as f:
            f.write(result["best_strategy"])
        print(f"  💾 Best strategy saved to {args.output}")

    return result


def _fetch_ohlcv(symbol: str, start: str | None = None, end: str | None = None) -> Any:
    """Fetch OHLCV data using yfinance, returning OHLCVData or None."""
    try:
        import yfinance as yf
        import warnings
        import logging

        from src.strategy.expression import OHLCVData

        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stock = yf.Ticker(symbol)
            if start:
                df = stock.history(start=start, end=end)
            else:
                df = stock.history(period="5y")

        if df.empty or len(df) < 100:
            return None

        return OHLCVData.from_dataframe(df)
    except Exception:
        return None
