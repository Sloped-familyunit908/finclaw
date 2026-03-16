"""CSV data sink."""

import csv
import os
from ..sources.base import DataSink


class CSVSink(DataSink):
    """Write/read price data to CSV files. One file per symbol."""

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, symbol: str) -> str:
        return os.path.join(self.base_dir, f"{symbol}.csv")

    def write(self, symbol: str, data: list[dict]) -> int:
        if not data:
            return 0
        path = self._path(symbol)
        fields = list(data[0].keys())
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
        return len(data)

    def read(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        path = self._path(symbol)
        if not os.path.exists(path):
            return []
        rows = []
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if start and row.get("date", "") < start:
                    continue
                if end and row.get("date", "") > end:
                    continue
                # Convert numeric fields
                for k, v in row.items():
                    if k != "date":
                        try:
                            row[k] = float(v)
                        except (ValueError, TypeError):
                            pass
                rows.append(row)
        return rows
