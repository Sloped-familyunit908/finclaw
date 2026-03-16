"""CSV file data source."""

import csv
import os
from datetime import datetime
from .base import DataSource


class CSVSource(DataSource):
    """Read price data from CSV files.

    Expected directory layout: {base_dir}/{SYMBOL}.csv
    Each CSV should have columns: date, open, high, low, close, volume
    """

    def __init__(self, base_dir: str, date_format: str = "%Y-%m-%d"):
        self.base_dir = base_dir
        self.date_format = date_format

    def fetch(self, symbols: list[str], start: str, end: str) -> dict[str, list[dict]]:
        result = {}
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")

        for symbol in symbols:
            path = os.path.join(self.base_dir, f"{symbol}.csv")
            if not os.path.exists(path):
                result[symbol] = []
                continue

            rows = []
            with open(path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        dt = datetime.strptime(row["date"], self.date_format)
                    except (KeyError, ValueError):
                        continue
                    if start_dt <= dt <= end_dt:
                        parsed = {"date": row["date"]}
                        for col in ("open", "high", "low", "close", "volume"):
                            if col in row:
                                try:
                                    parsed[col] = float(row[col])
                                except (ValueError, TypeError):
                                    pass
                        rows.append(parsed)
            result[symbol] = sorted(rows, key=lambda r: r["date"])
        return result

    def validate(self) -> bool:
        return os.path.isdir(self.base_dir)
