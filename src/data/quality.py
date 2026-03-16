"""
Data Quality Checker — Validate and clean financial time series data.

Detects missing dates, gaps, outliers, stale prices, and corporate actions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DataQualityReport:
    """Report from data quality check."""
    missing_dates: list[str] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)  # {start, end, business_days}
    outliers: list[dict] = field(default_factory=list)  # {date, column, value, zscore}
    stale_prices: list[dict] = field(default_factory=list)  # {start, end, days, price}
    corporate_actions: list[dict] = field(default_factory=list)  # {date, type, ratio}
    total_rows: int = 0
    date_range: tuple[str, str] = ("", "")
    score: float = 100.0  # 0-100 quality score

    def summary(self) -> str:
        lines = [
            f"=== Data Quality Report (Score: {self.score:.0f}/100) ===",
            f"Rows: {self.total_rows} | Range: {self.date_range[0]} to {self.date_range[1]}",
            f"Missing dates: {len(self.missing_dates)}",
            f"Gaps: {len(self.gaps)}",
            f"Outliers: {len(self.outliers)}",
            f"Stale price periods: {len(self.stale_prices)}",
            f"Potential corporate actions: {len(self.corporate_actions)}",
        ]
        return "\n".join(lines)


class DataQualityChecker:
    """Check and clean financial time series data quality."""

    def __init__(self, outlier_threshold: float = 4.0,
                 stale_threshold: int = 3,
                 split_threshold: float = 0.4):
        """
        Args:
            outlier_threshold: Z-score threshold for outlier detection
            stale_threshold: Days of unchanged price to flag as stale
            split_threshold: Min daily return magnitude to flag as potential split
        """
        self.outlier_threshold = outlier_threshold
        self.stale_threshold = stale_threshold
        self.split_threshold = split_threshold

    def check(self, data: pd.DataFrame) -> DataQualityReport:
        """
        Run quality checks on price data.

        Expects DataFrame with DatetimeIndex (or 'date' column) and
        at minimum a 'close' column. Optionally 'open', 'high', 'low', 'volume'.
        """
        df = self._normalize(data)
        report = DataQualityReport()

        if df.empty:
            report.score = 0
            return report

        report.total_rows = len(df)
        report.date_range = (str(df.index[0].date()), str(df.index[-1].date()))

        # Check missing dates
        report.missing_dates = self._check_missing_dates(df)

        # Check gaps
        report.gaps = self._check_gaps(df)

        # Check outliers
        report.outliers = self._check_outliers(df)

        # Check stale prices
        report.stale_prices = self._check_stale(df)

        # Check corporate actions
        report.corporate_actions = self._check_corporate_actions(df)

        # Calculate score
        report.score = self._calculate_score(report)

        return report

    def clean(self, data: pd.DataFrame, config: Optional[dict] = None) -> pd.DataFrame:
        """
        Clean data based on config options.

        Config options:
            fill_gaps: bool (forward fill gaps, default True)
            remove_outliers: bool (clip outliers, default False)
            adjust_splits: bool (adjust for detected splits, default False)
            drop_stale: bool (remove stale periods, default False)
        """
        cfg = config or {}
        df = self._normalize(data).copy()

        if cfg.get('fill_gaps', True):
            # Forward fill up to 5 business days
            df = df.asfreq('B')
            df = df.ffill(limit=5)
            df = df.dropna(subset=['close'])

        if cfg.get('remove_outliers', False):
            for col in ['close', 'open', 'high', 'low']:
                if col in df.columns:
                    returns = df[col].pct_change()
                    mean = returns.mean()
                    std = returns.std()
                    if std > 0:
                        z = (returns - mean) / std
                        mask = z.abs() > self.outlier_threshold
                        df.loc[mask, col] = np.nan
                        df[col] = df[col].ffill()

        if cfg.get('adjust_splits', False):
            actions = self._check_corporate_actions(df)
            for action in actions:
                if action['type'] == 'split':
                    date = pd.Timestamp(action['date'])
                    ratio = action['ratio']
                    mask = df.index < date
                    for col in ['close', 'open', 'high', 'low']:
                        if col in df.columns:
                            df.loc[mask, col] *= ratio
                    if 'volume' in df.columns:
                        df.loc[mask, 'volume'] /= ratio

        if cfg.get('drop_stale', False):
            stale = self._check_stale(df)
            for period in stale:
                start = pd.Timestamp(period['start'])
                end = pd.Timestamp(period['end'])
                df = df[(df.index < start) | (df.index > end)]

        return df

    def _normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Ensure DatetimeIndex and lowercase columns."""
        df = data.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass

        df = df.sort_index()
        return df

    def _check_missing_dates(self, df: pd.DataFrame) -> list[str]:
        """Find business days missing from the data."""
        if len(df) < 2:
            return []
        full_range = pd.bdate_range(df.index[0], df.index[-1])
        missing = full_range.difference(df.index)
        return [str(d.date()) for d in missing]

    def _check_gaps(self, df: pd.DataFrame) -> list[dict]:
        """Find significant gaps (>3 business days)."""
        gaps = []
        if len(df) < 2:
            return gaps

        diffs = pd.Series(df.index[1:]) - pd.Series(df.index[:-1])
        for i, diff in enumerate(diffs):
            bdays = np.busday_count(
                df.index[i].date(), df.index[i + 1].date()
            )
            if bdays > 3:
                gaps.append({
                    'start': str(df.index[i].date()),
                    'end': str(df.index[i + 1].date()),
                    'business_days': int(bdays),
                })
        return gaps

    def _check_outliers(self, df: pd.DataFrame) -> list[dict]:
        """Find extreme price moves (z-score based)."""
        outliers = []
        if 'close' not in df.columns or len(df) < 10:
            return outliers

        returns = df['close'].pct_change().dropna()
        if returns.std() == 0:
            return outliers

        z_scores = (returns - returns.mean()) / returns.std()

        for date, z in z_scores.items():
            if abs(z) > self.outlier_threshold:
                outliers.append({
                    'date': str(date.date()) if hasattr(date, 'date') else str(date),
                    'column': 'close',
                    'value': float(df.loc[date, 'close']),
                    'zscore': float(z),
                })
        return outliers

    def _check_stale(self, df: pd.DataFrame) -> list[dict]:
        """Find periods of unchanged prices."""
        stale = []
        if 'close' not in df.columns or len(df) < self.stale_threshold:
            return stale

        prices = df['close'].values
        run_start = 0
        for i in range(1, len(prices)):
            if prices[i] != prices[run_start]:
                run_len = i - run_start
                if run_len >= self.stale_threshold:
                    stale.append({
                        'start': str(df.index[run_start].date()),
                        'end': str(df.index[i - 1].date()),
                        'days': run_len,
                        'price': float(prices[run_start]),
                    })
                run_start = i

        # Check final run
        run_len = len(prices) - run_start
        if run_len >= self.stale_threshold:
            stale.append({
                'start': str(df.index[run_start].date()),
                'end': str(df.index[-1].date()),
                'days': run_len,
                'price': float(prices[run_start]),
            })

        return stale

    def _check_corporate_actions(self, df: pd.DataFrame) -> list[dict]:
        """Detect potential stock splits and dividends from price jumps."""
        actions = []
        if 'close' not in df.columns or len(df) < 2:
            return actions

        returns = df['close'].pct_change().dropna()

        for date, ret in returns.items():
            abs_ret = abs(ret)
            if abs_ret >= self.split_threshold:
                # Likely a split
                ratio = 1 / (1 + ret) if ret < 0 else (1 + ret)
                # Check common split ratios
                common_ratios = [2, 3, 4, 5, 0.5, 0.333, 0.25, 0.2]
                is_split = any(abs(ratio - cr) < 0.1 for cr in common_ratios)

                actions.append({
                    'date': str(date.date()) if hasattr(date, 'date') else str(date),
                    'type': 'split' if is_split else 'large_move',
                    'ratio': round(float(ratio), 4),
                    'return': round(float(ret), 4),
                })

        return actions

    def _calculate_score(self, report: DataQualityReport) -> float:
        """Calculate quality score 0-100."""
        score = 100.0
        total = max(report.total_rows, 1)

        # Missing dates penalty (up to -20)
        missing_pct = len(report.missing_dates) / max(total, 1)
        score -= min(20, missing_pct * 100)

        # Gap penalty (up to -20)
        score -= min(20, len(report.gaps) * 5)

        # Outlier penalty (up to -15)
        score -= min(15, len(report.outliers) * 3)

        # Stale penalty (up to -15)
        stale_days = sum(s['days'] for s in report.stale_prices)
        score -= min(15, (stale_days / max(total, 1)) * 100)

        # Corporate action penalty (up to -10)
        score -= min(10, len(report.corporate_actions) * 2)

        # Minimum data penalty
        if total < 30:
            score -= 20

        return max(0, round(score, 1))
