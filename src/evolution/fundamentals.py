"""
Fundamental data fetcher for A-share stocks.
Uses BaoStock (free, no API key) for:
- PE ratio (price/earnings)
- PB ratio (price/book)
- ROE (return on equity)
- Revenue growth rate
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_fundamentals_baostock(
    codes: List[str], cache_dir: str = "data/fundamentals"
) -> Dict[str, Dict[str, float]]:
    """Fetch fundamental data for a list of stock codes.

    Uses BaoStock query_profit_data and query_growth_data.
    Results are cached to disk (1 day TTL) to avoid repeated API calls.

    Args:
        codes: List of stock codes like ['sh.600438', 'sz.000001']
        cache_dir: Directory for caching results

    Returns:
        Dict mapping code -> {pe, pb, roe, revenue_growth, profit_growth}
    """
    if not codes:
        return {}

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")
    cache_file = cache_path / f"{today_str}.json"

    # Check cache first
    cached: Dict[str, Dict[str, float]] = {}
    if cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            age_seconds = time.time() - mtime
            if age_seconds < 86400:  # 1 day TTL
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                # If all requested codes are cached, return immediately
                uncached = [c for c in codes if c not in cached]
                if not uncached:
                    return {c: cached[c] for c in codes if c in cached}
        except (json.JSONDecodeError, OSError):
            cached = {}

    # Try to import baostock — graceful degradation if not installed
    try:
        import baostock as bs  # type: ignore
    except ImportError:
        return {c: cached[c] for c in codes if c in cached}

    uncached = [c for c in codes if c not in cached]
    if not uncached:
        return {c: cached[c] for c in codes if c in cached}

    # Login to baostock (anonymous, free)
    try:
        lg = bs.login()
    except Exception:
        return {c: cached[c] for c in codes if c in cached}

    try:
        # Determine latest available quarter
        now = datetime.now()
        year = now.year
        month = now.month
        # Quarterly data lags: use previous quarter
        if month <= 3:
            query_year = year - 1
            query_quarter = 3  # Q3 of previous year (conservative)
        elif month <= 6:
            query_year = year
            query_quarter = 1
        elif month <= 9:
            query_year = year
            query_quarter = 2
        else:
            query_year = year
            query_quarter = 3

        for code in uncached:
            fund: Dict[str, float] = {}
            try:
                # Query profitability data (PE, PB, ROE)
                rs_profit = bs.query_profit_data(
                    code=code, year=query_year, quarter=query_quarter
                )
                if (
                    rs_profit is not None
                    and hasattr(rs_profit, "error_code")
                    and rs_profit.error_code == "0"
                ):
                    profit_rows = []
                    while rs_profit.next():
                        profit_rows.append(rs_profit.get_row_data())
                    if profit_rows:
                        row = profit_rows[-1]  # latest entry
                        fields = rs_profit.fields if hasattr(rs_profit, "fields") else []
                        field_map = {f: i for i, f in enumerate(fields)}

                        # ROE
                        if "roeAvg" in field_map:
                            val = row[field_map["roeAvg"]]
                            if val and val != "":
                                fund["roe"] = float(val)

                # Query growth data (revenue growth, profit growth)
                rs_growth = bs.query_growth_data(
                    code=code, year=query_year, quarter=query_quarter
                )
                if (
                    rs_growth is not None
                    and hasattr(rs_growth, "error_code")
                    and rs_growth.error_code == "0"
                ):
                    growth_rows = []
                    while rs_growth.next():
                        growth_rows.append(rs_growth.get_row_data())
                    if growth_rows:
                        row = growth_rows[-1]
                        fields = rs_growth.fields if hasattr(rs_growth, "fields") else []
                        field_map = {f: i for i, f in enumerate(fields)}

                        if "YOYEquity" in field_map:
                            val = row[field_map["YOYEquity"]]
                            if val and val != "":
                                fund["revenue_growth"] = float(val)
                        if "YOYNI" in field_map:
                            val = row[field_map["YOYNI"]]
                            if val and val != "":
                                fund["profit_growth"] = float(val)

                # Query valuation (PE, PB) from daily k-line with adjustflag
                # BaoStock provides PE/PB via query_history_k_data with ipoDate
                # Alternative: use dupont data or derive from other fields
                rs_dupont = bs.query_dupont_data(
                    code=code, year=query_year, quarter=query_quarter
                )
                if (
                    rs_dupont is not None
                    and hasattr(rs_dupont, "error_code")
                    and rs_dupont.error_code == "0"
                ):
                    dupont_rows = []
                    while rs_dupont.next():
                        dupont_rows.append(rs_dupont.get_row_data())
                    if dupont_rows:
                        row = dupont_rows[-1]
                        fields = rs_dupont.fields if hasattr(rs_dupont, "fields") else []
                        field_map = {f: i for i, f in enumerate(fields)}

                        # Try to extract PE from dupontROE and other fields
                        # PE and PB are often available from specific queries
                        # For now, use placeholders if not available from dupont

                # PE/PB: query from history k-line data (contains peTTM, pbMRQ)
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                rs_kline = bs.query_history_k_data_plus(
                    code,
                    "date,peTTM,pbMRQ",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3",
                )
                if (
                    rs_kline is not None
                    and hasattr(rs_kline, "error_code")
                    and rs_kline.error_code == "0"
                ):
                    kline_rows = []
                    while rs_kline.next():
                        kline_rows.append(rs_kline.get_row_data())
                    if kline_rows:
                        row = kline_rows[-1]  # latest day
                        fields = rs_kline.fields if hasattr(rs_kline, "fields") else []
                        field_map = {f: i for i, f in enumerate(fields)}

                        if "peTTM" in field_map:
                            val = row[field_map["peTTM"]]
                            if val and val != "":
                                fund["pe"] = float(val)
                        if "pbMRQ" in field_map:
                            val = row[field_map["pbMRQ"]]
                            if val and val != "":
                                fund["pb"] = float(val)

            except Exception:
                pass  # skip this stock on error

            if fund:
                cached[code] = fund

    finally:
        try:
            bs.logout()
        except Exception:
            pass

    # Save updated cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cached, f, indent=2, ensure_ascii=False)
    except OSError:
        pass

    return {c: cached[c] for c in codes if c in cached}


def compute_pe_score(pe: float, sector_avg_pe: float = 25.0) -> float:
    """Score PE ratio relative to sector average. Lower PE = higher score.
    Returns 0-1 score."""
    if pe <= 0 or pe > 200:
        return 0.0
    ratio = pe / sector_avg_pe
    if ratio < 0.5:
        return 1.0  # very undervalued
    elif ratio < 1.0:
        return 0.8 - (ratio - 0.5) * 0.6  # undervalued
    elif ratio < 1.5:
        return 0.5 - (ratio - 1.0) * 0.6  # fair
    else:
        return max(0.0, 0.2 - (ratio - 1.5) * 0.2)  # overvalued


def compute_growth_score(revenue_growth: float) -> float:
    """Score revenue growth rate. Higher growth = higher score.
    revenue_growth is in percentage (e.g., 30.0 for 30%).
    Returns 0-1 score."""
    if revenue_growth > 50:
        return 1.0
    elif revenue_growth > 30:
        return 0.8
    elif revenue_growth > 15:
        return 0.6
    elif revenue_growth > 0:
        return 0.4
    elif revenue_growth > -10:
        return 0.2
    else:
        return 0.0


def compute_roe_score(roe: float) -> float:
    """Score ROE. Higher ROE = higher score.
    roe is in percentage (e.g., 15.0 for 15%).
    Returns 0-1 score."""
    if roe > 25:
        return 1.0
    elif roe > 15:
        return 0.8
    elif roe > 10:
        return 0.6
    elif roe > 5:
        return 0.4
    elif roe > 0:
        return 0.2
    else:
        return 0.0


def compute_pb_score(pb: float) -> float:
    """Score PB ratio. Lower PB = higher score (value investing).
    Returns 0-1 score."""
    if pb <= 0:
        return 0.0
    if pb < 1.0:
        return 1.0  # trading below book value
    elif pb < 2.0:
        return 0.7
    elif pb < 3.0:
        return 0.5
    elif pb < 5.0:
        return 0.3
    else:
        return 0.1
