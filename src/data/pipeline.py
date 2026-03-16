"""
Data Pipeline Manager — Orchestrates data flow from sources through transforms to sinks.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable

from .sources.base import DataSource, DataSink

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrate data flow: sources → transforms → sinks."""

    def __init__(self):
        self.sources: dict[str, DataSource] = {}
        self.transforms: list[Callable[[list[dict]], list[dict]]] = []
        self.sinks: dict[str, DataSink] = {}
        self._scheduler_thread: threading.Thread | None = None
        self._scheduler_running = False
        self._last_run: dict | None = None

    def add_source(self, name: str, source: DataSource) -> "DataPipeline":
        """Register a data source."""
        if not isinstance(source, DataSource):
            raise TypeError(f"Expected DataSource, got {type(source).__name__}")
        self.sources[name] = source
        return self

    def add_transform(self, transform: Callable) -> "DataPipeline":
        """Add a transform function: list[dict] -> list[dict]."""
        if not callable(transform):
            raise TypeError("Transform must be callable")
        self.transforms.append(transform)
        return self

    def add_sink(self, name: str, sink: DataSink) -> "DataPipeline":
        """Register a data sink."""
        if not isinstance(sink, DataSink):
            raise TypeError(f"Expected DataSink, got {type(sink).__name__}")
        self.sinks[name] = sink
        return self

    def run(self, symbols: list[str], start: str, end: str) -> dict:
        """Execute pipeline: fetch → transform → write. Returns summary."""
        if not self.sources:
            raise ValueError("No sources configured")
        if not self.sinks:
            raise ValueError("No sinks configured")

        summary = {
            "started_at": datetime.now().isoformat(),
            "symbols": symbols,
            "sources": {},
            "sinks": {},
            "errors": [],
        }

        # 1. Fetch from all sources and merge
        merged: dict[str, list[dict]] = {s: [] for s in symbols}
        for src_name, source in self.sources.items():
            try:
                data = source.fetch(symbols, start, end)
                rows_total = 0
                for sym, rows in data.items():
                    if rows:
                        merged[sym].extend(rows)
                        rows_total += len(rows)
                summary["sources"][src_name] = {"rows": rows_total, "status": "ok"}
            except Exception as e:
                summary["sources"][src_name] = {"rows": 0, "status": "error", "error": str(e)}
                summary["errors"].append(f"Source {src_name}: {e}")

        # Deduplicate by date per symbol
        for sym in merged:
            seen = set()
            deduped = []
            for row in sorted(merged[sym], key=lambda r: r.get("date", "")):
                d = row.get("date", "")
                if d not in seen:
                    seen.add(d)
                    deduped.append(row)
            merged[sym] = deduped

        # 2. Apply transforms
        for transform in self.transforms:
            for sym in merged:
                try:
                    merged[sym] = transform(merged[sym])
                except Exception as e:
                    summary["errors"].append(f"Transform on {sym}: {e}")

        # 3. Write to all sinks
        for sink_name, sink in self.sinks.items():
            rows_total = 0
            for sym, rows in merged.items():
                try:
                    written = sink.write(sym, rows)
                    rows_total += written
                except Exception as e:
                    summary["errors"].append(f"Sink {sink_name}/{sym}: {e}")
            summary["sinks"][sink_name] = {"rows": rows_total, "status": "ok"}

        summary["finished_at"] = datetime.now().isoformat()
        self._last_run = summary
        return summary

    def schedule(self, cron: str, symbols: list[str] | None = None,
                 start: str = "2020-01-01", end: str | None = None) -> None:
        """Simple interval-based scheduling. cron format: '{seconds}s' or '{minutes}m' or '{hours}h'."""
        interval = self._parse_interval(cron)
        self._scheduler_running = True

        def _loop():
            while self._scheduler_running:
                actual_end = end or datetime.now().strftime("%Y-%m-%d")
                syms = symbols or ["BTC"]
                try:
                    self.run(syms, start, actual_end)
                except Exception as e:
                    logger.error(f"Scheduled run failed: {e}")
                time.sleep(interval)

        self._scheduler_thread = threading.Thread(target=_loop, daemon=True)
        self._scheduler_thread.start()

    def stop_schedule(self) -> None:
        """Stop the scheduler."""
        self._scheduler_running = False

    @property
    def last_run(self) -> dict | None:
        return self._last_run

    @staticmethod
    def _parse_interval(cron: str) -> float:
        cron = cron.strip().lower()
        if cron.endswith("s"):
            return float(cron[:-1])
        elif cron.endswith("m"):
            return float(cron[:-1]) * 60
        elif cron.endswith("h"):
            return float(cron[:-1]) * 3600
        else:
            raise ValueError(f"Invalid interval format: {cron}. Use '30s', '5m', or '1h'.")
