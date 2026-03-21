#!/usr/bin/env python3
"""
Run the 24/7 evolution engine.

Usage:
  python scripts/run_evolve.py                  # basic, no sync
  python scripts/run_evolve.py --git-sync       # auto push results to git
  python scripts/run_evolve.py --pop 50         # larger population
"""
import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.auto_evolve import AutoEvolver


def main():
    parser = argparse.ArgumentParser(description="FinClaw 24/7 Evolution Engine")
    parser.add_argument("--data-dir", default="data/a_shares", help="CSV data directory")
    parser.add_argument("--pop", type=int, default=30, help="Population size per generation")
    parser.add_argument("--elite", type=int, default=5, help="Elite count (TOP N to keep)")
    parser.add_argument("--mutation", type=float, default=0.3, help="Mutation rate")
    parser.add_argument("--generations", type=int, default=999999, help="Max generations")
    parser.add_argument("--save-every", type=int, default=10, help="Save results every N gens")
    parser.add_argument("--results-dir", default="evolution_results", help="Results directory")
    parser.add_argument("--git-sync", action="store_true", help="Auto git commit+push results")
    args = parser.parse_args()

    evolver = AutoEvolver(
        data_dir=args.data_dir,
        population_size=args.pop,
        elite_count=args.elite,
        mutation_rate=args.mutation,
        results_dir=args.results_dir,
        git_sync=args.git_sync,
    )

    evolver.evolve(generations=args.generations, save_interval=args.save_every)


if __name__ == "__main__":
    main()
