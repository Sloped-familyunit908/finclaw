"""
FinClaw DeFi Monitor
====================
Monitor DeFi yields on Arbitrum and other chains.
Uses DeFi Llama API (free, no key needed).
"""

import urllib.request
import json
from typing import Optional
import logging

logger = logging.getLogger("finclaw.defi")


class DeFiMonitor:
    """Monitor DeFi yields across protocols."""

    LLAMA_POOLS_URL = "https://yields.llama.fi/pools"
    LLAMA_CHART_URL = "https://yields.llama.fi/chart"  # /{pool_id}

    # Common stablecoin symbols used for risk-filtered queries
    _STABLECOINS = frozenset({
        "USDC", "USDT", "DAI", "FRAX", "LUSD", "TUSD", "BUSD",
        "USDP", "GUSD", "SUSD", "MIM", "CRVUSD", "PYUSD", "USDS",
        "GHO", "DOLA", "EUSD", "HAY", "USD+",
    })

    def __init__(self, timeout: int = 15):
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_json(self, url: str) -> dict | list:
        """Fetch JSON from a URL."""
        req = urllib.request.Request(url, headers={"User-Agent": "FinClaw/1.0"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode())

    def _fetch_pools(self) -> list[dict]:
        """Fetch all pools from DeFi Llama."""
        data = self._fetch_json(self.LLAMA_POOLS_URL)
        # The API returns {"status": "success", "data": [...]}
        if isinstance(data, dict):
            return data.get("data", [])
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_top_pools(
        self,
        chain: str = "Arbitrum",
        min_tvl: float = 1_000_000,
        min_apy: float = 5.0,
        limit: int = 20,
    ) -> list[dict]:
        """Get top yielding pools for a chain.

        Returns a list of dicts with keys:
        ``pool, project, chain, symbol, tvl, apy, apy_base, apy_reward``
        """
        pools = self._fetch_pools()
        filtered = []
        for p in pools:
            p_chain = (p.get("chain") or "").lower()
            if chain and p_chain != chain.lower():
                continue
            tvl = p.get("tvlUsd") or 0
            apy = p.get("apy") or 0
            if tvl < min_tvl or apy < min_apy:
                continue
            filtered.append({
                "pool": p.get("pool", ""),
                "project": p.get("project", ""),
                "chain": p.get("chain", ""),
                "symbol": p.get("symbol", ""),
                "tvl": tvl,
                "apy": apy,
                "apy_base": p.get("apyBase"),
                "apy_reward": p.get("apyReward"),
            })

        filtered.sort(key=lambda x: x["apy"], reverse=True)
        return filtered[:limit]

    def get_pool_history(self, pool_id: str) -> list[dict]:
        """Get historical APY for a specific pool.

        Returns a list of ``{timestamp, tvlUsd, apy}`` dicts.
        """
        url = f"{self.LLAMA_CHART_URL}/{pool_id}"
        data = self._fetch_json(url)
        if isinstance(data, dict):
            return data.get("data", [])
        return data

    def find_best_stable_pools(
        self,
        chain: str = "Arbitrum",
        min_tvl: float = 500_000,
        limit: int = 10,
    ) -> list[dict]:
        """Find best stablecoin pools (lowest risk).

        Filters for pools whose symbol contains at least one known
        stablecoin ticker.
        """
        pools = self._fetch_pools()
        results = []
        for p in pools:
            p_chain = (p.get("chain") or "").lower()
            if chain and p_chain != chain.lower():
                continue
            tvl = p.get("tvlUsd") or 0
            if tvl < min_tvl:
                continue

            symbol = (p.get("symbol") or "").upper()
            # Check if any token in the pool is a stablecoin
            tokens = {t.strip() for t in symbol.replace("/", "-").split("-")}
            if not tokens & self._STABLECOINS:
                continue

            results.append({
                "pool": p.get("pool", ""),
                "project": p.get("project", ""),
                "chain": p.get("chain", ""),
                "symbol": p.get("symbol", ""),
                "tvl": tvl,
                "apy": p.get("apy") or 0,
                "apy_base": p.get("apyBase"),
                "apy_reward": p.get("apyReward"),
                "stablecoin": True,
            })

        results.sort(key=lambda x: x["apy"], reverse=True)
        return results[:limit]

    def generate_recommendation(self, budget_usd: float = 2000) -> str:
        """Generate allocation recommendation for a given budget.

        Fetches Arbitrum stable pools and volatile pools, then builds a
        simple 60/40 allocation suggestion.
        """
        stable_pools = self.find_best_stable_pools(chain="Arbitrum", limit=3)
        volatile_pools = self.get_top_pools(chain="Arbitrum", min_tvl=2_000_000, limit=3)

        stable_budget = budget_usd * 0.6
        volatile_budget = budget_usd * 0.4

        lines = [
            "=" * 50,
            "FinClaw DeFi Allocation Recommendation",
            "=" * 50,
            f"Budget: ${budget_usd:,.0f}",
            "",
            f"📌 Conservative allocation (60% = ${stable_budget:,.0f}):",
        ]

        if stable_pools:
            alloc_each = stable_budget / len(stable_pools)
            for p in stable_pools:
                est_yield = alloc_each * (p["apy"] / 100)
                lines.append(
                    f"  • {p['project']} {p['symbol']} — "
                    f"APY {p['apy']:.2f}% | ${alloc_each:,.0f} → "
                    f"~${est_yield:,.0f}/yr"
                )
        else:
            lines.append("  (no qualifying stable pools found)")

        lines.append("")
        lines.append(f"🚀 Growth allocation (40% = ${volatile_budget:,.0f}):")

        if volatile_pools:
            alloc_each = volatile_budget / len(volatile_pools)
            for p in volatile_pools:
                est_yield = alloc_each * (p["apy"] / 100)
                lines.append(
                    f"  • {p['project']} {p['symbol']} — "
                    f"APY {p['apy']:.2f}% | ${alloc_each:,.0f} → "
                    f"~${est_yield:,.0f}/yr"
                )
        else:
            lines.append("  (no qualifying volatile pools found)")

        total_apy = 0.0
        if stable_pools and volatile_pools:
            stable_avg = sum(p["apy"] for p in stable_pools) / len(stable_pools)
            volatile_avg = sum(p["apy"] for p in volatile_pools) / len(volatile_pools)
            total_apy = stable_avg * 0.6 + volatile_avg * 0.4

        lines += [
            "",
            f"Estimated blended APY: {total_apy:.2f}%",
            f"Estimated annual yield: ~${budget_usd * total_apy / 100:,.0f}",
            "",
            "⚠️  DeFi yields fluctuate. Past APY ≠ future APY.",
            "⚠️  Always verify smart-contract audits before depositing.",
        ]
        return "\n".join(lines)
