"""
Data Cache
File-based caching for price data to avoid redundant API calls.
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheEntry:
    key: str
    data: list[dict]
    timestamp: float
    ttl: float  # seconds


class DataCache:
    """Simple file-based data cache with TTL."""

    def __init__(self, cache_dir: str = ".finclaw_cache", default_ttl: float = 3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._memory: dict[str, CacheEntry] = {}
        os.makedirs(cache_dir, exist_ok=True)

    def _file_path(self, key: str) -> str:
        safe = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe}.json")

    def get(self, key: str) -> Optional[list[dict]]:
        """Get cached data. Returns None if expired or missing."""
        # Memory cache first
        if key in self._memory:
            entry = self._memory[key]
            if time.time() - entry.timestamp < entry.ttl:
                return entry.data
            del self._memory[key]

        # File cache
        path = self._file_path(key)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    raw = json.load(f)
                if time.time() - raw["timestamp"] < raw.get("ttl", self.default_ttl):
                    self._memory[key] = CacheEntry(
                        key=key, data=raw["data"],
                        timestamp=raw["timestamp"], ttl=raw.get("ttl", self.default_ttl)
                    )
                    return raw["data"]
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def set(self, key: str, data: list[dict], ttl: float = None):
        """Store data in cache."""
        ttl = ttl or self.default_ttl
        ts = time.time()
        self._memory[key] = CacheEntry(key=key, data=data, timestamp=ts, ttl=ttl)

        path = self._file_path(key)
        with open(path, "w") as f:
            json.dump({"key": key, "data": data, "timestamp": ts, "ttl": ttl}, f)

    def invalidate(self, key: str):
        self._memory.pop(key, None)
        path = self._file_path(key)
        if os.path.exists(path):
            os.remove(path)

    def clear(self):
        self._memory.clear()
        for f in os.listdir(self.cache_dir):
            if f.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, f))
