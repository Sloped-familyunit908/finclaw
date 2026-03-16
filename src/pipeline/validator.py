"""
Data Validator
Validate and clean price data: detect gaps, outliers, and missing values.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import math


@dataclass
class ValidationReport:
    total_bars: int
    missing_dates: int
    outliers_removed: int
    gaps_filled: int
    issues: list[str] = field(default_factory=list)
    is_valid: bool = True


class DataValidator:
    """Validate and clean OHLCV price data."""

    def __init__(
        self,
        max_daily_change: float = 0.50,  # 50% max daily move
        max_gap_days: int = 5,           # max allowed gap
        min_price: float = 0.0001,
    ):
        self.max_daily_change = max_daily_change
        self.max_gap_days = max_gap_days
        self.min_price = min_price

    def validate(self, bars: list[dict]) -> ValidationReport:
        """Validate without modifying data."""
        report = ValidationReport(total_bars=len(bars), missing_dates=0,
                                  outliers_removed=0, gaps_filled=0)
        if len(bars) < 2:
            report.issues.append("fewer than 2 bars")
            report.is_valid = False
            return report

        for i in range(1, len(bars)):
            price = bars[i].get("price", 0)
            prev_price = bars[i-1].get("price", 0)

            if price <= self.min_price:
                report.issues.append(f"bar {i}: price {price} below minimum")
                report.is_valid = False

            if prev_price > 0:
                change = abs(price / prev_price - 1)
                if change > self.max_daily_change:
                    report.outliers_removed += 1
                    report.issues.append(f"bar {i}: {change:.1%} daily change")

            # Date gaps
            d1 = bars[i-1].get("date")
            d2 = bars[i].get("date")
            if isinstance(d1, datetime) and isinstance(d2, datetime):
                gap = (d2 - d1).days
                if gap > self.max_gap_days:
                    report.missing_dates += gap - 1
                    report.issues.append(f"bar {i}: {gap}-day gap")

        return report

    def clean(self, bars: list[dict]) -> tuple[list[dict], ValidationReport]:
        """Clean data: remove outliers, fill small gaps with interpolation."""
        report = self.validate(bars)
        if len(bars) < 2:
            return bars, report

        cleaned = [bars[0]]
        for i in range(1, len(bars)):
            price = bars[i].get("price", 0)
            prev_price = cleaned[-1].get("price", 0)

            if price <= self.min_price:
                continue  # skip invalid

            if prev_price > 0:
                change = abs(price / prev_price - 1)
                if change > self.max_daily_change:
                    # Replace with interpolated value
                    bars[i] = {**bars[i], "price": prev_price}
                    report.outliers_removed += 1

            cleaned.append(bars[i])

        report.total_bars = len(cleaned)
        return cleaned, report
