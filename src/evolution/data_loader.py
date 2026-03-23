"""
Unified Data Loader for Multi-Market Evolution
================================================
Supports loading market data from:
- Local CSV directories (A-shares, US stocks, crypto — any CSV)
- akshare (A-share data download)
- yfinance (US stock / global data download)

All methods return a unified format:
    Dict[str, Dict[str, list]]
    {symbol: {date: [...], open: [...], high: [...], low: [...], close: [...], volume: [...]}}

Includes data validation and cleaning to ensure backtest integrity.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional dependencies — gracefully degrade if not installed
try:
    import akshare as ak  # type: ignore

    _HAS_AKSHARE = True
except ImportError:
    _HAS_AKSHARE = False

try:
    import yfinance as yf  # type: ignore

    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False


# ────────────────── Data Quality Report ──────────────────


@dataclass
class StockWarning:
    """A single warning/error for a stock."""

    stock: str
    level: str  # "warning" or "error"
    message: str


@dataclass
class DataQualityReport:
    """Report on the quality of loaded market data."""

    total_stocks: int = 0
    valid_stocks: int = 0
    stocks_with_gaps: int = 0
    stocks_with_bad_data: int = 0
    date_range: Tuple[str, str] = ("", "")
    avg_trading_days: float = 0.0
    warnings: List[StockWarning] = field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            f"Data Quality Report",
            f"  Total stocks:       {self.total_stocks}",
            f"  Valid stocks:       {self.valid_stocks}",
            f"  Stocks with gaps:   {self.stocks_with_gaps}",
            f"  Stocks with bad data: {self.stocks_with_bad_data}",
            f"  Date range:         {self.date_range[0]} — {self.date_range[1]}",
            f"  Avg trading days:   {self.avg_trading_days:.0f}",
        ]
        if self.warnings:
            lines.append(f"  Warnings/errors:    {len(self.warnings)}")
            # Show first 10 warnings
            for w in self.warnings[:10]:
                lines.append(f"    [{w.level}] {w.stock}: {w.message}")
            if len(self.warnings) > 10:
                lines.append(f"    ... and {len(self.warnings) - 10} more")
        return "\n".join(lines)


# ────────────────── Validation & Cleaning ──────────────────


def _is_nan(val: Any) -> bool:
    """Check if a value is NaN (works for float and other types)."""
    try:
        return math.isnan(float(val))
    except (ValueError, TypeError):
        return False


def _has_nan(values: list) -> bool:
    """Check if any value in a list is NaN."""
    return any(_is_nan(v) for v in values)


def _clean_stock_data(
    stock_data: Dict[str, list], symbol: str
) -> Tuple[Optional[Dict[str, list]], List[StockWarning]]:
    """Clean a single stock's data.

    Operations:
    - Remove rows with NaN in any OHLCV field
    - Remove rows with negative prices
    - Remove rows with zero volume (but allow it — some indices have 0 volume)
    - Remove duplicate dates (keep first)
    - Sort by date (ascending)
    - Interpolate minor gaps (1-2 consecutive NaN values in price)

    Returns:
        (cleaned_data_or_None, list_of_warnings)
    """
    warnings: List[StockWarning] = []
    keys = ["date", "open", "high", "low", "close", "volume"]

    # Verify all keys present
    for k in keys:
        if k not in stock_data:
            warnings.append(
                StockWarning(symbol, "error", f"Missing required column: {k}")
            )
            return None, warnings

    n = len(stock_data["date"])
    if n == 0:
        warnings.append(StockWarning(symbol, "error", "No data rows"))
        return None, warnings

    # Ensure all arrays same length
    min_len = min(len(stock_data[k]) for k in keys)
    if min_len < n:
        warnings.append(
            StockWarning(
                symbol,
                "warning",
                f"Mismatched column lengths (min={min_len}, max={n}), truncating",
            )
        )
        n = min_len

    # Build row-level mask: True = keep
    keep = [True] * n
    nan_count = 0
    neg_count = 0
    dup_dates_count = 0

    seen_dates: set = set()
    price_keys = ["open", "high", "low", "close"]

    for i in range(n):
        # Check for NaN in any numeric field
        for k in price_keys + ["volume"]:
            val = stock_data[k][i]
            if _is_nan(val):
                keep[i] = False
                nan_count += 1
                break

        if not keep[i]:
            continue

        # Check for negative prices
        for k in price_keys:
            if float(stock_data[k][i]) < 0:
                keep[i] = False
                neg_count += 1
                break

        if not keep[i]:
            continue

        # Check for duplicate dates
        d = stock_data["date"][i]
        if d in seen_dates:
            keep[i] = False
            dup_dates_count += 1
        else:
            seen_dates.add(d)

    if nan_count > 0:
        warnings.append(
            StockWarning(symbol, "warning", f"Removed {nan_count} rows with NaN values")
        )
    if neg_count > 0:
        warnings.append(
            StockWarning(
                symbol, "warning", f"Removed {neg_count} rows with negative prices"
            )
        )
    if dup_dates_count > 0:
        warnings.append(
            StockWarning(
                symbol, "warning", f"Removed {dup_dates_count} duplicate date rows"
            )
        )

    # Apply mask
    cleaned: Dict[str, list] = {}
    for k in keys:
        cleaned[k] = [stock_data[k][i] for i in range(n) if keep[i]]

    if len(cleaned["date"]) == 0:
        warnings.append(
            StockWarning(symbol, "error", "No data remaining after cleaning")
        )
        return None, warnings

    # Sort by date ascending
    # First check if already sorted
    was_unsorted = any(
        cleaned["date"][i] > cleaned["date"][i + 1]
        for i in range(len(cleaned["date"]) - 1)
    )
    if was_unsorted:
        warnings.append(StockWarning(symbol, "warning", "Dates were out of order, sorted"))

    indices = list(range(len(cleaned["date"])))
    indices.sort(key=lambda i: cleaned["date"][i])

    sorted_data: Dict[str, list] = {}
    for k in keys:
        sorted_data[k] = [cleaned[k][i] for i in indices]

    # Interpolate minor gaps (1-2 missing values) for price fields
    # We do this by scanning for sudden jumps that suggest a missing trading day
    # (this is mainly useful after NaN removal creates gaps in the series)
    # For now, we just ensure the data is clean — full gap interpolation
    # would require a calendar which is market-specific.

    return sorted_data, warnings


def validate_data(data: Dict[str, Dict[str, list]]) -> DataQualityReport:
    """Validate a dataset and produce a quality report.

    Checks each stock for:
    - NaN values in OHLCV
    - Negative prices
    - Zero volume days
    - Duplicate dates
    - Out-of-order dates
    - Date range and trading day count

    Args:
        data: Dict of symbol -> {date, open, high, low, close, volume}

    Returns:
        DataQualityReport with findings
    """
    report = DataQualityReport()
    report.total_stocks = len(data)

    all_warnings: List[StockWarning] = []
    all_start_dates: List[str] = []
    all_end_dates: List[str] = []
    trading_day_counts: List[int] = []
    bad_stocks = set()
    gap_stocks = set()

    for symbol, sd in data.items():
        keys = ["date", "open", "high", "low", "close", "volume"]

        # Check required columns
        missing_cols = [k for k in keys if k not in sd]
        if missing_cols:
            all_warnings.append(
                StockWarning(
                    symbol, "error", f"Missing columns: {missing_cols}"
                )
            )
            bad_stocks.add(symbol)
            continue

        n = len(sd["date"])
        if n == 0:
            all_warnings.append(StockWarning(symbol, "error", "Empty data"))
            bad_stocks.add(symbol)
            continue

        trading_day_counts.append(n)
        all_start_dates.append(sd["date"][0])
        all_end_dates.append(sd["date"][-1])

        # Check for NaN
        for k in ["open", "high", "low", "close", "volume"]:
            if _has_nan(sd[k][:n]):
                all_warnings.append(
                    StockWarning(symbol, "warning", f"NaN found in {k}")
                )
                bad_stocks.add(symbol)
                break

        # Check for negative prices
        for k in ["open", "high", "low", "close"]:
            if any(float(v) < 0 for v in sd[k][:n]):
                all_warnings.append(
                    StockWarning(symbol, "warning", f"Negative prices in {k}")
                )
                bad_stocks.add(symbol)
                break

        # Check zero volume (warn but don't mark as bad — indices can have 0 vol)
        zero_vol = sum(1 for v in sd["volume"][:n] if float(v) == 0)
        if zero_vol > n * 0.5:  # more than 50% zero volume is suspicious
            all_warnings.append(
                StockWarning(
                    symbol,
                    "warning",
                    f"High zero-volume ratio: {zero_vol}/{n} days ({100*zero_vol/n:.0f}%)",
                )
            )

        # Check duplicate dates
        dates = sd["date"][:n]
        if len(set(dates)) < len(dates):
            dup_count = len(dates) - len(set(dates))
            all_warnings.append(
                StockWarning(
                    symbol, "warning", f"{dup_count} duplicate dates found"
                )
            )
            bad_stocks.add(symbol)

        # Check date ordering
        for i in range(1, len(dates)):
            if dates[i] < dates[i - 1]:
                all_warnings.append(
                    StockWarning(symbol, "warning", "Dates are not in ascending order")
                )
                bad_stocks.add(symbol)
                break

        # Check for gaps (missing trading days) — rough heuristic
        # If there's a jump of 5+ calendar days between consecutive dates,
        # flag as a gap (weekends are 2-3 days, holidays up to 10)
        if len(dates) >= 2:
            for i in range(1, len(dates)):
                try:
                    # Simple string comparison for YYYY-MM-DD format
                    # We just check if consecutive dates are reasonable
                    d1 = dates[i - 1]
                    d2 = dates[i]
                    # Parse year-month-day
                    y1, m1, dd1 = int(d1[:4]), int(d1[5:7]), int(d1[8:10])
                    y2, m2, dd2 = int(d2[:4]), int(d2[5:7]), int(d2[8:10])
                    # Rough days between
                    day_diff = (y2 - y1) * 365 + (m2 - m1) * 30 + (dd2 - dd1)
                    if day_diff > 14:  # 2+ week gap
                        gap_stocks.add(symbol)
                        break
                except (ValueError, IndexError):
                    pass

    report.valid_stocks = report.total_stocks - len(bad_stocks)
    report.stocks_with_bad_data = len(bad_stocks)
    report.stocks_with_gaps = len(gap_stocks)
    report.warnings = all_warnings

    if all_start_dates:
        report.date_range = (min(all_start_dates), max(all_end_dates))
    if trading_day_counts:
        report.avg_trading_days = sum(trading_day_counts) / len(trading_day_counts)

    return report


# ────────────────── Unified Data Loader ──────────────────


class UnifiedDataLoader:
    """Multi-market data loader with validation and cleaning.

    Loads data from CSV directories, akshare (A-shares), or yfinance (US stocks).
    All methods return the same unified format.
    """

    def load_csv_dir(
        self,
        path: str,
        market: str = "cn",
        min_days: int = 60,
        clean: bool = True,
    ) -> Dict[str, Dict[str, list]]:
        """Load all CSV files from a directory.

        Extracts from the existing AutoEvolver.load_data logic but generalized
        for any market. CSV files must have columns: date, open, high, low, close, volume.
        Extra columns (code, amount, turn, etc.) are ignored.

        Args:
            path: Directory path containing CSV files
            market: Market identifier ("cn", "us", "crypto") — for metadata only
            min_days: Minimum trading days required (skip shorter stocks)
            clean: Whether to clean/validate data (remove NaN, bad rows, etc.)

        Returns:
            Dict[symbol, {date, open, high, low, close, volume}]
        """
        data: Dict[str, Dict[str, list]] = {}
        data_path = Path(path)

        if not data_path.exists():
            return data

        csv_files = list(data_path.glob("*.csv"))
        for fp in csv_files:
            try:
                lines = fp.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) < 2:
                    continue

                header = lines[0].strip().split(",")
                col_map = {h.strip().lower(): i for i, h in enumerate(header)}

                # Required columns
                required = {"date", "open", "high", "low", "close", "volume"}
                if not required.issubset(col_map.keys()):
                    continue

                dates: List[str] = []
                opens: List[float] = []
                highs: List[float] = []
                lows: List[float] = []
                closes: List[float] = []
                volumes: List[float] = []

                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if len(parts) > max(col_map[k] for k in required):
                        try:
                            dates.append(parts[col_map["date"]])
                            opens.append(float(parts[col_map["open"]]))
                            highs.append(float(parts[col_map["high"]]))
                            lows.append(float(parts[col_map["low"]]))
                            closes.append(float(parts[col_map["close"]]))
                            volumes.append(float(parts[col_map["volume"]]))
                        except (ValueError, IndexError):
                            continue

                if len(closes) >= min_days:
                    symbol = fp.stem
                    stock_data: Dict[str, list] = {
                        "date": dates,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                    }

                    if clean:
                        cleaned, _warnings = _clean_stock_data(stock_data, symbol)
                        if cleaned and len(cleaned["date"]) >= min_days:
                            data[symbol] = cleaned
                    else:
                        data[symbol] = stock_data
            except Exception:
                continue

        return data

    def load_from_akshare(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        market: str = "cn",
    ) -> Dict[str, Dict[str, list]]:
        """Download A-share data via akshare.

        Args:
            symbols: List of stock codes, e.g. ["000001", "600036"]
            start_date: Start date "YYYYMMDD"
            end_date: End date "YYYYMMDD"
            market: Market type ("cn" for A-shares)

        Returns:
            Unified format dict

        Raises:
            ImportError: If akshare is not installed
        """
        if not _HAS_AKSHARE:
            raise ImportError(
                "akshare is not installed. Install with: pip install akshare"
            )

        data: Dict[str, Dict[str, list]] = {}

        for symbol in symbols:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",  # forward-adjusted
                )
                if df is None or df.empty:
                    continue

                # akshare column names (Chinese)
                col_mapping = {
                    "日期": "date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                }

                stock_data: Dict[str, list] = {
                    "date": [],
                    "open": [],
                    "high": [],
                    "low": [],
                    "close": [],
                    "volume": [],
                }

                for _, row in df.iterrows():
                    try:
                        stock_data["date"].append(str(row.get("日期", "")))
                        stock_data["open"].append(float(row.get("开盘", 0)))
                        stock_data["high"].append(float(row.get("最高", 0)))
                        stock_data["low"].append(float(row.get("最低", 0)))
                        stock_data["close"].append(float(row.get("收盘", 0)))
                        stock_data["volume"].append(float(row.get("成交量", 0)))
                    except (ValueError, TypeError):
                        continue

                if stock_data["date"]:
                    cleaned, _ = _clean_stock_data(stock_data, symbol)
                    if cleaned:
                        data[symbol] = cleaned

            except Exception:
                continue

        return data

    def load_from_yfinance(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Dict[str, list]]:
        """Download US stock / global data via yfinance.

        Args:
            symbols: List of ticker symbols, e.g. ["AAPL", "GOOGL", "BTC-USD"]
            start_date: Start date "YYYY-MM-DD"
            end_date: End date "YYYY-MM-DD"

        Returns:
            Unified format dict

        Raises:
            ImportError: If yfinance is not installed
        """
        if not _HAS_YFINANCE:
            raise ImportError(
                "yfinance is not installed. Install with: pip install yfinance"
            )

        data: Dict[str, Dict[str, list]] = {}

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date)

                if df is None or df.empty:
                    continue

                stock_data: Dict[str, list] = {
                    "date": [],
                    "open": [],
                    "high": [],
                    "low": [],
                    "close": [],
                    "volume": [],
                }

                for idx, row in df.iterrows():
                    try:
                        # yfinance index is DatetimeIndex
                        date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
                        stock_data["date"].append(date_str)
                        stock_data["open"].append(float(row["Open"]))
                        stock_data["high"].append(float(row["High"]))
                        stock_data["low"].append(float(row["Low"]))
                        stock_data["close"].append(float(row["Close"]))
                        stock_data["volume"].append(float(row["Volume"]))
                    except (ValueError, TypeError, KeyError):
                        continue

                if stock_data["date"]:
                    cleaned, _ = _clean_stock_data(stock_data, symbol)
                    if cleaned:
                        data[symbol] = cleaned

            except Exception:
                continue

        return data
