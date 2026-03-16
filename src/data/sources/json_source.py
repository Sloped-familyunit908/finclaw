"""JSON file data source."""

import json
import os
from datetime import datetime
from .base import DataSource


class JSONSource(DataSource):
    """Read price data from JSON files.

    Expected layout: {base_dir}/{SYMBOL}.json
    Each JSON is a list of objects with date, open, high, low, close, volume.
    """

    def __init__(self, base_dir: str, date_format: str = "%Y-%m-%d"):
        self.base_dir = base_dir
        self.date_format = date_format

    def fetch(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict]]:
        result = {}
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")

        for symbol in symbols:
            path = os.path.join(self.base_dir, f"{symbol}.json")
            if not os.path.exists(path):
                result[symbol] = []
                continue

            with open(path, "r") as f:
                data = json.load(f)

            rows = []
            for row in data:
                try:
                    dt = datetime.strptime(row["date"], self.date_format)
                except (KeyError, ValueError):
                    continue
                if start_dt <= dt <= end_dt:
                    rows.append(row)
            result[symbol] = sorted(rows, key=lambda r: r["date"])
        return result

    def validate(self) -> bool:
        return os.path.isdir(self.base_dir)
