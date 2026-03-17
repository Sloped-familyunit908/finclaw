"""
Lightning Network Monitor
==========================
Monitor Lightning Network statistics via 1ML.com API.
Tracks network capacity, node count, channel count, and fee rates.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from src.exchanges.http_client import HttpClient, ExchangeAPIError, ExchangeConnectionError


@dataclass
class LightningStats:
    """Lightning Network statistics snapshot."""
    capacity_btc: float
    capacity_usd: float
    node_count: int
    channel_count: int
    avg_fee_rate: float  # satoshis per hop
    avg_base_fee: float  # millisatoshis
    avg_channel_size_btc: float
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class LightningNode:
    """Top Lightning Network node by capacity."""
    alias: str
    pub_key: str
    capacity_btc: float
    channel_count: int
    first_seen: int = 0


class LightningMonitor:
    """Monitor Lightning Network via 1ML.com API.

    Falls back to simulated data when API is unreachable.
    """

    def __init__(self, timeout: int = 10, btc_price_usd: float = 65000.0):
        self._client = HttpClient("https://1ml.com", timeout=timeout)
        self._btc_price = btc_price_usd

    def get_network_stats(self) -> LightningStats:
        """Fetch current Lightning Network statistics.

        Returns:
            LightningStats with capacity, node/channel counts, fees.
        """
        try:
            data = self._client.get("/api/v1/statistics", headers={"Accept": "application/json"})
            latest = data.get("latest", data)
            capacity_sat = float(latest.get("total_capacity", {}).get("value", 0))
            capacity_btc = capacity_sat / 1e8 if capacity_sat > 1000 else capacity_sat
            node_count = int(latest.get("node_count", {}).get("value", 0))
            channel_count = int(latest.get("channel_count", {}).get("value", 0))
            avg_fee = float(latest.get("avg_fee_rate", {}).get("value", 0))
            avg_base = float(latest.get("avg_base_fee", {}).get("value", 0))

            avg_ch_size = capacity_btc / channel_count if channel_count > 0 else 0

            return LightningStats(
                capacity_btc=round(capacity_btc, 4),
                capacity_usd=round(capacity_btc * self._btc_price, 2),
                node_count=node_count,
                channel_count=channel_count,
                avg_fee_rate=avg_fee,
                avg_base_fee=avg_base,
                avg_channel_size_btc=round(avg_ch_size, 6),
            )
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_stats()

    def get_top_nodes(self, limit: int = 10) -> list[LightningNode]:
        """Fetch top nodes by capacity.

        Args:
            limit: Number of nodes to return.

        Returns:
            List of LightningNode sorted by capacity desc.
        """
        try:
            data = self._client.get("/api/v1/node/rank/capacity", headers={"Accept": "application/json"})
            nodes = []
            entries = data if isinstance(data, list) else data.get("nodes", data.get("list", []))
            for item in entries[:limit]:
                cap_sat = float(item.get("capacity", 0))
                nodes.append(LightningNode(
                    alias=item.get("alias", "Unknown"),
                    pub_key=item.get("pub_key", item.get("publickey", "")),
                    capacity_btc=round(cap_sat / 1e8, 4) if cap_sat > 1000 else round(cap_sat, 4),
                    channel_count=int(item.get("channelcount", item.get("channel_count", 0))),
                ))
            return nodes if nodes else self._simulated_top_nodes(limit)
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_top_nodes(limit)

    def _simulated_stats(self) -> LightningStats:
        """Realistic simulated Lightning Network stats."""
        return LightningStats(
            capacity_btc=5200.0,
            capacity_usd=5200.0 * self._btc_price,
            node_count=16500,
            channel_count=52000,
            avg_fee_rate=150.0,
            avg_base_fee=1000.0,
            avg_channel_size_btc=0.1,
        )

    @staticmethod
    def _simulated_top_nodes(limit: int) -> list[LightningNode]:
        """Generate simulated top nodes."""
        names = [
            "ACINQ", "Bitfinex", "CoinGate", "LNBig", "River Financial",
            "Kraken", "Wallet of Satoshi", "Fold", "OpenNode", "Strike",
            "BlueWallet", "Muun", "Phoenix", "Breez", "Moon",
        ]
        nodes = []
        for i in range(min(limit, len(names))):
            h = int(hashlib.sha256(names[i].encode()).hexdigest()[:8], 16)
            nodes.append(LightningNode(
                alias=names[i],
                pub_key=hashlib.sha256(names[i].encode()).hexdigest()[:66],
                capacity_btc=round(50 + (h % 500), 2),
                channel_count=100 + (h % 2000),
            ))
        return sorted(nodes, key=lambda n: n.capacity_btc, reverse=True)
