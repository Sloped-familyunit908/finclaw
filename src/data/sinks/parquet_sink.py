"""Parquet data sink (simple implementation using struct packing)."""

import json
import os
from ..sources.base import DataSink


class ParquetSink(DataSink):
    """Write/read price data to Parquet-like JSON files.

    This is a lightweight implementation that stores data in columnar JSON
    format. For production use with real Parquet, install pyarrow/fastparquet.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self._use_pyarrow = False
        try:
            import pyarrow  # noqa: F401
            import pyarrow.parquet  # noqa: F401
            self._use_pyarrow = True
        except ImportError:
            pass

    def _path(self, symbol: str) -> str:
        ext = ".parquet" if self._use_pyarrow else ".parquet.json"
        return os.path.join(self.base_dir, f"{symbol}{ext}")

    def write(self, symbol: str, data: list[dict]) -> int:
        if not data:
            return 0
        path = self._path(symbol)
        if self._use_pyarrow:
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.Table.from_pylist(data)
            pq.write_table(table, path)
        else:
            # Columnar JSON fallback
            columns = {}
            for key in data[0]:
                columns[key] = [row.get(key) for row in data]
            with open(path, "w") as f:
                json.dump({"columns": columns, "num_rows": len(data)}, f, default=str)
        return len(data)

    def read(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        path = self._path(symbol)
        if not os.path.exists(path):
            return []
        if self._use_pyarrow:
            import pyarrow.parquet as pq
            table = pq.read_table(path)
            data = table.to_pylist()
        else:
            with open(path, "r") as f:
                stored = json.load(f)
            columns = stored["columns"]
            num_rows = stored["num_rows"]
            keys = list(columns.keys())
            data = [{k: columns[k][i] for k in keys} for i in range(num_rows)]

        if start or end:
            data = [r for r in data
                    if (not start or str(r.get("date", "")) >= start)
                    and (not end or str(r.get("date", "")) <= end)]
        return data
