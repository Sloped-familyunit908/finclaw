"""
Data Cache — SQLite Backend
High-performance SQLite-based caching with TTL invalidation and statistics.
"""

import json
import os
import sqlite3
import time
import threading
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int
    misses: int
    total_entries: int
    size_bytes: int
    hit_rate: float
    expired_purged: int


class DataCache:
    """SQLite-backed data cache with TTL and statistics."""

    def __init__(self, cache_dir: str = ".finclaw_cache", default_ttl: float = 3600,
                 db_name: str = "cache.db"):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._purged = 0
        self._memory: dict[str, tuple[list[dict], float, float]] = {}  # key -> (data, ts, ttl)
        self._lock = threading.Lock()

        os.makedirs(cache_dir, exist_ok=True)
        self._db_path = os.path.join(cache_dir, db_name)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(timestamp)")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def get(self, key: str) -> Optional[list[dict]]:
        """Get cached data. Returns None if expired or missing."""
        now = time.time()

        # Memory cache first
        with self._lock:
            if key in self._memory:
                data, ts, ttl = self._memory[key]
                if now - ts < ttl:
                    self._hits += 1
                    return data
                del self._memory[key]

        # SQLite fallback
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT data, timestamp, ttl FROM cache WHERE key = ?", (key,)
                ).fetchone()
        except sqlite3.Error:
            self._misses += 1
            return None

        if row:
            data_str, ts, ttl = row
            if now - ts < ttl:
                data = json.loads(data_str)
                with self._lock:
                    self._memory[key] = (data, ts, ttl)
                    self._hits += 1
                return data
            # Expired — clean up
            try:
                with self._conn() as conn:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                self._purged += 1
            except sqlite3.Error:
                pass

        self._misses += 1
        return None

    def set(self, key: str, data: list[dict], ttl: float = None) -> None:
        """Store data in cache."""
        ttl = ttl or self.default_ttl
        ts = time.time()
        data_str = json.dumps(data)

        with self._lock:
            self._memory[key] = (data, ts, ttl)

        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, timestamp, ttl) VALUES (?, ?, ?, ?)",
                    (key, data_str, ts, ttl),
                )
        except sqlite3.Error:
            pass  # Memory cache still works

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        with self._lock:
            self._memory.pop(key, None)
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        except sqlite3.Error:
            pass

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._memory.clear()
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM cache")
        except sqlite3.Error:
            pass

    def purge_expired(self) -> int:
        """Remove all expired entries. Returns count purged."""
        now = time.time()
        count = 0

        with self._lock:
            expired_keys = [
                k for k, (_, ts, ttl) in self._memory.items()
                if now - ts >= ttl
            ]
            for k in expired_keys:
                del self._memory[k]
                count += 1

        try:
            with self._conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE (? - timestamp) >= ttl", (now,)
                )
                count += cursor.rowcount
        except sqlite3.Error:
            pass

        self._purged += count
        return count

    def stats(self) -> CacheStats:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        try:
            size = os.path.getsize(self._db_path)
        except OSError:
            size = 0

        try:
            with self._conn() as conn:
                row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
                entries = row[0] if row else 0
        except sqlite3.Error:
            entries = len(self._memory)

        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            total_entries=entries,
            size_bytes=size,
            hit_rate=round(hit_rate, 4),
            expired_purged=self._purged,
        )

    def keys(self) -> list[str]:
        """List all valid (non-expired) cache keys."""
        now = time.time()
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT key FROM cache WHERE (? - timestamp) < ttl", (now,)
                ).fetchall()
                return [r[0] for r in rows]
        except sqlite3.Error:
            return list(self._memory.keys())
