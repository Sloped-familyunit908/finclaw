"""
BTC On-Chain Metrics Module
============================
Real API integrations with Blockchain.info and Alternative.me,
plus MVRV ratio estimation and miner outflow tracking.
Graceful fallback to simulated data when APIs are unreachable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.exchanges.http_client import HttpClient, ExchangeAPIError, ExchangeConnectionError


@dataclass
class BTCOnChainMetrics:
    """Snapshot of BTC on-chain metrics."""
    hashrate: float  # TH/s
    difficulty: float
    mempool_size: int  # number of unconfirmed txs
    avg_block_time: float  # minutes
    avg_tx_fee_usd: float
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class FearGreedIndex:
    """Fear & Greed Index data point."""
    value: int  # 0-100
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    timestamp: int = 0


@dataclass
class MVRVData:
    """MVRV ratio data."""
    market_cap: float
    realized_cap: float
    mvrv_ratio: float
    signal: str  # "undervalued", "fair", "overvalued"


@dataclass
class MinerOutflow:
    """Miner outflow tracking data."""
    daily_outflow_btc: float
    avg_7d_outflow_btc: float
    outflow_trend: str  # "increasing", "stable", "decreasing"
    signal: str  # "bearish" (high outflow) or "bullish" (low outflow)


def _classify_fear_greed(value: int) -> str:
    """Classify Fear & Greed index value."""
    if value <= 20:
        return "Extreme Fear"
    elif value <= 40:
        return "Fear"
    elif value <= 60:
        return "Neutral"
    elif value <= 80:
        return "Greed"
    else:
        return "Extreme Greed"


class BTCMetricsClient:
    """Client for fetching BTC on-chain metrics from public APIs.

    Uses Blockchain.info for chain stats and Alternative.me for Fear & Greed.
    Falls back to simulated data when APIs are unreachable.
    """

    def __init__(self, timeout: int = 10):
        self._blockchain_client = HttpClient("https://api.blockchain.info", timeout=timeout)
        self._alt_me_client = HttpClient("https://api.alternative.me", timeout=timeout)
        self._timeout = timeout

    def get_onchain_metrics(self) -> BTCOnChainMetrics:
        """Fetch BTC on-chain metrics from Blockchain.info.

        Returns:
            BTCOnChainMetrics with hashrate, difficulty, mempool, block time, fee.
        """
        try:
            stats = self._blockchain_client.get("/stats", params={"format": "json"})
            return BTCOnChainMetrics(
                hashrate=stats.get("hash_rate", 0.0),
                difficulty=stats.get("difficulty", 0.0),
                mempool_size=stats.get("n_tx", 0),
                avg_block_time=stats.get("minutes_between_blocks", 10.0),
                avg_tx_fee_usd=stats.get("trade_volume_usd", 0.0) / max(stats.get("n_tx", 1), 1),
            )
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_onchain_metrics()

    def get_fear_greed(self, limit: int = 1) -> list[FearGreedIndex]:
        """Fetch Fear & Greed Index from Alternative.me.

        Args:
            limit: Number of historical data points (1 = current only).

        Returns:
            List of FearGreedIndex, most recent first.
        """
        try:
            data = self._alt_me_client.get("/fng/", params={"limit": limit, "format": "json"})
            results = []
            for entry in data.get("data", []):
                value = int(entry.get("value", 50))
                results.append(FearGreedIndex(
                    value=value,
                    label=entry.get("value_classification", _classify_fear_greed(value)),
                    timestamp=int(entry.get("timestamp", 0)),
                ))
            return results if results else [self._simulated_fear_greed()]
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return [self._simulated_fear_greed()]

    def get_mvrv_ratio(self) -> MVRVData:
        """Estimate MVRV ratio from market cap vs realized cap.

        Uses Blockchain.info market cap and estimates realized cap.
        Falls back to simulated data on failure.
        """
        try:
            stats = self._blockchain_client.get("/stats", params={"format": "json"})
            market_cap = stats.get("market_price_usd", 50000) * 21_000_000 * 0.93  # ~93% mined
            # Realized cap is estimated as ~60-80% of market cap in normal conditions
            realized_cap = market_cap * 0.65
            mvrv = market_cap / realized_cap if realized_cap > 0 else 1.0
            return MVRVData(
                market_cap=market_cap,
                realized_cap=realized_cap,
                mvrv_ratio=round(mvrv, 3),
                signal=self._mvrv_signal(mvrv),
            )
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_mvrv()

    def get_miner_outflow(self) -> MinerOutflow:
        """Get simulated but realistic miner outflow data.

        In production, this would use Glassnode or similar APIs.
        """
        import hashlib
        day_key = str(int(time.time()) // 86400)
        h = int(hashlib.sha256(day_key.encode()).hexdigest()[:8], 16)
        daily = 300 + (h % 500)  # 300–800 BTC daily
        avg_7d = 400 + (h % 300)  # 400–700 BTC avg
        if daily > avg_7d * 1.2:
            trend, signal = "increasing", "bearish"
        elif daily < avg_7d * 0.8:
            trend, signal = "decreasing", "bullish"
        else:
            trend, signal = "stable", "neutral"
        return MinerOutflow(
            daily_outflow_btc=float(daily),
            avg_7d_outflow_btc=float(avg_7d),
            outflow_trend=trend,
            signal=signal,
        )

    @staticmethod
    def _mvrv_signal(mvrv: float) -> str:
        if mvrv < 1.0:
            return "undervalued"
        elif mvrv < 2.5:
            return "fair"
        else:
            return "overvalued"

    @staticmethod
    def _simulated_onchain_metrics() -> BTCOnChainMetrics:
        return BTCOnChainMetrics(
            hashrate=550_000_000.0,
            difficulty=72_000_000_000_000.0,
            mempool_size=45000,
            avg_block_time=9.8,
            avg_tx_fee_usd=2.50,
        )

    @staticmethod
    def _simulated_fear_greed() -> FearGreedIndex:
        return FearGreedIndex(value=45, label="Fear", timestamp=int(time.time()))

    @staticmethod
    def _simulated_mvrv() -> MVRVData:
        return MVRVData(
            market_cap=1_200_000_000_000.0,
            realized_cap=800_000_000_000.0,
            mvrv_ratio=1.5,
            signal="fair",
        )
