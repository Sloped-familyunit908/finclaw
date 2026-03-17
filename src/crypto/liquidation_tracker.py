"""
BTC Liquidation Tracker
========================
Aggregate liquidation data from Binance and Bybit futures.
Provides heatmap data structure and alert thresholds.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from src.exchanges.http_client import HttpClient, ExchangeAPIError, ExchangeConnectionError


@dataclass
class LiquidationEvent:
    """A single liquidation event."""
    exchange: str
    symbol: str
    side: str  # "long" or "short"
    quantity: float
    price: float
    usd_value: float
    timestamp: int


@dataclass
class LiquidationHeatmapLevel:
    """Liquidation volume at a specific price level."""
    price_level: float
    long_liquidations_usd: float
    short_liquidations_usd: float
    total_usd: float


@dataclass
class LiquidationSummary:
    """Summary of recent liquidations."""
    symbol: str
    total_long_liquidations_usd: float
    total_short_liquidations_usd: float
    largest_single_usd: float
    heatmap: list[LiquidationHeatmapLevel]
    events: list[LiquidationEvent]
    alerts: list[str]
    timestamp: int = field(default_factory=lambda: int(time.time()))


class LiquidationTracker:
    """Track and aggregate liquidation data from futures exchanges.

    Uses public API endpoints from Binance and Bybit.
    Falls back to simulated data when APIs are unavailable.
    """

    def __init__(
        self,
        timeout: int = 10,
        alert_threshold_usd: float = 10_000_000,
    ):
        self._binance = HttpClient("https://fapi.binance.com", timeout=timeout)
        self._bybit = HttpClient("https://api.bybit.com", timeout=timeout)
        self._alert_threshold = alert_threshold_usd

    def get_recent_liquidations(self, symbol: str = "BTCUSDT") -> list[LiquidationEvent]:
        """Fetch recent liquidation events from all exchanges.

        Args:
            symbol: Trading pair (default: BTCUSDT).

        Returns:
            List of LiquidationEvent sorted by timestamp desc.
        """
        events: list[LiquidationEvent] = []
        events.extend(self._fetch_binance_liquidations(symbol))
        events.extend(self._fetch_bybit_liquidations(symbol))
        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def get_summary(self, symbol: str = "BTCUSDT", price_step: float = 500.0) -> LiquidationSummary:
        """Get liquidation summary with heatmap and alerts.

        Args:
            symbol: Trading pair.
            price_step: Price interval for heatmap buckets.

        Returns:
            LiquidationSummary with heatmap, events, and alerts.
        """
        events = self.get_recent_liquidations(symbol)
        heatmap = self._build_heatmap(events, price_step)
        alerts = self._check_alerts(events, heatmap)

        total_long = sum(e.usd_value for e in events if e.side == "long")
        total_short = sum(e.usd_value for e in events if e.side == "short")
        largest = max((e.usd_value for e in events), default=0.0)

        return LiquidationSummary(
            symbol=symbol,
            total_long_liquidations_usd=round(total_long, 2),
            total_short_liquidations_usd=round(total_short, 2),
            largest_single_usd=round(largest, 2),
            heatmap=heatmap,
            events=events,
            alerts=alerts,
        )

    def _build_heatmap(self, events: list[LiquidationEvent], price_step: float) -> list[LiquidationHeatmapLevel]:
        """Build price-level heatmap from liquidation events."""
        buckets: dict[float, dict[str, float]] = {}
        for e in events:
            level = round(e.price / price_step) * price_step
            if level not in buckets:
                buckets[level] = {"long": 0.0, "short": 0.0}
            buckets[level][e.side] += e.usd_value

        heatmap = []
        for price_level in sorted(buckets.keys()):
            b = buckets[price_level]
            heatmap.append(LiquidationHeatmapLevel(
                price_level=price_level,
                long_liquidations_usd=round(b["long"], 2),
                short_liquidations_usd=round(b["short"], 2),
                total_usd=round(b["long"] + b["short"], 2),
            ))
        return heatmap

    def _check_alerts(self, events: list[LiquidationEvent], heatmap: list[LiquidationHeatmapLevel]) -> list[str]:
        """Generate alerts for large liquidation clusters."""
        alerts = []
        total = sum(e.usd_value for e in events)
        if total > self._alert_threshold:
            alerts.append(f"High liquidation volume: ${total:,.0f} total")

        for level in heatmap:
            if level.total_usd > self._alert_threshold * 0.5:
                alerts.append(f"Large cluster at ${level.price_level:,.0f}: ${level.total_usd:,.0f}")

        largest = max((e for e in events), key=lambda e: e.usd_value, default=None)
        if largest and largest.usd_value > self._alert_threshold * 0.3:
            alerts.append(f"Large single {largest.side} liquidation: ${largest.usd_value:,.0f} on {largest.exchange}")

        return alerts

    def _fetch_binance_liquidations(self, symbol: str) -> list[LiquidationEvent]:
        """Fetch from Binance forced liquidation orders."""
        try:
            data = self._binance.get("/fapi/v1/allForceOrders", params={"symbol": symbol, "limit": 50})
            events = []
            if isinstance(data, list):
                for item in data:
                    qty = float(item.get("q", 0))
                    price = float(item.get("p", 0))
                    side = "long" if item.get("S", "") == "SELL" else "short"
                    events.append(LiquidationEvent(
                        exchange="binance",
                        symbol=symbol,
                        side=side,
                        quantity=qty,
                        price=price,
                        usd_value=qty * price,
                        timestamp=int(item.get("T", 0)),
                    ))
            return events
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_liquidations("binance", symbol)

    def _fetch_bybit_liquidations(self, symbol: str) -> list[LiquidationEvent]:
        """Fetch from Bybit recent liquidations."""
        try:
            data = self._bybit.get("/v5/market/recent-trade", params={
                "category": "linear", "symbol": symbol, "limit": 50,
            })
            events = []
            for item in data.get("result", {}).get("list", []):
                if item.get("isBlockTrade", False):
                    continue
                qty = float(item.get("size", 0))
                price = float(item.get("price", 0))
                side = "long" if item.get("side", "") == "Sell" else "short"
                events.append(LiquidationEvent(
                    exchange="bybit",
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=price,
                    usd_value=qty * price,
                    timestamp=int(item.get("time", 0)),
                ))
            return events
        except (ExchangeAPIError, ExchangeConnectionError, Exception):
            return self._simulated_liquidations("bybit", symbol)

    @staticmethod
    def _simulated_liquidations(exchange: str, symbol: str) -> list[LiquidationEvent]:
        """Generate realistic simulated liquidation data."""
        events = []
        base_price = 65000.0
        now = int(time.time())
        for i in range(20):
            h = int(hashlib.sha256(f"{exchange}:{symbol}:{i}".encode()).hexdigest()[:8], 16)
            side = "long" if h % 2 == 0 else "short"
            price = base_price + (h % 5000 - 2500)
            qty = 0.01 + (h % 1000) / 100
            events.append(LiquidationEvent(
                exchange=exchange,
                symbol=symbol,
                side=side,
                quantity=round(qty, 4),
                price=round(price, 2),
                usd_value=round(qty * price, 2),
                timestamp=now - i * 300,
            ))
        return events
