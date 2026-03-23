"""
Launch the 24/7 evolution engine.
Runs continuously, saving results every 10 generations.
Can be interrupted (Ctrl+C) and resumed — picks up from last checkpoint.
"""

import argparse
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.auto_evolve import AutoEvolver


def main():
    parser = argparse.ArgumentParser(description="FinClaw Strategy Evolution Engine")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to CSV data directory (default: data/a_shares for cn, data/crypto for crypto)",
    )
    parser.add_argument(
        "--market",
        default="cn",
        choices=["cn", "crypto"],
        help="Market type: 'cn' for A-shares, 'crypto' for cryptocurrency (default: cn)",
    )
    parser.add_argument(
        "--population", type=int, default=30, help="Population size per generation (default: 30)"
    )
    parser.add_argument(
        "--elite", type=int, default=5, help="Number of elite strategies to keep (default: 5)"
    )
    parser.add_argument(
        "--mutation-rate", type=float, default=0.3, help="Mutation rate 0.0-1.0 (default: 0.3)"
    )
    parser.add_argument(
        "--generations", type=int, default=100, help="Number of generations to run (default: 100)"
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=10,
        help="Save results every N generations (default: 10)",
    )
    parser.add_argument(
        "--results-dir",
        default="evolution_results",
        help="Directory for saving results (default: evolution_results)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    # Default data directory based on market
    data_dir = args.data_dir
    if data_dir is None:
        data_dir = "data/crypto" if args.market == "crypto" else "data/a_shares"

    evolver = AutoEvolver(
        data_dir=data_dir,
        population_size=args.population,
        elite_count=args.elite,
        mutation_rate=args.mutation_rate,
        results_dir=args.results_dir,
        seed=args.seed,
        market=args.market,
    )

    try:
        evolver.evolve(generations=args.generations, save_interval=args.save_interval)
    except KeyboardInterrupt:
        print("\n\n🦀 Evolution interrupted. Results saved — resume anytime.")
        sys.exit(0)

    # Print final best strategy
    best = evolver.load_best()
    if best:
        print(f"\n🏆 Best strategy found:\n{best}")


if __name__ == "__main__":
    main()
