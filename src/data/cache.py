"""
Data Cache Layer v2.6.0
SQLite-backed cache with max_age, stats, and DataFrame support.
"""

import json
import os
import sqlite3
import time
from typing import Any, Optional


class DataCache:
    """SQLite-based data cache with TTL and statistics."""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.finclaw/cache")
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._db_path = os.path.join(cache_dir, "cache.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    data_type TEXT DEFAULT 'json'
                )
            """)

    def get(self, key: str, max_age_hours: int = 24) -> Any:
        """Get cached data. Returns None if expired or missing."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT data, created_at, data_type FROM cache WHERE key = ?", (key,)
                ).fetchone()
        except sqlite3.Error:
            return None

        if not row:
            return None

        data_str, created_at, data_type = row
        age_hours = (time.time() - created_at) / 3600
        if age_hours > max_age_hours:
            return None

        if data_type == "dataframe":
            try:
                import pandas as pd
                parsed = json.loads(data_str)
                index = None
                if parsed.get("index"):
                    try:
                        index = pd.to_datetime(parsed["index"], utc=True)
                    except Exception:
                        index = parsed["index"]
                return pd.DataFrame(parsed["data"], columns=parsed["columns"], index=index)
            except Exception:
                return json.loads(data_str)
        return json.loads(data_str)

    def set(self, key: str, data: Any) -> None:
        """Store data in cache. Supports DataFrames and JSON-serializable objects."""
        try:
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                data_str = json.dumps({
                    "columns": data.columns.tolist(),
                    "data": data.values.tolist(),
                    "index": [str(i) for i in data.index],
                })
                data_type = "dataframe"
            else:
                data_str = json.dumps(data, default=str)
                data_type = "json"
        except ImportError:
            data_str = json.dumps(data, default=str)
            data_type = "json"

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, created_at, data_type) VALUES (?, ?, ?, ?)",
                    (key, data_str, time.time(), data_type),
                )
        except sqlite3.Error:
            pass

    def clear(self, older_than_days: int = 0) -> int:
        """Clear cache entries. If older_than_days > 0, only clear old entries."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                if older_than_days > 0:
                    cutoff = time.time() - older_than_days * 86400
                    cursor = conn.execute("DELETE FROM cache WHERE created_at < ?", (cutoff,))
                else:
                    cursor = conn.execute("DELETE FROM cache")
                return cursor.rowcount
        except sqlite3.Error:
            return 0

    def stats(self) -> dict:
        """Return cache statistics."""
        try:
            size_kb = os.path.getsize(self._db_path) / 1024
        except OSError:
            size_kb = 0

        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
                entries = row[0] if row else 0
        except sqlite3.Error:
            entries = 0

        return {"entries": entries, "size_kb": round(size_kb, 2), "cache_dir": self.cache_dir}

    def keys(self) -> list:
        """List all cache keys."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute("SELECT key FROM cache").fetchall()
                return [r[0] for r in rows]
        except sqlite3.Error:
            return []
