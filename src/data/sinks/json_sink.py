"""JSON data sink."""

import json
import os
from ..sources.base import DataSink


class JSONSink(DataSink):
    """Write/read price data to JSON files. One file per symbol."""

    def __init__(self, base_dir: str, indent: int = 2):
        self.base_dir = base_dir
        self.indent = indent
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, symbol: str) -> str:
        return os.path.join(self.base_dir, f"{symbol}.json")

    def write(self, symbol: str, data: list[dict]) -> int:
        if not data:
            return 0
        path = self._path(symbol)
        with open(path, "w") as f:
            json.dump(data, f, indent=self.indent, default=str)
        return len(data)

    def read(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        path = self._path(symbol)
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            data = json.load(f)
        if start or end:
            data = [r for r in data
                    if (not start or r.get("date", "") >= start)
                    and (not end or r.get("date", "") <= end)]
        return data
