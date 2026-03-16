"""Data sinks for the pipeline."""

from .csv_sink import CSVSink
from .json_sink import JSONSink
from .sqlite_sink import SQLiteSink
from .parquet_sink import ParquetSink

__all__ = ["CSVSink", "JSONSink", "SQLiteSink", "ParquetSink"]
