"""
In-memory + file-backed market data storage.
Stores ticks and candles with optional CSV export.
"""

import csv
import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MarketStore:
    """In-memory market data store with file-backed persistence and CSV export."""

    def __init__(self, data_dir: str | None = None, max_ticks: int = 10000, max_candles: int = 5000):
        self.data_dir = data_dir
        self.max_ticks = max_ticks
        self.max_candles = max_candles

        # {exchange: {symbol: [tick_data]}}
        self._ticks: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        # {exchange: {symbol: [candle_data]}}
        self._candles: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        self._stats: dict[str, int] = {"ticks_stored": 0, "candles_stored": 0}

        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

    def store_tick(self, exchange: str, symbol: str, data: dict) -> None:
        """Store a tick data point."""
        tick = {**data, "_stored_at": time.time()}
        ticks = self._ticks[exchange][symbol]
        ticks.append(tick)
        if len(ticks) > self.max_ticks:
            ticks[:] = ticks[-self.max_ticks:]
        self._stats["ticks_stored"] += 1

    def store_candle(self, exchange: str, symbol: str, candle: dict) -> None:
        """Store a candle (OHLCV) data point. Deduplicates by timestamp."""
        candles = self._candles[exchange][symbol]
        ts = candle.get("timestamp")
        # Update existing candle with same timestamp (for live updates)
        for i, c in enumerate(candles):
            if c.get("timestamp") == ts:
                candles[i] = {**candle, "_stored_at": time.time()}
                return
        candle_entry = {**candle, "_stored_at": time.time()}
        candles.append(candle_entry)
        if len(candles) > self.max_candles:
            candles[:] = candles[-self.max_candles:]
        self._stats["candles_stored"] += 1

    def get_ticks(self, exchange: str, symbol: str, limit: int | None = None) -> list[dict]:
        """Get stored ticks, optionally limited."""
        ticks = self._ticks.get(exchange, {}).get(symbol, [])
        if limit:
            return ticks[-limit:]
        return list(ticks)

    def get_candles(
        self, exchange: str, symbol: str,
        start: float | None = None, end: float | None = None,
    ) -> list[dict]:
        """Get candles in a time range (start/end as epoch ms or seconds)."""
        candles = self._candles.get(exchange, {}).get(symbol, [])
        if start is None and end is None:
            return list(candles)

        result = []
        for c in candles:
            ts = c.get("timestamp", 0)
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            result.append(c)
        return result

    def get_latest_tick(self, exchange: str, symbol: str) -> dict | None:
        """Get the most recent tick."""
        ticks = self._ticks.get(exchange, {}).get(symbol, [])
        return ticks[-1] if ticks else None

    def get_latest_candle(self, exchange: str, symbol: str) -> dict | None:
        """Get the most recent candle."""
        candles = self._candles.get(exchange, {}).get(symbol, [])
        return candles[-1] if candles else None

    def export_csv(self, exchange: str, symbol: str, path: str, data_type: str = "candles") -> int:
        """Export data to CSV file. Returns number of rows written."""
        if data_type == "candles":
            data = self.get_candles(exchange, symbol)
        else:
            data = self.get_ticks(exchange, symbol)

        if not data:
            return 0

        # Exclude internal fields
        fields = [k for k in data[0].keys() if not k.startswith("_")]

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in data:
                writer.writerow({k: v for k, v in row.items() if not k.startswith("_")})

        return len(data)

    def save_snapshot(self, exchange: str, symbol: str) -> str | None:
        """Save current data to JSON file in data_dir."""
        if not self.data_dir:
            return None
        filename = f"{exchange}_{symbol}_{int(time.time())}.json"
        path = os.path.join(self.data_dir, filename)
        snapshot = {
            "exchange": exchange,
            "symbol": symbol,
            "ticks": self.get_ticks(exchange, symbol, limit=1000),
            "candles": self.get_candles(exchange, symbol),
            "exported_at": datetime.now().isoformat(),
        }
        with open(path, "w") as f:
            json.dump(snapshot, f, default=str)
        return path

    def clear(self, exchange: str | None = None, symbol: str | None = None) -> None:
        """Clear stored data."""
        if exchange and symbol:
            self._ticks[exchange][symbol] = []
            self._candles[exchange][symbol] = []
        elif exchange:
            self._ticks[exchange] = defaultdict(list)
            self._candles[exchange] = defaultdict(list)
        else:
            self._ticks.clear()
            self._candles.clear()

    @property
    def stats(self) -> dict:
        total_ticks = sum(len(t) for ex in self._ticks.values() for t in ex.values())
        total_candles = sum(len(c) for ex in self._candles.values() for c in ex.values())
        return {
            **self._stats,
            "ticks_in_memory": total_ticks,
            "candles_in_memory": total_candles,
        }
