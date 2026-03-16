"""
DeFi Yield Tracker
Simulated APY data for common DeFi protocols with risk scoring.
"""

from dataclasses import dataclass
import math
import hashlib


@dataclass
class YieldInfo:
    protocol: str
    pool: str
    apy: float
    tvl: float
    risk_score: float
    chain: str


# Simulated protocol data (deterministic for testing)
_PROTOCOL_DATA = {
    'aave': {
        'pools': [
            {'pool': 'USDC Lending', 'apy': 4.5, 'tvl': 5_000_000_000, 'chain': 'ethereum'},
            {'pool': 'ETH Lending', 'apy': 2.1, 'tvl': 3_000_000_000, 'chain': 'ethereum'},
            {'pool': 'WBTC Lending', 'apy': 1.8, 'tvl': 1_500_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.15,
    },
    'compound': {
        'pools': [
            {'pool': 'USDC', 'apy': 3.8, 'tvl': 2_000_000_000, 'chain': 'ethereum'},
            {'pool': 'ETH', 'apy': 1.9, 'tvl': 1_200_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.18,
    },
    'curve': {
        'pools': [
            {'pool': '3pool', 'apy': 6.2, 'tvl': 3_500_000_000, 'chain': 'ethereum'},
            {'pool': 'stETH/ETH', 'apy': 5.1, 'tvl': 2_800_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.22,
    },
    'uniswap': {
        'pools': [
            {'pool': 'ETH/USDC 0.3%', 'apy': 12.5, 'tvl': 800_000_000, 'chain': 'ethereum'},
            {'pool': 'ETH/USDT 0.3%', 'apy': 10.8, 'tvl': 600_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.35,
    },
    'lido': {
        'pools': [
            {'pool': 'stETH', 'apy': 3.9, 'tvl': 15_000_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.12,
    },
    'pancakeswap': {
        'pools': [
            {'pool': 'CAKE/BNB', 'apy': 25.0, 'tvl': 400_000_000, 'chain': 'bsc'},
            {'pool': 'USDT/BUSD', 'apy': 8.5, 'tvl': 500_000_000, 'chain': 'bsc'},
        ],
        'risk_base': 0.45,
    },
    'yearn': {
        'pools': [
            {'pool': 'yvUSDC', 'apy': 7.2, 'tvl': 300_000_000, 'chain': 'ethereum'},
            {'pool': 'yvDAI', 'apy': 6.8, 'tvl': 250_000_000, 'chain': 'ethereum'},
        ],
        'risk_base': 0.30,
    },
}


class YieldTracker:
    """Track and compare DeFi protocol yields."""

    def __init__(self):
        self._data = _PROTOCOL_DATA

    def get_rates(self, protocols: list[str] = None) -> dict:
        """Get APY rates for protocols.

        Args:
            protocols: list of protocol names, or None for all.

        Returns:
            {protocol: [YieldInfo, ...]}
        """
        result = {}
        targets = protocols if protocols else list(self._data.keys())

        for name in targets:
            name_lower = name.lower()
            if name_lower not in self._data:
                continue
            proto = self._data[name_lower]
            result[name_lower] = [
                YieldInfo(
                    protocol=name_lower,
                    pool=p['pool'],
                    apy=p['apy'],
                    tvl=p['tvl'],
                    risk_score=proto['risk_base'],
                    chain=p['chain'],
                )
                for p in proto['pools']
            ]
        return result

    def best_yields(self, min_tvl: float = 1e6) -> list[dict]:
        """Get all pools sorted by APY, filtered by min TVL.

        Returns:
            List of dicts with protocol, pool, apy, tvl, risk_score.
        """
        all_pools = []
        for proto_name, proto in self._data.items():
            for p in proto['pools']:
                if p['tvl'] >= min_tvl:
                    all_pools.append({
                        'protocol': proto_name,
                        'pool': p['pool'],
                        'apy': p['apy'],
                        'tvl': p['tvl'],
                        'risk_score': proto['risk_base'],
                        'chain': p['chain'],
                    })
        all_pools.sort(key=lambda x: x['apy'], reverse=True)
        return all_pools

    def compare_protocols(self) -> dict:
        """Compare protocols by avg APY, total TVL, and risk.

        Returns:
            {protocol: {avg_apy, total_tvl, risk_score, num_pools}}
        """
        result = {}
        for name, proto in self._data.items():
            pools = proto['pools']
            avg_apy = sum(p['apy'] for p in pools) / len(pools)
            total_tvl = sum(p['tvl'] for p in pools)
            result[name] = {
                'avg_apy': round(avg_apy, 2),
                'total_tvl': total_tvl,
                'risk_score': proto['risk_base'],
                'num_pools': len(pools),
            }
        return result

    def risk_score(self, protocol: str) -> float:
        """Get risk score for a protocol (0-1, lower is safer).

        Args:
            protocol: protocol name.

        Returns:
            Risk score float.

        Raises:
            KeyError: if protocol not found.
        """
        proto = protocol.lower()
        if proto not in self._data:
            raise KeyError(f"Unknown protocol: {protocol}")
        return self._data[proto]['risk_base']
