"""
Arena Evolver — integrates arena competition into the evolution pipeline.
==========================================================================
Wraps the existing UnifiedEvolver and periodically (every N generations)
runs an arena evaluation on the frontier's top DNAs. Arena performance
adjusts fitness scores: DNAs that overfit (perform well alone but poorly
in competition) get penalized.

Usage:
    python -m src.evolution.arena_evolver --help
    python -m src.evolution.arena_evolver --generations 50 --arena-interval 5
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .arena import TradingArena, ArenaResult, arena_evaluate
from .unified_evolver import UnifiedDNA, UnifiedEvolver, _PARAM_RANGES


# ════════════════════════════════════════════════════════════════════
# ArenaEvolver — evolution with arena-based anti-overfitting
# ════════════════════════════════════════════════════════════════════

@dataclass
class ArenaConfig:
    """Configuration for arena-enhanced evolution."""

    # Evolution parameters
    generations: int = 50
    population_size: int = 30
    elite_count: int = 5
    mutation_rate: float = 0.3

    # Arena parameters
    arena_interval: int = 5        # Run arena every N generations
    arena_top_k: int = 10          # How many top DNAs enter the arena
    arena_penalty: float = 0.15    # Max fitness penalty for worst arena rank
    arena_impact_pct: float = 0.005  # Price impact percentage
    arena_impact_threshold: float = 0.5  # Fraction triggering impact

    # Data
    data_dir: str = "data/a_shares"
    results_dir: str = "evolution_results_arena"
    use_ml: bool = False  # ML training is slow; default off for arena mode
    seed: Optional[int] = None


class ArenaEvolver:
    """Evolution engine with periodic arena-based fitness adjustment.

    Every ``arena_interval`` generations, the top-K DNAs from the current
    frontier are placed into a TradingArena. Their arena ranking is used
    to adjust fitness:
      - Best-ranked DNA: no penalty
      - Worst-ranked DNA: fitness *= (1 - arena_penalty)

    This penalizes overfitted DNAs that only perform well in isolation.

    Parameters
    ----------
    config : ArenaConfig
        Configuration parameters.
    base_evolver : UnifiedEvolver, optional
        Pre-configured evolver. If None, one is created from config.
    """

    def __init__(
        self,
        config: Optional[ArenaConfig] = None,
        base_evolver: Optional[UnifiedEvolver] = None,
    ):
        self.config = config or ArenaConfig()
        self.base_evolver = base_evolver or UnifiedEvolver(
            data_dir=self.config.data_dir,
            population_size=self.config.population_size,
            elite_count=self.config.elite_count,
            mutation_rate=self.config.mutation_rate,
            results_dir=self.config.results_dir,
            seed=self.config.seed,
        )
        self.arena_history: List[Dict[str, Any]] = []

    def evolve(self) -> List[Dict[str, Any]]:
        """Run evolution with periodic arena competition.

        Returns the final elite results (same format as UnifiedEvolver).
        """
        cfg = self.config
        evolver = self.base_evolver

        print("=" * 60)
        print("🏟️  Arena Evolution Mode")
        print(f"    Arena every {cfg.arena_interval} gens | "
              f"Top-{cfg.arena_top_k} compete | "
              f"Penalty up to {cfg.arena_penalty:.0%}")
        print("=" * 60)

        # Load data
        t0 = time.time()
        print("Loading stock data...", flush=True)
        data = evolver.load_elite_pool()
        print(f"Loaded {len(data)} stocks in {time.time() - t0:.1f}s")

        if not data:
            print("ERROR: No data loaded. Check data_dir.")
            return []

        # Optional ML model
        ml_model = None
        if cfg.use_ml:
            print("Training ML model...", flush=True)
            ml_model = evolver.train_ml_model(data, evolver.best_dna)
            if ml_model:
                print("ML model ready.")
            else:
                print("ML training failed, continuing without ML.")

        # Initialize population
        parents = evolver._load_parents()
        start_gen = evolver._load_start_gen()
        if not parents:
            parents = [evolver.best_dna]
            start_gen = 0

        print(f"Starting from gen {start_gen} with {len(parents)} parents")
        print("-" * 60)

        all_results: List[Dict[str, Any]] = []
        best_fitness_ever = float("-inf")

        for gen in range(start_gen, start_gen + cfg.generations):
            gen_t0 = time.time()

            # Generate candidates
            candidates: List[UnifiedDNA] = list(parents)
            while len(candidates) < cfg.population_size:
                parent = evolver.rng.choice(parents)
                if evolver.rng.random() < 0.7:
                    child = evolver.mutate(parent)
                else:
                    other = evolver.rng.choice(parents)
                    child = evolver.crossover(parent, other)
                    child = evolver.mutate(child)
                candidates.append(child)

            # Evaluate all candidates
            results = [evolver.backtest(dna, data, ml_model) for dna in candidates]
            results.sort(key=lambda r: r["fitness"], reverse=True)

            # Arena evaluation at specified intervals
            is_arena_gen = (gen > 0 and gen % cfg.arena_interval == 0)
            if is_arena_gen and len(results) >= 2:
                arena_top = results[:min(cfg.arena_top_k, len(results))]
                arena_dnas = [r["dna"] for r in arena_top]

                # Prepare stock data for arena (convert to arena format)
                arena_stock_data = self._prepare_arena_data(data)

                if arena_stock_data:
                    arena_results = arena_evaluate(
                        dna_list=arena_dnas,
                        stock_data=arena_stock_data,
                        impact_threshold=cfg.arena_impact_threshold,
                        impact_pct=cfg.arena_impact_pct,
                    )

                    # Apply arena penalty to fitness
                    n_arena = len(arena_results)
                    for ar in arena_results:
                        if ar.dna_index < len(arena_top):
                            # Linear penalty: rank 1 = no penalty, rank N = max penalty
                            penalty_frac = (ar.rank - 1) / max(n_arena - 1, 1)
                            penalty = 1.0 - penalty_frac * cfg.arena_penalty
                            arena_top[ar.dna_index]["fitness"] *= penalty
                            arena_top[ar.dna_index]["arena_rank"] = ar.rank
                            arena_top[ar.dna_index]["arena_penalty"] = round(1 - penalty, 4)

                    # Re-sort after penalty
                    results.sort(key=lambda r: r["fitness"], reverse=True)

                    # Log arena results
                    self.arena_history.append({
                        "generation": gen,
                        "arena_results": [
                            {
                                "dna_index": ar.dna_index,
                                "rank": ar.rank,
                                "final_value": ar.final_value,
                                "sharpe": ar.sharpe,
                                "max_drawdown": ar.max_drawdown,
                            }
                            for ar in arena_results
                        ],
                    })

                    print(f"  🏟️  Arena @ gen {gen}: "
                          f"top={arena_results[0].final_value:.0f} "
                          f"bot={arena_results[-1].final_value:.0f}")

            # Select elites
            elite_results = results[:cfg.elite_count]
            best = elite_results[0]
            gen_time = time.time() - gen_t0

            arena_marker = " 🏟️" if is_arena_gen else ""
            print(
                f"Gen {gen:4d}{arena_marker} | "
                f"fitness={best['fitness']:8.2f} | "
                f"return={best['annual_return']:7.2f}% | "
                f"dd={best['max_drawdown']:5.2f}% | "
                f"sharpe={best['sharpe']:5.2f} | "
                f"trades={best['total_trades']:4d} | "
                f"{gen_time:.1f}s"
            )

            if best["fitness"] > best_fitness_ever:
                best_fitness_ever = best["fitness"]

            parents = [UnifiedDNA.from_dict(r["dna"]) for r in elite_results]
            all_results = elite_results

            # Save periodically
            if (gen + 1) % 10 == 0 or gen == start_gen + cfg.generations - 1:
                self._save_results(gen, elite_results)

        print("-" * 60)
        print(f"Arena evolution complete! Best fitness: {best_fitness_ever:.4f}")
        print(f"Arena evaluations: {len(self.arena_history)}")
        print("=" * 60)

        return all_results

    def run_single_arena(
        self,
        dna_dicts: List[Dict[str, Any]],
        stock_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[ArenaResult]:
        """Run a single arena evaluation on provided DNAs.

        Convenience method for testing or one-off comparisons.
        """
        if stock_data is None:
            raw_data = self.base_evolver.load_elite_pool()
            stock_data = self._prepare_arena_data(raw_data)

        return arena_evaluate(
            dna_list=dna_dicts,
            stock_data=stock_data,
            impact_threshold=self.config.arena_impact_threshold,
            impact_pct=self.config.arena_impact_pct,
        )

    def _prepare_arena_data(
        self,
        data: Dict[str, Dict[str, Any]],
        max_stocks: int = 50,
    ) -> Dict[str, Dict[str, Any]]:
        """Convert evolver stock data to arena format.

        Selects a subset of stocks to keep arena simulation fast.
        """
        arena_data: Dict[str, Dict[str, Any]] = {}
        codes = list(data.keys())[:max_stocks]
        for code in codes:
            sd = data[code]
            arena_data[code] = {
                "close": sd["close"],
                "volume": sd["volume"],
            }
        return arena_data

    def _save_results(self, gen: int, results: List[Dict[str, Any]]) -> None:
        """Save evolution results and arena history."""
        os.makedirs(self.config.results_dir, exist_ok=True)
        payload = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "system": "arena_evolution",
            "results": results,
            "arena_history": self.arena_history,
        }
        latest = os.path.join(self.config.results_dir, "latest.json")
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════
# CLI entry point
# ════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point for arena evolution."""
    parser = argparse.ArgumentParser(
        prog="arena_evolver",
        description="Multi-DNA Arena Competition Evolution — anti-overfitting via market simulation",
    )
    parser.add_argument(
        "--generations", type=int, default=50,
        help="Number of evolution generations (default: 50)",
    )
    parser.add_argument(
        "--population", type=int, default=30,
        help="Population size per generation (default: 30)",
    )
    parser.add_argument(
        "--elite-count", type=int, default=5,
        help="Number of elite DNAs to keep per generation (default: 5)",
    )
    parser.add_argument(
        "--arena-interval", type=int, default=5,
        help="Run arena every N generations (default: 5)",
    )
    parser.add_argument(
        "--arena-top-k", type=int, default=10,
        help="Number of top DNAs to enter arena (default: 10)",
    )
    parser.add_argument(
        "--arena-penalty", type=float, default=0.15,
        help="Max fitness penalty for worst arena rank (default: 0.15)",
    )
    parser.add_argument(
        "--impact-pct", type=float, default=0.005,
        help="Price impact when threshold exceeded (default: 0.005 = 0.5%%)",
    )
    parser.add_argument(
        "--data-dir", type=str, default="data/a_shares",
        help="Directory containing stock CSV data",
    )
    parser.add_argument(
        "--results-dir", type=str, default="evolution_results_arena",
        help="Directory to save results",
    )
    parser.add_argument(
        "--use-ml", action="store_true",
        help="Enable ML model training (slower)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args(argv)

    config = ArenaConfig(
        generations=args.generations,
        population_size=args.population,
        elite_count=args.elite_count,
        arena_interval=args.arena_interval,
        arena_top_k=args.arena_top_k,
        arena_penalty=args.arena_penalty,
        arena_impact_pct=args.impact_pct,
        data_dir=args.data_dir,
        results_dir=args.results_dir,
        use_ml=args.use_ml,
        seed=args.seed,
    )

    evolver = ArenaEvolver(config=config)
    results = evolver.evolve()

    if results:
        print(f"\nBest DNA fitness: {results[0]['fitness']:.4f}")
        print(f"Best annual return: {results[0]['annual_return']:.2f}%")
        print(f"Results saved to: {config.results_dir}/latest.json")


if __name__ == "__main__":
    main()
