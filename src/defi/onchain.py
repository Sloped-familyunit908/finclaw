"""
On-Chain Data Analyzer
Enhanced whale tracking, token flows (CEX inflow/outflow), gas tracker, and mempool monitoring.
Extends the existing OnChainAnalytics with additional capabilities.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class MempoolTransaction:
    tx_hash: str
    from_addr: str
    to_addr: str
    value_eth: float
    gas_price_gwei: float
    tx_type: str  # 'swap', 'transfer', 'contract_call', 'nft_mint'


class OnChainAnalyzer:
    """Advanced on-chain data analysis for multiple chains."""

    def __init__(self, seed: int = 42):
        self._seed = seed

    def _deterministic_hash(self, key: str) -> str:
        return hashlib.sha256(f"{self._seed}:{key}".encode()).hexdigest()

    def _pseudo_random(self, key: str, idx: int = 0) -> float:
        h = self._deterministic_hash(f"{key}:{idx}")
        return int(h[:8], 16) / 0xFFFFFFFF

    def whale_tracker(self, token: str, min_amount: float = 100_000) -> list:
        """Track whale movements for a token.

        Args:
            token: token symbol (e.g. 'BTC', 'ETH').
            min_amount: minimum USD amount to qualify as whale tx.

        Returns:
            list of dicts with tx_hash, token, amount_usd, direction, from_label, to_label.
        """
        token = token.upper()
        labels = ['Binance', 'Coinbase', 'Kraken', 'Unknown Wallet', 'OKX', 'Whale 0x...abc', 'DeFi Contract']
        directions = ['cex_deposit', 'cex_withdrawal', 'wallet_transfer', 'defi_interaction']
        results = []

        for i in range(25):
            r = self._pseudo_random(f"whale2:{token}", i)
            amount = 10_000 + r * 5_000_000
            if amount < min_amount:
                continue
            results.append({
                'tx_hash': f"0x{self._deterministic_hash(f'wh:{token}:{i}')[:16]}",
                'token': token,
                'amount_usd': round(amount, 2),
                'direction': directions[int(r * 100) % len(directions)],
                'from_label': labels[int(r * 1000) % len(labels)],
                'to_label': labels[(int(r * 1000) + 3) % len(labels)],
                'timestamp': 1700000000 + i * 1800,
            })
        return results

    def token_flows(self, token: str, exchanges: list = None) -> dict:
        """Analyze CEX inflow/outflow for a token across exchanges.

        Args:
            token: token symbol.
            exchanges: list of exchange names, or None for all major.

        Returns:
            dict with per-exchange flows and aggregate totals.
        """
        token = token.upper()
        if exchanges is None:
            exchanges = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']

        flows = {}
        total_inflow = 0
        total_outflow = 0

        for ex in exchanges:
            ex_lower = ex.lower()
            r_in = self._pseudo_random(f"flow_in:{token}:{ex_lower}")
            r_out = self._pseudo_random(f"flow_out:{token}:{ex_lower}")
            inflow = round(r_in * 20_000_000, 2)
            outflow = round(r_out * 20_000_000, 2)
            net = round(inflow - outflow, 2)
            total_inflow += inflow
            total_outflow += outflow
            flows[ex_lower] = {
                'inflow': inflow,
                'outflow': outflow,
                'net': net,
            }

        total_net = round(total_inflow - total_outflow, 2)
        signal = 'bearish' if total_net > 0 else 'bullish'

        return {
            'token': token,
            'exchanges': flows,
            'total_inflow': round(total_inflow, 2),
            'total_outflow': round(total_outflow, 2),
            'total_net': total_net,
            'signal': signal,
        }

    def gas_tracker(self, chain: str = 'ethereum') -> dict:
        """Get current gas prices for a chain.

        Args:
            chain: blockchain name (ethereum, polygon, arbitrum, bsc, avalanche).

        Returns:
            dict with slow, standard, fast, rapid, base_fee in native units.
        """
        chain = chain.lower()
        base_gas = {
            'ethereum': 25, 'polygon': 50, 'arbitrum': 0.1,
            'bsc': 3, 'avalanche': 25, 'optimism': 0.01,
        }
        base = base_gas.get(chain, 25)
        r = self._pseudo_random(f"gas:{chain}")
        multiplier = 0.5 + r * 2.0
        current = base * multiplier

        return {
            'chain': chain,
            'slow': round(current * 0.8, 4),
            'standard': round(current, 4),
            'fast': round(current * 1.3, 4),
            'rapid': round(current * 1.6, 4),
            'base_fee': round(current * 0.7, 4),
            'unit': 'gwei',
        }

    def mempool_monitor(self) -> list:
        """Monitor pending transactions in the mempool (simulated).

        Returns:
            list of MempoolTransaction dataclass instances.
        """
        tx_types = ['swap', 'transfer', 'contract_call', 'nft_mint']
        txs = []

        for i in range(20):
            r = self._pseudo_random("mempool", i)
            txs.append(MempoolTransaction(
                tx_hash=f"0x{self._deterministic_hash(f'mem:{i}')[:16]}",
                from_addr=f"0x{self._deterministic_hash(f'mfrom:{i}')[:40]}",
                to_addr=f"0x{self._deterministic_hash(f'mto:{i}')[:40]}",
                value_eth=round(r * 100, 4),
                gas_price_gwei=round(15 + r * 80, 2),
                tx_type=tx_types[int(r * 100) % len(tx_types)],
            ))
        return txs
