"""
DeFi Llama API Client
Real-time DeFi protocol data: TVL, yields, chains, stablecoins.
Free API, no keys needed.
"""

import urllib.request
import json
from dataclasses import dataclass


@dataclass
class ProtocolInfo:
    name: str
    slug: str
    tvl: float
    chain: str
    category: str
    change_1d: float | None = None
    change_7d: float | None = None


@dataclass
class YieldPool:
    pool_id: str
    project: str
    chain: str
    symbol: str
    tvl_usd: float
    apy: float
    apy_base: float | None = None
    apy_reward: float | None = None


@dataclass
class ChainTVL:
    name: str
    tvl: float


@dataclass
class StablecoinInfo:
    name: str
    symbol: str
    peg_type: str
    circulating: float
    price: float | None = None


class DefiLlamaClient:
    """Client for DeFi Llama's free APIs."""

    BASE = "https://api.llama.fi"
    YIELDS_BASE = "https://yields.llama.fi"
    STABLECOINS_BASE = "https://stablecoins.llama.fi"

    def __init__(self, timeout: int = 15):
        self._timeout = timeout

    def _get(self, url: str) -> dict | list:
        req = urllib.request.Request(url, headers={"User-Agent": "FinClaw/1.0"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode())

    def get_top_protocols(self, limit: int = 20) -> list[ProtocolInfo]:
        """Top DeFi protocols by TVL."""
        data = self._get(f"{self.BASE}/protocols")
        results = []
        for p in data[:limit]:
            results.append(ProtocolInfo(
                name=p.get("name", ""),
                slug=p.get("slug", ""),
                tvl=p.get("tvl", 0) or 0,
                chain=p.get("chain", p.get("chains", [""])[0] if p.get("chains") else ""),
                category=p.get("category", ""),
                change_1d=p.get("change_1d"),
                change_7d=p.get("change_7d"),
            ))
        return results

    def get_protocol_tvl(self, name: str) -> dict:
        """TVL history for a protocol. Returns raw protocol detail dict."""
        return self._get(f"{self.BASE}/protocol/{name}")

    def get_best_yields(self, chain: str | None = None, min_tvl: float = 100_000) -> list[YieldPool]:
        """Highest APY pools from DeFi Llama yields API."""
        data = self._get(f"{self.YIELDS_BASE}/pools")
        pools = data.get("data", data) if isinstance(data, dict) else data
        results = []
        for p in pools:
            tvl = p.get("tvlUsd", 0) or 0
            apy = p.get("apy", 0) or 0
            if tvl < min_tvl or apy <= 0:
                continue
            p_chain = p.get("chain", "")
            if chain and p_chain.lower() != chain.lower():
                continue
            results.append(YieldPool(
                pool_id=p.get("pool", ""),
                project=p.get("project", ""),
                chain=p_chain,
                symbol=p.get("symbol", ""),
                tvl_usd=tvl,
                apy=apy,
                apy_base=p.get("apyBase"),
                apy_reward=p.get("apyReward"),
            ))
        results.sort(key=lambda x: x.apy, reverse=True)
        return results

    def get_chain_rankings(self) -> list[ChainTVL]:
        """Chains ranked by TVL."""
        data = self._get(f"{self.BASE}/chains")
        results = []
        for c in data:
            results.append(ChainTVL(
                name=c.get("name", ""),
                tvl=c.get("tvl", 0) or 0,
            ))
        results.sort(key=lambda x: x.tvl, reverse=True)
        return results

    def get_stablecoin_market(self) -> list[StablecoinInfo]:
        """Stablecoin market overview."""
        data = self._get(f"{self.STABLECOINS_BASE}/stablecoins")
        peggedAssets = data.get("peggedAssets", data) if isinstance(data, dict) else data
        results = []
        for s in peggedAssets:
            circulating = 0
            peg_stats = s.get("circulating", {})
            if isinstance(peg_stats, dict):
                circulating = peg_stats.get("peggedUSD", 0) or 0
            results.append(StablecoinInfo(
                name=s.get("name", ""),
                symbol=s.get("symbol", ""),
                peg_type=s.get("pegType", ""),
                circulating=circulating,
                price=s.get("price"),
            ))
        results.sort(key=lambda x: x.circulating, reverse=True)
        return results
