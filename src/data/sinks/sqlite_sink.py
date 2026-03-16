"""SQLite data sink."""

import os
import sqlite3
from ..sources.base import DataSink


class SQLiteSink(DataSink):
    """Write/read price data to a SQLite database. One table per symbol."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

    def _table_name(self, symbol: str) -> str:
        return f"price_{symbol.replace('-', '_').replace('/', '_').lower()}"

    def _ensure_table(self, symbol: str, columns: list[str]) -> None:
        table = self._table_name(symbol)
        cols = ", ".join(f'"{c}" TEXT' for c in columns)
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})')
        self._conn.commit()

    def write(self, symbol: str, data: list[dict]) -> int:
        if not data:
            return 0
        columns = list(data[0].keys())
        self._ensure_table(symbol, columns)
        table = self._table_name(symbol)
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(f'"{c}"' for c in columns)
        self._conn.execute(f'DELETE FROM "{table}"')  # overwrite
        for row in data:
            values = [str(row.get(c, "")) for c in columns]
            self._conn.execute(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})', values)
        self._conn.commit()
        return len(data)

    def read(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        table = self._table_name(symbol)
        try:
            query = f'SELECT * FROM "{table}"'
            conditions = []
            params = []
            if start:
                conditions.append('"date" >= ?')
                params.append(start)
            if end:
                conditions.append('"date" <= ?')
                params.append(end)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += ' ORDER BY "date"'
            rows = self._conn.execute(query, params).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for k, v in d.items():
                    if k != "date":
                        try:
                            d[k] = float(v)
                        except (ValueError, TypeError):
                            pass
                result.append(d)
            return result
        except sqlite3.OperationalError:
            return []

    def close(self) -> None:
        self._conn.close()
