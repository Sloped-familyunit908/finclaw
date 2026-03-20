"""
Launch the Strategy Inventor — discover new trading strategies automatically.
Combines modular rule blocks instead of just tuning parameters.
Can be interrupted (Ctrl+C) and resumed.
"""

import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.strategy_inventor import StrategyInventor


def main():
    parser = argparse.ArgumentParser(
        description="🦀 FinClaw Strategy Inventor — discover new trading strategies"
    )
    parser.add_argument(
        "--data-dir",
        default="data/a_shares",
        help="Path to A-shares CSV directory (default: data/a_shares)",
    )
    parser.add_argument(
        "--population",
        type=int,
        default=20,
        help="Population size per generation (default: 20)",
    )
    parser.add_argument(
        "--elite",
        type=int,
        default=5,
        help="Number of elite strategies to keep (default: 5)",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=50,
        help="Number of generations to run (default: 50)",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=10,
        help="Save results every N generations (default: 10)",
    )
    parser.add_argument(
        "--results-dir",
        default="invention_results",
        help="Directory for saving results (default: invention_results)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    inventor = StrategyInventor(
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        seed=args.seed,
    )

    try:
        results = inventor.invent(
            generations=args.generations,
            population=args.population,
            elite_count=args.elite,
            save_interval=args.save_interval,
        )
    except KeyboardInterrupt:
        print("\n\n🦀 Invention interrupted. Results saved — resume anytime.")
        sys.exit(0)

    if results:
        best = results[0]
        print(f"\n🏆 Best invented strategy: {best.strategy.name}")
        print(f"   Entry rules:  {best.strategy.entry_rules}")
        print(f"   Filter rules: {best.strategy.filter_rules}")
        print(f"   Exit rules:   {best.strategy.exit_rules}")
        print(f"   Fitness: {best.fitness:.4f}")
        print(f"   Annual return: {best.annual_return:.2f}%")
        print(f"   Max drawdown:  {best.max_drawdown:.2f}%")
        print(f"   Win rate:      {best.win_rate:.1f}%")
        print(f"   Sharpe:        {best.sharpe:.2f}")


if __name__ == "__main__":
    main()
