"""
On-Chain Analytics
Whale tracking, exchange flows, active addresses, and gas tracking.
Uses simulated data for deterministic testing.
"""

import hashlib
import math
from dataclasses import dataclass


@dataclass
class WhaleTransaction:
    tx_hash: str
    token: str
    amount_usd: float
    from_addr: str
    to_addr: str
    direction: str  # 'in_exchange', 'out_exchange', 'transfer'
    timestamp: int


class OnChainAnalytics:
    """Simulated on-chain analytics for crypto tokens."""

    def __init__(self, seed: int = 42):
        self._seed = seed

    def _deterministic_hash(self, key: str) -> str:
        return hashlib.sha256(f"{self._seed}:{key}".encode()).hexdigest()

    def _pseudo_random(self, key: str, idx: int) -> float:
        h = self._deterministic_hash(f"{key}:{idx}")
        return int(h[:8], 16) / 0xFFFFFFFF

    def whale_transactions(self, token: str, min_usd: float = 100000) -> list[WhaleTransaction]:
        """Get simulated whale transactions for a token.

        Args:
            token: token symbol (e.g. 'BTC', 'ETH').
            min_usd: minimum USD value to qualify as whale.

        Returns:
            List of WhaleTransaction.
        """
        token = token.upper()
        txs = []
        directions = ['in_exchange', 'out_exchange', 'transfer']

        for i in range(20):
            r = self._pseudo_random(f"whale:{token}", i)
            amount = 50000 + r * 2_000_000
            if amount < min_usd:
                continue
            tx_hash = self._deterministic_hash(f"tx:{token}:{i}")[:16]
            direction = directions[int(r * 100) % 3]
            txs.append(WhaleTransaction(
                tx_hash=f"0x{tx_hash}",
                token=token,
                amount_usd=round(amount, 2),
                from_addr=f"0x{self._deterministic_hash(f'from:{token}:{i}')[:40]}",
                to_addr=f"0x{self._deterministic_hash(f'to:{token}:{i}')[:40]}",
                direction=direction,
                timestamp=1700000000 + i * 3600,
            ))
        return txs

    def exchange_flows(self, token: str) -> dict:
        """Get net exchange inflow/outflow for a token.

        Returns:
            dict with inflow, outflow, net, signal.
        """
        token = token.upper()
        r1 = self._pseudo_random(f"flow_in:{token}", 0)
        r2 = self._pseudo_random(f"flow_out:{token}", 0)

        inflow = round(r1 * 50_000_000, 2)
        outflow = round(r2 * 50_000_000, 2)
        net = round(inflow - outflow, 2)

        # Net positive inflow = bearish (selling pressure)
        signal = 'bearish' if net > 0 else 'bullish'

        return {
            'token': token,
            'inflow': inflow,
            'outflow': outflow,
            'net': net,
            'signal': signal,
        }

    def active_addresses(self, token: str) -> dict:
        """Get active address metrics.

        Returns:
            dict with active_24h, active_7d, change_pct, trend.
        """
        token = token.upper()
        r1 = self._pseudo_random(f"active24:{token}", 0)
        r2 = self._pseudo_random(f"active7d:{token}", 0)

        active_24h = int(10000 + r1 * 500000)
        active_7d = int(50000 + r2 * 2000000)
        change_pct = round((r1 - 0.5) * 40, 2)  # -20% to +20%
        trend = 'increasing' if change_pct > 0 else 'decreasing'

        return {
            'token': token,
            'active_24h': active_24h,
            'active_7d': active_7d,
            'change_pct': change_pct,
            'trend': trend,
        }

    def gas_tracker(self) -> dict:
        """Get current Ethereum gas prices (simulated).

        Returns:
            dict with slow, standard, fast, base_fee (in gwei).
        """
        r = self._pseudo_random("gas", 0)
        base = 15 + r * 80

        return {
            'slow': round(base * 0.8, 1),
            'standard': round(base, 1),
            'fast': round(base * 1.3, 1),
            'rapid': round(base * 1.6, 1),
            'base_fee': round(base * 0.7, 1),
            'unit': 'gwei',
        }
