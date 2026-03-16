"""
FinClaw Data Exporter
Export DataFrames / dicts to CSV, JSON, Parquet, and Excel.
Optional dependencies degrade gracefully.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from typing import Any, Sequence

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pyarrow  # noqa: F401
    import pyarrow.parquet as pq
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False

try:
    import openpyxl  # noqa: F401
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj: Any) -> Any:
        if HAS_NUMPY:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        return super().default(obj)


class DataExporter:
    """
    Export tabular data (list-of-dicts or DataFrame) to multiple formats.

    Usage:
        exporter = DataExporter()
        exporter.to_csv(data, "output.csv")
        exporter.to_json(data, "output.json")
        exporter.to_parquet(data, "output.parquet")
        exporter.to_excel(data, "output.xlsx")
    """

    @staticmethod
    def _ensure_dir(path: str) -> None:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    @staticmethod
    def _to_records(data: Any) -> list[dict]:
        """Normalize data to list of dicts."""
        if isinstance(data, list):
            return data
        # DataFrame-like
        if hasattr(data, "to_dict"):
            return data.to_dict("records")
        if isinstance(data, dict):
            return [data]
        raise TypeError(f"Unsupported data type: {type(data)}")

    def to_csv(self, data: Any, path: str) -> str:
        """Export to CSV. Returns the written path."""
        records = self._to_records(data)
        if not records:
            raise ValueError("No data to export")
        self._ensure_dir(path)
        fieldnames = list(records[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        logger.info("Exported %d rows to CSV: %s", len(records), path)
        return path

    def to_json(self, data: Any, path: str, indent: int = 2) -> str:
        """Export to JSON. Returns the written path."""
        records = self._to_records(data)
        self._ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, cls=_NumpyEncoder, indent=indent, ensure_ascii=False)
        logger.info("Exported %d records to JSON: %s", len(records), path)
        return path

    def to_parquet(self, data: Any, path: str) -> str:
        """Export to Parquet (requires pyarrow)."""
        if not HAS_PARQUET:
            raise ImportError("pyarrow is required for Parquet export: pip install pyarrow")
        import pyarrow as pa
        import pyarrow.parquet as pq
        records = self._to_records(data)
        if not records:
            raise ValueError("No data to export")
        self._ensure_dir(path)
        table = pa.Table.from_pylist(records)
        pq.write_table(table, path)
        logger.info("Exported %d rows to Parquet: %s", len(records), path)
        return path

    def to_excel(self, data: Any, path: str, sheet_name: str = "Sheet1") -> str:
        """Export to Excel (requires openpyxl)."""
        if not HAS_EXCEL:
            raise ImportError("openpyxl is required for Excel export: pip install openpyxl")
        from openpyxl import Workbook
        records = self._to_records(data)
        if not records:
            raise ValueError("No data to export")
        self._ensure_dir(path)
        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        headers = list(records[0].keys())
        ws.append(headers)
        for row in records:
            ws.append([row.get(h) for h in headers])
        wb.save(path)
        logger.info("Exported %d rows to Excel: %s", len(records), path)
        return path

    def to_string(self, data: Any, fmt: str = "csv") -> str:
        """Export to string (useful for API responses)."""
        records = self._to_records(data)
        if fmt == "json":
            return json.dumps(records, cls=_NumpyEncoder, indent=2, ensure_ascii=False)
        # CSV string
        if not records:
            return ""
        buf = io.StringIO()
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        return buf.getvalue()
