"""Tests for Data Pipeline & Storage — 45 tests covering pipeline, sources, sinks, and quality."""

import csv
import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.pipeline import DataPipeline
from src.data.sources.base import DataSource, DataSink
from src.data.sources.csv_source import CSVSource
from src.data.sources.json_source import JSONSource
from src.data.sources.exchange_source import ExchangeSource
from src.data.sources.api_source import APISource
from src.data.sinks.csv_sink import CSVSink
from src.data.sinks.json_sink import JSONSink
from src.data.sinks.sqlite_sink import SQLiteSink
from src.data.sinks.parquet_sink import ParquetSink
from src.data.quality import DataQualityChecker


# ── Helpers ──────────────────────────────────────────────────────────────

def _sample_rows(n=10, start_date="2024-01-01"):
    """Generate sample OHLCV rows."""
    rows = []
    base = datetime.strptime(start_date, "%Y-%m-%d")
    price = 100.0
    for i in range(n):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        price *= 1.005
        rows.append({
            "date": d, "open": round(price * 0.99, 2), "high": round(price * 1.01, 2),
            "low": round(price * 0.98, 2), "close": round(price, 2), "volume": 1000 + i,
        })
    return rows


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _write_json(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f)


class MockExchangeAdapter:
    """Mock exchange adapter for testing."""
    def __init__(self, data=None):
        self._data = data or {}

    def fetch_ohlcv(self, symbol, start, end):
        return self._data.get(symbol, [])


class InMemorySource(DataSource):
    """In-memory source for pipeline testing."""
    def __init__(self, data: dict):
        self._data = data

    def fetch(self, symbols, start, end):
        return {s: self._data.get(s, []) for s in symbols}


class InMemorySink(DataSink):
    """In-memory sink for pipeline testing."""
    def __init__(self):
        self.stored = {}

    def write(self, symbol, data):
        self.stored[symbol] = data
        return len(data)

    def read(self, symbol, start=None, end=None):
        return self.stored.get(symbol, [])


# ── CSV Source Tests ─────────────────────────────────────────────────────

class TestCSVSource:
    def test_fetch_basic(self, tmp_path):
        rows = _sample_rows(5)
        _write_csv(tmp_path / "AAPL.csv", rows)
        src = CSVSource(str(tmp_path))
        result = src.fetch(["AAPL"], "2024-01-01", "2024-01-10")
        assert len(result["AAPL"]) == 5

    def test_fetch_date_filter(self, tmp_path):
        rows = _sample_rows(10)
        _write_csv(tmp_path / "AAPL.csv", rows)
        src = CSVSource(str(tmp_path))
        result = src.fetch(["AAPL"], "2024-01-03", "2024-01-07")
        assert all("2024-01-03" <= r["date"] <= "2024-01-07" for r in result["AAPL"])

    def test_fetch_missing_file(self, tmp_path):
        src = CSVSource(str(tmp_path))
        result = src.fetch(["MISSING"], "2024-01-01", "2024-12-31")
        assert result["MISSING"] == []

    def test_validate(self, tmp_path):
        src = CSVSource(str(tmp_path))
        assert src.validate() is True
        src2 = CSVSource("/nonexistent/path/xyz")
        assert src2.validate() is False

    def test_multiple_symbols(self, tmp_path):
        for sym in ["AAPL", "GOOG"]:
            _write_csv(tmp_path / f"{sym}.csv", _sample_rows(3))
        src = CSVSource(str(tmp_path))
        result = src.fetch(["AAPL", "GOOG"], "2024-01-01", "2024-12-31")
        assert len(result["AAPL"]) == 3
        assert len(result["GOOG"]) == 3


# ── JSON Source Tests ────────────────────────────────────────────────────

class TestJSONSource:
    def test_fetch_basic(self, tmp_path):
        rows = _sample_rows(5)
        _write_json(tmp_path / "BTC.json", rows)
        src = JSONSource(str(tmp_path))
        result = src.fetch(["BTC"], "2024-01-01", "2024-01-10")
        assert len(result["BTC"]) == 5

    def test_fetch_date_filter(self, tmp_path):
        rows = _sample_rows(10)
        _write_json(tmp_path / "ETH.json", rows)
        src = JSONSource(str(tmp_path))
        result = src.fetch(["ETH"], "2024-01-03", "2024-01-05")
        assert len(result["ETH"]) == 3

    def test_missing_file(self, tmp_path):
        src = JSONSource(str(tmp_path))
        result = src.fetch(["NOPE"], "2024-01-01", "2024-12-31")
        assert result["NOPE"] == []


# ── Exchange Source Tests ────────────────────────────────────────────────

class TestExchangeSource:
    def test_fetch(self):
        adapter = MockExchangeAdapter({"BTC": _sample_rows(5)})
        src = ExchangeSource(adapter, "test_exchange")
        result = src.fetch(["BTC"], "2024-01-01", "2024-12-31")
        assert len(result["BTC"]) == 5

    def test_validate(self):
        adapter = MockExchangeAdapter()
        src = ExchangeSource(adapter)
        assert src.validate() is True

    def test_missing_symbol(self):
        adapter = MockExchangeAdapter({})
        src = ExchangeSource(adapter)
        result = src.fetch(["XYZ"], "2024-01-01", "2024-12-31")
        assert result["XYZ"] == []


# ── API Source Tests ─────────────────────────────────────────────────────

class TestAPISource:
    def test_validate(self):
        src = APISource("https://example.com/{symbol}")
        assert src.validate() is True
        src2 = APISource("")
        assert src2.validate() is False

    def test_fetch_error_handled(self):
        src = APISource("https://invalid.localhost/{symbol}", timeout=1)
        result = src.fetch(["BTC"], "2024-01-01", "2024-12-31")
        assert result["BTC"] == []


# ── CSV Sink Tests ───────────────────────────────────────────────────────

class TestCSVSink:
    def test_write_and_read(self, tmp_path):
        sink = CSVSink(str(tmp_path / "out"))
        rows = _sample_rows(5)
        assert sink.write("AAPL", rows) == 5
        back = sink.read("AAPL")
        assert len(back) == 5
        assert float(back[0]["close"]) == rows[0]["close"]

    def test_empty_write(self, tmp_path):
        sink = CSVSink(str(tmp_path / "out"))
        assert sink.write("EMPTY", []) == 0

    def test_read_missing(self, tmp_path):
        sink = CSVSink(str(tmp_path / "out"))
        assert sink.read("NOPE") == []

    def test_date_filter(self, tmp_path):
        sink = CSVSink(str(tmp_path / "out"))
        sink.write("X", _sample_rows(10))
        result = sink.read("X", start="2024-01-03", end="2024-01-05")
        assert all("2024-01-03" <= r["date"] <= "2024-01-05" for r in result)


# ── JSON Sink Tests ──────────────────────────────────────────────────────

class TestJSONSink:
    def test_write_and_read(self, tmp_path):
        sink = JSONSink(str(tmp_path / "out"))
        rows = _sample_rows(5)
        assert sink.write("BTC", rows) == 5
        back = sink.read("BTC")
        assert len(back) == 5

    def test_empty_write(self, tmp_path):
        sink = JSONSink(str(tmp_path / "out"))
        assert sink.write("E", []) == 0

    def test_date_filter(self, tmp_path):
        sink = JSONSink(str(tmp_path / "out"))
        sink.write("X", _sample_rows(10))
        result = sink.read("X", start="2024-01-05")
        assert all(r["date"] >= "2024-01-05" for r in result)


# ── SQLite Sink Tests ────────────────────────────────────────────────────

class TestSQLiteSink:
    def test_write_and_read(self, tmp_path):
        sink = SQLiteSink(str(tmp_path / "test.db"))
        rows = _sample_rows(5)
        assert sink.write("AAPL", rows) == 5
        back = sink.read("AAPL")
        assert len(back) == 5
        sink.close()

    def test_overwrite(self, tmp_path):
        sink = SQLiteSink(str(tmp_path / "test.db"))
        sink.write("X", _sample_rows(5))
        sink.write("X", _sample_rows(3))
        assert len(sink.read("X")) == 3
        sink.close()

    def test_date_filter(self, tmp_path):
        sink = SQLiteSink(str(tmp_path / "test.db"))
        sink.write("X", _sample_rows(10))
        result = sink.read("X", start="2024-01-03", end="2024-01-05")
        assert all("2024-01-03" <= r["date"] <= "2024-01-05" for r in result)
        sink.close()

    def test_read_missing_table(self, tmp_path):
        sink = SQLiteSink(str(tmp_path / "test.db"))
        assert sink.read("NOPE") == []
        sink.close()


# ── Parquet Sink Tests ───────────────────────────────────────────────────

class TestParquetSink:
    def test_write_and_read(self, tmp_path):
        sink = ParquetSink(str(tmp_path / "out"))
        rows = _sample_rows(5)
        assert sink.write("BTC", rows) == 5
        back = sink.read("BTC")
        assert len(back) == 5

    def test_empty_write(self, tmp_path):
        sink = ParquetSink(str(tmp_path / "out"))
        assert sink.write("E", []) == 0

    def test_date_filter(self, tmp_path):
        sink = ParquetSink(str(tmp_path / "out"))
        sink.write("X", _sample_rows(10))
        result = sink.read("X", start="2024-01-05")
        assert all(str(r["date"]) >= "2024-01-05" for r in result)


# ── Pipeline Tests ───────────────────────────────────────────────────────

class TestDataPipeline:
    def test_basic_pipeline(self):
        data = {"BTC": _sample_rows(5)}
        pipe = DataPipeline()
        pipe.add_source("mem", InMemorySource(data))
        pipe.add_sink("mem", InMemorySink())
        result = pipe.run(["BTC"], "2024-01-01", "2024-12-31")
        assert result["sources"]["mem"]["status"] == "ok"
        assert result["sinks"]["mem"]["rows"] == 5

    def test_pipeline_with_transform(self):
        data = {"BTC": _sample_rows(10)}
        pipe = DataPipeline()
        pipe.add_source("s", InMemorySource(data))
        pipe.add_sink("k", InMemorySink())
        # Transform: only keep rows with volume > 1003
        pipe.add_transform(lambda rows: [r for r in rows if r.get("volume", 0) > 1003])
        result = pipe.run(["BTC"], "2024-01-01", "2024-12-31")
        assert result["sinks"]["k"]["rows"] < 10

    def test_no_sources_error(self):
        pipe = DataPipeline()
        pipe.add_sink("s", InMemorySink())
        with pytest.raises(ValueError, match="No sources"):
            pipe.run(["X"], "2024-01-01", "2024-12-31")

    def test_no_sinks_error(self):
        pipe = DataPipeline()
        pipe.add_source("s", InMemorySource({}))
        with pytest.raises(ValueError, match="No sinks"):
            pipe.run(["X"], "2024-01-01", "2024-12-31")

    def test_add_source_type_check(self):
        pipe = DataPipeline()
        with pytest.raises(TypeError):
            pipe.add_source("bad", "not a source")

    def test_add_sink_type_check(self):
        pipe = DataPipeline()
        with pytest.raises(TypeError):
            pipe.add_sink("bad", "not a sink")

    def test_add_transform_type_check(self):
        pipe = DataPipeline()
        with pytest.raises(TypeError):
            pipe.add_transform("not callable")

    def test_chaining(self):
        pipe = DataPipeline()
        result = pipe.add_source("s", InMemorySource({}))
        assert result is pipe
        result2 = pipe.add_transform(lambda x: x)
        assert result2 is pipe

    def test_multiple_sources_merge(self):
        src1 = InMemorySource({"BTC": _sample_rows(3, "2024-01-01")})
        src2 = InMemorySource({"BTC": _sample_rows(3, "2024-01-10")})
        sink = InMemorySink()
        pipe = DataPipeline()
        pipe.add_source("a", src1).add_source("b", src2).add_sink("out", sink)
        pipe.run(["BTC"], "2024-01-01", "2024-12-31")
        assert len(sink.stored["BTC"]) == 6  # merged, no overlap

    def test_multiple_sinks(self):
        data = {"BTC": _sample_rows(5)}
        sink1, sink2 = InMemorySink(), InMemorySink()
        pipe = DataPipeline()
        pipe.add_source("s", InMemorySource(data))
        pipe.add_sink("a", sink1).add_sink("b", sink2)
        pipe.run(["BTC"], "2024-01-01", "2024-12-31")
        assert len(sink1.stored["BTC"]) == 5
        assert len(sink2.stored["BTC"]) == 5

    def test_last_run(self):
        pipe = DataPipeline()
        pipe.add_source("s", InMemorySource({"X": []}))
        pipe.add_sink("k", InMemorySink())
        assert pipe.last_run is None
        pipe.run(["X"], "2024-01-01", "2024-12-31")
        assert pipe.last_run is not None
        assert "started_at" in pipe.last_run

    def test_schedule_and_stop(self):
        pipe = DataPipeline()
        pipe.add_source("s", InMemorySource({"X": _sample_rows(2)}))
        pipe.add_sink("k", InMemorySink())
        pipe.schedule("1s", symbols=["X"])
        time.sleep(1.5)
        pipe.stop_schedule()
        assert pipe.last_run is not None

    def test_parse_interval(self):
        assert DataPipeline._parse_interval("30s") == 30.0
        assert DataPipeline._parse_interval("5m") == 300.0
        assert DataPipeline._parse_interval("2h") == 7200.0
        with pytest.raises(ValueError):
            DataPipeline._parse_interval("bad")

    def test_deduplication(self):
        """Same date rows from two sources should be deduplicated."""
        rows = _sample_rows(3)
        src1 = InMemorySource({"X": rows})
        src2 = InMemorySource({"X": rows})  # exact duplicates
        sink = InMemorySink()
        pipe = DataPipeline()
        pipe.add_source("a", src1).add_source("b", src2).add_sink("out", sink)
        pipe.run(["X"], "2024-01-01", "2024-12-31")
        assert len(sink.stored["X"]) == 3  # deduped


# ── Quality Checker Tests ────────────────────────────────────────────────

class TestDataQualityChecker:
    def _make_df(self, n=30):
        import pandas as pd
        dates = pd.bdate_range("2024-01-01", periods=n)
        closes = [100 + i * 0.5 for i in range(n)]
        return pd.DataFrame({"close": closes}, index=dates)

    def test_check_returns_report(self):
        checker = DataQualityChecker()
        df = self._make_df()
        report = checker.check(df)
        assert report.total_rows == 30
        assert report.score > 0

    def test_clean_basic(self):
        checker = DataQualityChecker()
        df = self._make_df()
        cleaned = checker.clean(df)
        assert len(cleaned) >= len(df)

    def test_empty_data(self):
        import pandas as pd
        checker = DataQualityChecker()
        report = checker.check(pd.DataFrame())
        assert report.score == 0
