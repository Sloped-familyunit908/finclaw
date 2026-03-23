"""Tests for the unified data loader (data_loader.py).

15+ tests covering:
- CSV loading with valid data
- CSV loading with missing columns (skip gracefully)
- CSV loading with NaN values (clean or skip)
- Data validation: negative prices, zero volume, duplicate dates, out-of-order dates
- Cleaned data has no NaN
- yfinance/akshare loaders return correct format (mocked)
- Empty directory returns empty dict
- Quality report generation
- Edge cases
"""

import math
import os
import random
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.evolution.data_loader import (
    DataQualityReport,
    StockWarning,
    UnifiedDataLoader,
    _clean_stock_data,
    _has_nan,
    _is_nan,
    validate_data,
)


# ────────────────── Helpers ──────────────────


def _make_csv(
    directory: Path,
    filename: str = "test_001.csv",
    days: int = 100,
    start_price: float = 10.0,
    include_header: bool = True,
    header: str = "date,code,open,high,low,close,volume,amount,turn",
    seed: int = 42,
    inject_nan: bool = False,
    inject_negative: bool = False,
    inject_duplicate_dates: bool = False,
    inject_unsorted: bool = False,
    missing_columns: bool = False,
) -> Path:
    """Generate a synthetic CSV file for testing."""
    rng = random.Random(seed)
    fp = directory / filename

    if missing_columns:
        # Write CSV with missing required columns
        lines = ["date,code,open"]
        for d in range(5):
            lines.append(f"2024-01-{d+1:02d},TEST,{10 + d}")
        fp.write_text("\n".join(lines), encoding="utf-8")
        return fp

    lines = []
    if include_header:
        lines.append(header)

    price = start_price
    rows = []
    for d in range(days):
        date_str = f"2024-{(d // 28) + 1:02d}-{(d % 28) + 1:02d}"
        ret = 0.001 + 0.02 * rng.gauss(0, 1)
        o = price
        c = price * (1 + ret)
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.005)))
        lo = min(o, c) * (1 - abs(rng.gauss(0, 0.005)))
        vol = int(rng.uniform(1_000_000, 10_000_000))
        amount = int(c * vol)
        turn = round(rng.uniform(0.5, 3.0), 2)
        rows.append((date_str, "TEST", o, h, lo, c, vol, amount, turn))
        price = c

    if inject_nan and len(rows) > 10:
        # Inject NaN in the close price at rows 5 and 6
        r = list(rows[5])
        r[5] = float("nan")
        rows[5] = tuple(r)
        r = list(rows[6])
        r[5] = float("nan")
        rows[6] = tuple(r)

    if inject_negative and len(rows) > 15:
        # Inject negative price at row 15
        r = list(rows[15])
        r[5] = -5.0
        rows[15] = tuple(r)

    if inject_duplicate_dates and len(rows) > 20:
        # Make row 20 have same date as row 19
        r = list(rows[20])
        r[0] = rows[19][0]
        rows[20] = tuple(r)

    if inject_unsorted and len(rows) > 10:
        # Swap rows 5 and 8
        rows[5], rows[8] = rows[8], rows[5]

    for row in rows:
        date_str, code, o, h, lo, c, vol, amount, turn = row
        lines.append(
            f"{date_str},{code},{o:.4f},{h:.4f},{lo:.4f},{c:.4f},{vol},{amount},{turn}"
        )

    fp.write_text("\n".join(lines), encoding="utf-8")
    return fp


def _make_valid_stock_data(n: int = 100) -> dict:
    """Create a valid stock data dict for testing."""
    rng = random.Random(42)
    price = 10.0
    data: dict = {"date": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    for d in range(n):
        date_str = f"2024-{(d // 28) + 1:02d}-{(d % 28) + 1:02d}"
        ret = 0.001 + 0.01 * rng.gauss(0, 1)
        o = price
        c = price * (1 + ret)
        h = max(o, c) * 1.005
        lo = min(o, c) * 0.995
        vol = rng.randint(1_000_000, 10_000_000)
        data["date"].append(date_str)
        data["open"].append(o)
        data["high"].append(h)
        data["low"].append(lo)
        data["close"].append(c)
        data["volume"].append(vol)
        price = c
    return data


# ────────────────── Tests: CSV Loading ──────────────────


class TestCSVLoading:
    """Tests for UnifiedDataLoader.load_csv_dir()."""

    def test_load_valid_csv(self, tmp_path):
        """Valid CSV files load correctly."""
        _make_csv(tmp_path, "stock_a.csv", days=100)
        _make_csv(tmp_path, "stock_b.csv", days=100, seed=99)

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path))

        assert len(data) == 2
        assert "stock_a" in data
        assert "stock_b" in data

        for symbol, sd in data.items():
            assert "date" in sd
            assert "open" in sd
            assert "high" in sd
            assert "low" in sd
            assert "close" in sd
            assert "volume" in sd
            assert len(sd["date"]) == len(sd["close"])
            assert len(sd["date"]) >= 60

    def test_load_csv_missing_columns_skipped(self, tmp_path):
        """CSV files with missing required columns are skipped."""
        _make_csv(tmp_path, "good.csv", days=100)
        _make_csv(tmp_path, "bad.csv", days=100, missing_columns=True)

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path))

        assert "good" in data
        assert "bad" not in data

    def test_load_csv_with_nan_cleaned(self, tmp_path):
        """CSV with NaN values gets cleaned — NaN rows removed."""
        _make_csv(tmp_path, "nanstock.csv", days=100, inject_nan=True)

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path), clean=True)

        assert "nanstock" in data
        sd = data["nanstock"]
        # Verify no NaN in close prices
        for c in sd["close"]:
            assert not math.isnan(c), "Cleaned data should have no NaN"
        # Should have fewer rows than original 100
        assert len(sd["close"]) < 100
        assert len(sd["close"]) >= 60  # still above min_days

    def test_load_csv_without_cleaning(self, tmp_path):
        """CSV loading without cleaning preserves raw data (including NaN)."""
        _make_csv(tmp_path, "raw.csv", days=100, inject_nan=True)

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path), clean=False)

        assert "raw" in data
        sd = data["raw"]
        assert len(sd["close"]) == 100  # all rows kept
        # NaN should still be present
        nan_count = sum(1 for c in sd["close"] if math.isnan(c))
        assert nan_count >= 1

    def test_load_csv_min_days_filter(self, tmp_path):
        """Stocks below min_days threshold are excluded."""
        _make_csv(tmp_path, "short.csv", days=30)  # too short
        _make_csv(tmp_path, "long.csv", days=100)   # long enough

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path), min_days=60)

        assert "long" in data
        assert "short" not in data

    def test_load_empty_directory(self, tmp_path):
        """Empty directory returns empty dict."""
        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path))
        assert data == {}

    def test_load_nonexistent_directory(self):
        """Nonexistent directory returns empty dict."""
        loader = UnifiedDataLoader()
        data = loader.load_csv_dir("/nonexistent/path/xyz")
        assert data == {}

    def test_load_csv_case_insensitive_header(self, tmp_path):
        """Headers with different casing still work."""
        fp = tmp_path / "caps.csv"
        lines = ["Date,Code,Open,High,Low,Close,Volume"]
        rng = random.Random(42)
        price = 10.0
        for d in range(100):
            ret = 0.001 + 0.01 * rng.gauss(0, 1)
            c = price * (1 + ret)
            h = max(price, c) * 1.005
            lo = min(price, c) * 0.995
            vol = rng.randint(1_000_000, 5_000_000)
            lines.append(
                f"2024-{(d//28)+1:02d}-{(d%28)+1:02d},TEST,{price:.4f},{h:.4f},{lo:.4f},{c:.4f},{vol}"
            )
            price = c
        fp.write_text("\n".join(lines), encoding="utf-8")

        loader = UnifiedDataLoader()
        data = loader.load_csv_dir(str(tmp_path))
        assert "caps" in data


# ────────────────── Tests: Data Cleaning ──────────────────


class TestDataCleaning:
    """Tests for _clean_stock_data function."""

    def test_clean_removes_nan(self):
        """Cleaning removes rows with NaN values."""
        sd = _make_valid_stock_data(50)
        sd["close"][10] = float("nan")
        sd["close"][11] = float("nan")

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is not None
        assert len(cleaned["close"]) == 48  # 50 - 2
        assert not any(math.isnan(c) for c in cleaned["close"])
        assert any("NaN" in w.message for w in warnings)

    def test_clean_removes_negative_prices(self):
        """Cleaning removes rows with negative prices."""
        sd = _make_valid_stock_data(50)
        sd["close"][20] = -5.0
        sd["open"][21] = -3.0

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is not None
        assert not any(float(c) < 0 for c in cleaned["close"])
        assert not any(float(o) < 0 for o in cleaned["open"])
        assert any("negative" in w.message.lower() for w in warnings)

    def test_clean_removes_duplicate_dates(self):
        """Cleaning removes duplicate date entries."""
        sd = _make_valid_stock_data(50)
        sd["date"][25] = sd["date"][24]  # duplicate

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is not None
        assert len(set(cleaned["date"])) == len(cleaned["date"])
        assert any("duplicate" in w.message.lower() for w in warnings)

    def test_clean_sorts_out_of_order(self):
        """Cleaning sorts dates that are out of order."""
        sd = _make_valid_stock_data(50)
        # Swap two dates
        sd["date"][5], sd["date"][8] = sd["date"][8], sd["date"][5]
        sd["close"][5], sd["close"][8] = sd["close"][8], sd["close"][5]

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is not None
        # Verify sorted
        for i in range(1, len(cleaned["date"])):
            assert cleaned["date"][i] >= cleaned["date"][i - 1]
        assert any("order" in w.message.lower() for w in warnings)

    def test_clean_missing_column_returns_none(self):
        """Missing required column causes clean to return None."""
        sd = {"date": ["2024-01-01"], "open": [10.0], "close": [10.5]}
        # Missing high, low, volume

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is None
        assert any("Missing" in w.message for w in warnings)

    def test_clean_empty_data_returns_none(self):
        """Empty data returns None."""
        sd = {"date": [], "open": [], "high": [], "low": [], "close": [], "volume": []}

        cleaned, warnings = _clean_stock_data(sd, "TEST")
        assert cleaned is None

    def test_cleaned_data_has_no_nan(self):
        """After cleaning, no field should contain NaN."""
        sd = _make_valid_stock_data(100)
        # Inject NaN in various places
        sd["open"][10] = float("nan")
        sd["high"][20] = float("nan")
        sd["low"][30] = float("nan")
        sd["close"][40] = float("nan")
        sd["volume"][50] = float("nan")

        cleaned, _ = _clean_stock_data(sd, "TEST")
        assert cleaned is not None
        for key in ["open", "high", "low", "close", "volume"]:
            for val in cleaned[key]:
                assert not _is_nan(val), f"NaN found in cleaned {key}"


# ────────────────── Tests: Validation ──────────────────


class TestValidation:
    """Tests for validate_data function."""

    def test_validate_clean_data(self):
        """Clean data produces a good report."""
        data = {
            "STOCK_A": _make_valid_stock_data(100),
            "STOCK_B": _make_valid_stock_data(80),
        }

        report = validate_data(data)
        assert report.total_stocks == 2
        assert report.valid_stocks == 2
        assert report.stocks_with_bad_data == 0
        assert report.avg_trading_days > 0
        assert report.date_range[0] != ""

    def test_validate_catches_negative_prices(self):
        """Validation flags stocks with negative prices."""
        sd = _make_valid_stock_data(100)
        sd["close"][50] = -1.0
        data = {"BAD": sd}

        report = validate_data(data)
        assert report.stocks_with_bad_data >= 1
        assert any("Negative" in w.message or "negative" in w.message for w in report.warnings)

    def test_validate_catches_nan(self):
        """Validation flags stocks with NaN values."""
        sd = _make_valid_stock_data(100)
        sd["close"][50] = float("nan")
        data = {"NAN_STOCK": sd}

        report = validate_data(data)
        assert report.stocks_with_bad_data >= 1
        assert any("NaN" in w.message for w in report.warnings)

    def test_validate_catches_duplicate_dates(self):
        """Validation flags duplicate dates."""
        sd = _make_valid_stock_data(100)
        sd["date"][50] = sd["date"][49]
        data = {"DUP": sd}

        report = validate_data(data)
        assert report.stocks_with_bad_data >= 1
        assert any("duplicate" in w.message.lower() for w in report.warnings)

    def test_validate_catches_out_of_order_dates(self):
        """Validation flags out-of-order dates."""
        sd = _make_valid_stock_data(100)
        sd["date"][50], sd["date"][51] = sd["date"][51], sd["date"][50]
        data = {"UNSORTED": sd}

        report = validate_data(data)
        assert report.stocks_with_bad_data >= 1
        assert any("order" in w.message.lower() for w in report.warnings)

    def test_validate_empty_data(self):
        """Validation handles empty dataset."""
        report = validate_data({})
        assert report.total_stocks == 0
        assert report.valid_stocks == 0

    def test_validate_missing_columns(self):
        """Validation flags stocks with missing columns."""
        data = {"BAD": {"date": ["2024-01-01"], "close": [10.0]}}

        report = validate_data(data)
        assert report.stocks_with_bad_data >= 1

    def test_quality_report_summary(self):
        """Quality report produces a non-empty summary string."""
        data = {
            "GOOD": _make_valid_stock_data(100),
        }
        report = validate_data(data)
        summary = report.summary()
        assert "Data Quality Report" in summary
        assert "Total stocks" in summary


# ────────────────── Tests: yfinance (mocked) ──────────────────


class TestYfinanceLoader:
    """Tests for UnifiedDataLoader.load_from_yfinance (mocked)."""

    def test_yfinance_not_installed_raises(self):
        """Raises ImportError when yfinance not installed."""
        loader = UnifiedDataLoader()
        with patch("src.evolution.data_loader._HAS_YFINANCE", False):
            with pytest.raises(ImportError, match="yfinance"):
                loader.load_from_yfinance(["AAPL"], "2024-01-01", "2024-12-31")

    @patch("src.evolution.data_loader._HAS_YFINANCE", True)
    def test_yfinance_returns_correct_format(self):
        """Mocked yfinance returns data in unified format."""
        loader = UnifiedDataLoader()

        # Create a mock DataFrame
        mock_df = MagicMock()
        mock_df.empty = False

        # Create mock rows
        mock_rows = []
        rng = random.Random(42)
        price = 150.0
        for d in range(100):
            mock_idx = MagicMock()
            mock_idx.date.return_value = f"2024-{(d//28)+1:02d}-{(d%28)+1:02d}"
            mock_idx.__str__ = lambda self, d=d: f"2024-{(d//28)+1:02d}-{(d%28)+1:02d}"
            ret = 0.001 + 0.01 * rng.gauss(0, 1)
            c = price * (1 + ret)
            h = max(price, c) * 1.005
            lo = min(price, c) * 0.995
            vol = rng.randint(1_000_000, 50_000_000)
            row = {"Open": price, "High": h, "Low": lo, "Close": c, "Volume": vol}
            mock_rows.append((mock_idx, row))
            price = c

        mock_df.iterrows.return_value = mock_rows

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df

        with patch("src.evolution.data_loader.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            data = loader.load_from_yfinance(["AAPL"], "2024-01-01", "2024-12-31")

        assert "AAPL" in data
        sd = data["AAPL"]
        assert "date" in sd
        assert "open" in sd
        assert "high" in sd
        assert "low" in sd
        assert "close" in sd
        assert "volume" in sd
        assert len(sd["date"]) > 0


# ────────────────── Tests: akshare (mocked) ──────────────────


class TestAkshareLoader:
    """Tests for UnifiedDataLoader.load_from_akshare (mocked)."""

    def test_akshare_not_installed_raises(self):
        """Raises ImportError when akshare not installed."""
        loader = UnifiedDataLoader()
        with patch("src.evolution.data_loader._HAS_AKSHARE", False):
            with pytest.raises(ImportError, match="akshare"):
                loader.load_from_akshare(["000001"], "20240101", "20241231")

    @patch("src.evolution.data_loader._HAS_AKSHARE", True)
    def test_akshare_returns_correct_format(self):
        """Mocked akshare returns data in unified format."""
        loader = UnifiedDataLoader()

        mock_df = MagicMock()
        mock_df.empty = False

        mock_rows = []
        rng = random.Random(42)
        price = 15.0
        for d in range(100):
            ret = 0.001 + 0.01 * rng.gauss(0, 1)
            c = price * (1 + ret)
            h = max(price, c) * 1.005
            lo = min(price, c) * 0.995
            vol = rng.randint(100_000, 5_000_000)
            row = MagicMock()
            row.get = lambda k, default=0, d=d, o=price, hi=h, low=lo, cl=c, v=vol: {
                "日期": f"2024-{(d//28)+1:02d}-{(d%28)+1:02d}",
                "开盘": o,
                "最高": hi,
                "最低": low,
                "收盘": cl,
                "成交量": v,
            }.get(k, default)
            mock_rows.append((d, row))
            price = c

        mock_df.iterrows.return_value = mock_rows

        with patch("src.evolution.data_loader.ak") as mock_ak:
            mock_ak.stock_zh_a_hist.return_value = mock_df
            data = loader.load_from_akshare(
                ["000001"], "20240101", "20241231"
            )

        assert "000001" in data
        sd = data["000001"]
        assert "date" in sd
        assert "close" in sd
        assert len(sd["date"]) > 0


# ────────────────── Tests: Helper Functions ──────────────────


class TestHelpers:
    """Tests for helper utility functions."""

    def test_is_nan_true(self):
        assert _is_nan(float("nan")) is True

    def test_is_nan_false(self):
        assert _is_nan(10.0) is False
        assert _is_nan(0) is False

    def test_is_nan_string(self):
        assert _is_nan("not a number") is False  # can't convert to float, not NaN
        assert _is_nan("10.5") is False
        assert _is_nan("nan") is True  # "nan" converts to float NaN

    def test_has_nan_with_nan(self):
        assert _has_nan([1.0, 2.0, float("nan"), 4.0]) is True

    def test_has_nan_without_nan(self):
        assert _has_nan([1.0, 2.0, 3.0, 4.0]) is False

    def test_has_nan_empty(self):
        assert _has_nan([]) is False
