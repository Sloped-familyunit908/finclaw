"""
Validate a trading strategy's robustness using Monte Carlo simulation.

Usage:
    python scripts/validate_strategy.py --results evolution_results/latest.json
    python scripts/validate_strategy.py --results results.json --output validation_report.json
    python scripts/validate_strategy.py --results results.json --iterations 5000 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.monte_carlo import generate_validation_report


def extract_trades(results_path: str) -> list:
    """Extract trade returns from a results JSON file.

    Supports multiple formats:
      - {"trades": [1.2, -0.5, ...]}  (direct list of % returns)
      - {"results": {"trades": [...]}}
      - {"backtest": {"trades": [...]}}
      - {"strategies": [{"trades": [...]}]}  (takes first strategy)
    """
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Direct trades list
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Top-level trades
        if "trades" in data:
            return data["trades"]

        # Nested under results
        if "results" in data and isinstance(data["results"], dict):
            if "trades" in data["results"]:
                return data["results"]["trades"]

        # Nested under backtest
        if "backtest" in data and isinstance(data["backtest"], dict):
            if "trades" in data["backtest"]:
                return data["backtest"]["trades"]

        # Array of strategies
        if "strategies" in data and isinstance(data["strategies"], list):
            for strat in data["strategies"]:
                if isinstance(strat, dict) and "trades" in strat:
                    return strat["trades"]

    print(f"Error: Could not find trade returns in {results_path}")
    print("Expected format: {{\"trades\": [1.2, -0.5, 3.1, ...]}} (% returns per trade)")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Validate strategy robustness with Monte Carlo simulation"
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to JSON file with backtest results containing trade returns",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for output report JSON (default: <results>_validation.json)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of Monte Carlo iterations (default: 1000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    # Extract trades
    trades = extract_trades(args.results)
    print(f"Loaded {len(trades)} trades from {args.results}")

    # Output path
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(args.results)[0]
        output_path = f"{base}_validation.json"

    # Run validation
    print(f"Running Monte Carlo validation ({args.iterations} iterations)...")
    result = generate_validation_report(
        trades, output_path, n_iterations=args.iterations, seed=args.seed
    )

    # Print summary
    print("\n" + "=" * 60)
    print("MONTE CARLO VALIDATION REPORT")
    print("=" * 60)
    print(f"  Trades analyzed:    {result.n_trades}")
    print(f"  Iterations:         {result.n_iterations}")
    print(f"  Original return:    {result.original_annual_return:.1f}%")
    print(f"  Original Sharpe:    {result.original_sharpe:.2f}")
    print(f"  Original drawdown:  {result.original_max_drawdown:.1f}%")
    print()
    print("  Bootstrap 95% Confidence Intervals:")
    print(f"    Annual return:    {result.ci_95_lower:.1f}% to {result.ci_95_upper:.1f}% (median {result.median_return:.1f}%)")
    print(f"    Sharpe ratio:     {result.sharpe_ci_lower:.2f} to {result.sharpe_ci_upper:.2f} (median {result.median_sharpe:.2f})")
    print(f"    Max drawdown:     {result.drawdown_ci_lower:.1f}% to {result.drawdown_ci_upper:.1f}% (median {result.median_drawdown:.1f}%)")
    print()
    print(f"  P-value vs random:  {result.p_value_vs_random:.4f}")
    sig = "✅ YES" if result.is_statistically_significant else "❌ NO"
    print(f"  Statistically significant: {sig}")
    regime = "✅ STABLE" if result.regime_stable else "⚠️ UNSTABLE"
    print(f"  Regime stability:   {regime}")
    print()
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
