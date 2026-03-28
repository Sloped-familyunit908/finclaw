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

    Tries AKShare first (more reliable), falls back to BaoStock.
    Results are cached to disk (1 day TTL) to avoid repeated API calls.

    Args:
        codes: List of stock codes like ['sh_600438', 'sz_000001']
        cache_dir: Directory for caching results

    Returns:
        Dict mapping code -> {pe, pb, roe, revenue_growth, profit_growth}
    """
    # Check cache first
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    cache_file = cache_path / f"{today}.json"

    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached:
                return cached
        except Exception:
            pass

    results: Dict[str, Dict[str, float]] = {}

    # Try AKShare first — use batch API (stock_zh_a_spot_em returns PE for all stocks at once)
    try:
        import akshare as ak
        print("  [fundamentals] using AKShare batch API...")
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                raw_code = str(row.get('代码', ''))
                # Match to our code format (sh_600438 or sz_000001)
                if raw_code.startswith('6'):
                    code_key = f"sh_{raw_code}"
                else:
                    code_key = f"sz_{raw_code}"
                if code_key in codes:
                    try:
                        results[code_key] = {
                            "pe": float(row.get('市盈率-动态', 0) or 0),
                            "pb": float(row.get('市净率', 0) or 0),
                            "roe": 0,
                            "revenue_growth": 0,
                            "profit_growth": 0,
                            "gross_margin": 0,
                            "net_margin": 0,
                            "debt_ratio": 0,
                        }
                    except (ValueError, TypeError):
                        continue

        if results:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False)
            except Exception:
                pass
            print(f"  [fundamentals] got data for {len(results)} stocks via AKShare")
            return results
    except ImportError:
        pass
    except Exception as e:
        print(f"  [fundamentals] AKShare failed: {e}")

    # Fall back to BaoStock
    try:
        return _fetch_via_baostock(codes, cache_file)
    except Exception as e:
        print(f"  [fundamentals] BaoStock also failed: {e}")
        return {}


def _fetch_via_baostock(
    codes: List[str], cache_file: Path
) -> Dict[str, Dict[str, float]]:
    """Original BaoStock implementation as fallback."""
    if not codes:
        return {}

    cache_file.parent.mkdir(parents=True, exist_ok=True)

    today_str = datetime.now().strftime("%Y-%m-%d")

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

                # Query profit data for extended fields (gpMargin, npMargin)
                if "roe" in fund or True:  # always try
                    # Re-use rs_profit if we got it, otherwise gpMargin fields
                    # are extracted from the same query above.
                    # Extract gpMargin from profit data if available
                    try:
                        rs_profit2 = bs.query_profit_data(
                            code=code, year=query_year, quarter=query_quarter
                        )
                        if (
                            rs_profit2 is not None
                            and hasattr(rs_profit2, "error_code")
                            and rs_profit2.error_code == "0"
                        ):
                            profit2_rows = []
                            while rs_profit2.next():
                                profit2_rows.append(rs_profit2.get_row_data())
                            if profit2_rows:
                                row = profit2_rows[-1]
                                fields = rs_profit2.fields if hasattr(rs_profit2, "fields") else []
                                field_map = {f: i for i, f in enumerate(fields)}
                                if "gpMargin" in field_map:
                                    val = row[field_map["gpMargin"]]
                                    if val and val != "":
                                        fund["gross_margin"] = float(val) * 100  # to percentage
                                if "npMargin" in field_map:
                                    val = row[field_map["npMargin"]]
                                    if val and val != "":
                                        fund["net_margin"] = float(val) * 100
                    except Exception:
                        pass

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
                        if "YOYEPSBasic" in field_map:
                            val = row[field_map["YOYEPSBasic"]]
                            if val and val != "":
                                fund["eps_growth"] = float(val)

                # Query balance data (debt ratio)
                try:
                    rs_balance = bs.query_balance_data(
                        code=code, year=query_year, quarter=query_quarter
                    )
                    if (
                        rs_balance is not None
                        and hasattr(rs_balance, "error_code")
                        and rs_balance.error_code == "0"
                    ):
                        balance_rows = []
                        while rs_balance.next():
                            balance_rows.append(rs_balance.get_row_data())
                        if balance_rows:
                            row = balance_rows[-1]
                            fields = rs_balance.fields if hasattr(rs_balance, "fields") else []
                            field_map = {f: i for i, f in enumerate(fields)}
                            total_liab = None
                            total_assets = None
                            if "totalLiab" in field_map:
                                val = row[field_map["totalLiab"]]
                                if val and val != "":
                                    total_liab = float(val)
                            if "totalAssets" in field_map:
                                val = row[field_map["totalAssets"]]
                                if val and val != "":
                                    total_assets = float(val)
                            if total_liab is not None and total_assets and total_assets > 0:
                                fund["debt_ratio"] = total_liab / total_assets * 100
                except Exception:
                    pass

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


# === Growth Factors ===


def compute_revenue_yoy_score(revenue_yoy: float) -> float:
    """Revenue year-over-year growth. Higher = better."""
    if revenue_yoy > 100: return 1.0
    if revenue_yoy > 50: return 0.9
    if revenue_yoy > 30: return 0.8
    if revenue_yoy > 15: return 0.65
    if revenue_yoy > 5: return 0.5
    if revenue_yoy > 0: return 0.35
    if revenue_yoy > -10: return 0.2
    return 0.1


def compute_revenue_qoq_score(revenue_qoq: float) -> float:
    """Revenue quarter-over-quarter growth. Captures acceleration."""
    if revenue_qoq > 30: return 1.0
    if revenue_qoq > 15: return 0.8
    if revenue_qoq > 5: return 0.6
    if revenue_qoq > 0: return 0.4
    if revenue_qoq > -5: return 0.3
    return 0.1


def compute_profit_yoy_score(profit_yoy: float) -> float:
    """Net profit YoY growth."""
    if profit_yoy > 100: return 1.0
    if profit_yoy > 50: return 0.85
    if profit_yoy > 20: return 0.7
    if profit_yoy > 0: return 0.5
    if profit_yoy > -20: return 0.3
    return 0.1


def compute_profit_qoq_score(profit_qoq: float) -> float:
    """Net profit QoQ growth. Captures earnings momentum."""
    if profit_qoq > 50: return 1.0
    if profit_qoq > 20: return 0.8
    if profit_qoq > 5: return 0.6
    if profit_qoq > 0: return 0.4
    return 0.2


# === Valuation Factors ===


def compute_ps_score(ps: float) -> float:
    """Price-to-Sales. Lower = better for growth stocks."""
    if ps <= 0: return 0.0
    if ps < 1: return 1.0
    if ps < 3: return 0.7
    if ps < 5: return 0.5
    if ps < 10: return 0.3
    return 0.1


def compute_peg_score(pe: float, growth: float) -> float:
    """PEG ratio (PE / growth rate). < 1 = undervalued growth."""
    if growth <= 0 or pe <= 0: return 0.3
    peg = pe / growth
    if peg < 0.5: return 1.0
    if peg < 1.0: return 0.8
    if peg < 1.5: return 0.6
    if peg < 2.0: return 0.4
    return 0.2


# === Quality Factors ===


def compute_gross_margin_score(gross_margin: float) -> float:
    """Gross margin %. Higher = stronger pricing power."""
    if gross_margin > 60: return 1.0
    if gross_margin > 40: return 0.8
    if gross_margin > 25: return 0.6
    if gross_margin > 15: return 0.4
    return 0.2


def compute_debt_ratio_score(debt_ratio: float) -> float:
    """Asset-liability ratio. Lower = safer."""
    if debt_ratio < 20: return 1.0
    if debt_ratio < 40: return 0.8
    if debt_ratio < 55: return 0.6
    if debt_ratio < 70: return 0.4
    return 0.2


def compute_cashflow_score(ocf_to_profit: float) -> float:
    """Operating cash flow / net profit. Higher = better earnings quality."""
    if ocf_to_profit > 1.5: return 1.0
    if ocf_to_profit > 1.0: return 0.8
    if ocf_to_profit > 0.5: return 0.5
    if ocf_to_profit > 0: return 0.3
    return 0.1


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
