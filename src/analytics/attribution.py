"""Brinson-style Performance Attribution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SectorWeight:
    """Sector allocation for portfolio or benchmark."""
    sector: str
    weight: float  # 0..1
    return_pct: float  # e.g. 0.05 for 5%


@dataclass
class AttributionResult:
    """Per-sector attribution breakdown."""
    sector: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_effect: float


class PerformanceAttribution:
    """Brinson–Hood–Beebower attribution analysis."""

    def __init__(
        self,
        portfolio_sectors: list[SectorWeight],
        benchmark_sectors: list[SectorWeight],
    ):
        self.portfolio = {s.sector: s for s in portfolio_sectors}
        self.benchmark = {s.sector: s for s in benchmark_sectors}
        self.sectors = sorted(set(self.portfolio) | set(self.benchmark))

    def analyze(self) -> list[AttributionResult]:
        """Run Brinson attribution, return per-sector results."""
        results: list[AttributionResult] = []
        # Benchmark total return for allocation effect
        bench_total = sum(s.weight * s.return_pct for s in self.benchmark.values())

        for sector in self.sectors:
            pw = self.portfolio[sector].weight if sector in self.portfolio else 0.0
            bw = self.benchmark[sector].weight if sector in self.benchmark else 0.0
            pr = self.portfolio[sector].return_pct if sector in self.portfolio else 0.0
            br = self.benchmark[sector].return_pct if sector in self.benchmark else 0.0

            allocation = (pw - bw) * (br - bench_total)
            selection = bw * (pr - br)
            interaction = (pw - bw) * (pr - br)

            results.append(AttributionResult(
                sector=sector,
                portfolio_weight=pw,
                benchmark_weight=bw,
                portfolio_return=pr,
                benchmark_return=br,
                allocation_effect=allocation,
                selection_effect=selection,
                interaction_effect=interaction,
                total_effect=allocation + selection + interaction,
            ))
        return results

    def summary(self) -> dict[str, float]:
        """Aggregate attribution effects."""
        results = self.analyze()
        return {
            "allocation_effect": sum(r.allocation_effect for r in results),
            "selection_effect": sum(r.selection_effect for r in results),
            "interaction_effect": sum(r.interaction_effect for r in results),
            "total_active_return": sum(r.total_effect for r in results),
        }
