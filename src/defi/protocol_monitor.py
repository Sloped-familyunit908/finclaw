"""
DeFi Protocol Monitor
TVL tracking, yield farming, pool info, and liquidation monitoring via simulated DeFiLlama-style data.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class PoolInfo:
    dex: str
    pair: str
    tvl: float
    volume_24h: float
    fee_tier: float
    apy: float


@dataclass
class Liquidation:
    protocol: str
    user_addr: str
    collateral_token: str
    debt_token: str
    amount_usd: float
    timestamp: int


# Simulated TVL data (deterministic)
_TVL_DATA = {
    'aave': {'tvl': 12_500_000_000, 'change_1d': -1.2, 'change_7d': 3.5, 'chain_tvls': {'ethereum': 8e9, 'polygon': 2e9, 'arbitrum': 2.5e9}},
    'lido': {'tvl': 18_000_000_000, 'change_1d': 0.8, 'change_7d': 2.1, 'chain_tvls': {'ethereum': 18e9}},
    'uniswap': {'tvl': 5_200_000_000, 'change_1d': -0.5, 'change_7d': 1.8, 'chain_tvls': {'ethereum': 3.5e9, 'arbitrum': 1e9, 'polygon': 0.7e9}},
    'curve': {'tvl': 4_800_000_000, 'change_1d': 0.3, 'change_7d': -0.9, 'chain_tvls': {'ethereum': 3.8e9, 'arbitrum': 1e9}},
    'compound': {'tvl': 2_800_000_000, 'change_1d': -0.2, 'change_7d': 1.1, 'chain_tvls': {'ethereum': 2.8e9}},
    'makerdao': {'tvl': 8_100_000_000, 'change_1d': 0.1, 'change_7d': 0.5, 'chain_tvls': {'ethereum': 8.1e9}},
    'pancakeswap': {'tvl': 2_100_000_000, 'change_1d': 1.5, 'change_7d': 4.2, 'chain_tvls': {'bsc': 2.1e9}},
    'gmx': {'tvl': 600_000_000, 'change_1d': 2.1, 'change_7d': 5.0, 'chain_tvls': {'arbitrum': 450e6, 'avalanche': 150e6}},
}

_YIELD_DATA = {
    'aave': [
        {'pool': 'USDC', 'apy': 4.5, 'tvl': 2e9, 'reward_apy': 0.8},
        {'pool': 'ETH', 'apy': 2.1, 'tvl': 3e9, 'reward_apy': 0.5},
        {'pool': 'WBTC', 'apy': 1.8, 'tvl': 1.5e9, 'reward_apy': 0.3},
    ],
    'curve': [
        {'pool': '3pool', 'apy': 6.2, 'tvl': 3.5e9, 'reward_apy': 3.1},
        {'pool': 'stETH/ETH', 'apy': 5.1, 'tvl': 2.8e9, 'reward_apy': 2.0},
        {'pool': 'tricrypto', 'apy': 8.5, 'tvl': 800e6, 'reward_apy': 4.2},
    ],
    'compound': [
        {'pool': 'USDC', 'apy': 3.8, 'tvl': 2e9, 'reward_apy': 0.6},
        {'pool': 'ETH', 'apy': 1.9, 'tvl': 1.2e9, 'reward_apy': 0.4},
    ],
    'pancakeswap': [
        {'pool': 'CAKE/BNB', 'apy': 25.0, 'tvl': 400e6, 'reward_apy': 18.0},
        {'pool': 'USDT/BUSD', 'apy': 8.5, 'tvl': 500e6, 'reward_apy': 5.0},
    ],
}


class ProtocolMonitor:
    """Monitor DeFi protocols for TVL, yields, pools, and liquidations."""

    def __init__(self, seed: int = 42):
        self._seed = seed

    def _deterministic_hash(self, key: str) -> str:
        return hashlib.sha256(f"{self._seed}:{key}".encode()).hexdigest()

    def _pseudo_random(self, key: str, idx: int = 0) -> float:
        h = self._deterministic_hash(f"{key}:{idx}")
        return int(h[:8], 16) / 0xFFFFFFFF

    def get_tvl(self, protocol: str) -> dict:
        """Get TVL data for a protocol (DeFiLlama-style).

        Args:
            protocol: protocol name (e.g. 'aave', 'lido').

        Returns:
            dict with tvl, change_1d, change_7d, chain_tvls.

        Raises:
            KeyError: if protocol not found.
        """
        key = protocol.lower()
        if key not in _TVL_DATA:
            raise KeyError(f"Unknown protocol: {protocol}")
        data = _TVL_DATA[key].copy()
        data['protocol'] = key
        return data

    def get_yields(self, protocol: str) -> list:
        """Get yield farming APY data for a protocol.

        Args:
            protocol: protocol name.

        Returns:
            list of dicts with pool, apy, tvl, reward_apy.

        Raises:
            KeyError: if protocol has no yield data.
        """
        key = protocol.lower()
        if key not in _YIELD_DATA:
            raise KeyError(f"No yield data for: {protocol}")
        return [{'protocol': key, **y} for y in _YIELD_DATA[key]]

    def get_pool_info(self, dex: str, pair: str) -> dict:
        """Get pool information for a DEX pair.

        Args:
            dex: DEX name (e.g. 'uniswap', 'curve').
            pair: trading pair (e.g. 'ETH/USDC').

        Returns:
            dict with dex, pair, tvl, volume_24h, fee_tier, apy.
        """
        dex_lower = dex.lower()
        pair_upper = pair.upper()
        r = self._pseudo_random(f"pool:{dex_lower}:{pair_upper}")

        fee_tiers = {'uniswap': 0.003, 'pancakeswap': 0.0025, 'curve': 0.0004, 'sushiswap': 0.003}
        fee = fee_tiers.get(dex_lower, 0.003)

        tvl = 10_000_000 + r * 500_000_000
        volume = tvl * (0.05 + r * 0.3)
        apy = (volume * fee * 365) / tvl * 100

        return {
            'dex': dex_lower,
            'pair': pair_upper,
            'tvl': round(tvl, 2),
            'volume_24h': round(volume, 2),
            'fee_tier': fee,
            'apy': round(apy, 2),
        }

    def monitor_liquidations(self, protocol: str) -> list:
        """Monitor recent liquidation events for a protocol.

        Args:
            protocol: lending protocol name (e.g. 'aave', 'compound').

        Returns:
            list of Liquidation dataclass instances.
        """
        key = protocol.lower()
        collateral_tokens = ['ETH', 'WBTC', 'stETH', 'LINK', 'UNI']
        debt_tokens = ['USDC', 'USDT', 'DAI']
        liquidations = []

        for i in range(15):
            r = self._pseudo_random(f"liq:{key}", i)
            amount = 1000 + r * 500_000
            if amount < 5000:  # filter small ones
                continue
            liquidations.append(Liquidation(
                protocol=key,
                user_addr=f"0x{self._deterministic_hash(f'liqaddr:{key}:{i}')[:40]}",
                collateral_token=collateral_tokens[int(r * 100) % len(collateral_tokens)],
                debt_token=debt_tokens[int(r * 1000) % len(debt_tokens)],
                amount_usd=round(amount, 2),
                timestamp=1700000000 + i * 600,
            ))
        return liquidations

    def list_protocols(self) -> list[str]:
        """List all available protocols with TVL data."""
        return sorted(_TVL_DATA.keys())

    def top_protocols(self, n: int = 5) -> list[dict]:
        """Get top N protocols by TVL.

        Args:
            n: number of protocols to return.

        Returns:
            list of dicts sorted by TVL descending.
        """
        protos = []
        for name, data in _TVL_DATA.items():
            protos.append({'protocol': name, **data})
        protos.sort(key=lambda x: x['tvl'], reverse=True)
        return protos[:n]
