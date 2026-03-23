"""
Market Index Safety Filter
============================
Checks if the broad A-share market is safe for buying today.
Uses Shanghai Composite (sh_000001.csv) as the reference index.

Usage as script:
    python scripts/market_filter.py

Usage as importable module:
    from scripts.market_filter import is_market_safe
    result = is_market_safe()
    if result["safe"]:
        # proceed with buying
    else:
        print(result["reason"])

Safety levels:
    "ok"      -- normal trading, no concerns
    "caution" -- 1d drop > 1% or 3d drop > 2%, reduce position size
    "danger"  -- 1d drop > 2% or 3d drop > 4%, DO NOT BUY
"""

import csv
import os
import sys
from pathlib import Path

# Project root (works whether imported or run directly)
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = str(ROOT / "data" / "a_shares")


def _load_closes(csv_path):
    """Load close prices from a stock CSV file.
    
    Returns:
        list of (date_str, close_float) tuples, oldest first.
    """
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            try:
                close = float(row["close"])
                date = row["date"]
                rows.append((date, close))
            except (ValueError, KeyError):
                continue
    return rows


def is_market_safe(data_dir=None):
    """Check if the broad market is safe for buying.
    
    Reads Shanghai Composite index (sh_000001.csv) and computes
    recent return metrics to determine market safety level.
    
    Args:
        data_dir: Path to data/a_shares/ directory. 
                  Defaults to project data/a_shares/.
    
    Returns:
        dict with keys:
            safe (bool): True if ok to buy, False if danger
            index_return_1d (float): 1-day return in percent
            index_return_3d (float): 3-day cumulative return in percent
            index_return_5d (float): 5-day cumulative return in percent
            level (str): "ok", "caution", or "danger"
            reason (str): Human-readable explanation
            last_date (str): Date of the last data point
            last_close (float): Last close price
    """
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    
    index_path = os.path.join(data_dir, "sh_000001.csv")
    
    if not os.path.exists(index_path):
        return {
            "safe": True,
            "index_return_1d": 0.0,
            "index_return_3d": 0.0,
            "index_return_5d": 0.0,
            "level": "unknown",
            "reason": "Index file not found: sh_000001.csv -- cannot assess market safety",
            "last_date": "",
            "last_close": 0.0,
        }
    
    data = _load_closes(index_path)
    
    if len(data) < 6:
        return {
            "safe": True,
            "index_return_1d": 0.0,
            "index_return_3d": 0.0,
            "index_return_5d": 0.0,
            "level": "unknown",
            "reason": f"Not enough data ({len(data)} rows) to assess market safety",
            "last_date": data[-1][0] if data else "",
            "last_close": data[-1][1] if data else 0.0,
        }
    
    last_date = data[-1][0]
    last_close = data[-1][1]
    
    # Compute returns
    # 1-day return: last close vs previous close
    prev_close_1d = data[-2][1]
    ret_1d = ((last_close / prev_close_1d) - 1.0) * 100.0 if prev_close_1d > 0 else 0.0
    
    # 3-day cumulative return: last close vs close 3 trading days ago
    close_3d_ago = data[-4][1] if len(data) >= 4 else data[0][1]
    ret_3d = ((last_close / close_3d_ago) - 1.0) * 100.0 if close_3d_ago > 0 else 0.0
    
    # 5-day cumulative return: last close vs close 5 trading days ago
    close_5d_ago = data[-6][1] if len(data) >= 6 else data[0][1]
    ret_5d = ((last_close / close_5d_ago) - 1.0) * 100.0 if close_5d_ago > 0 else 0.0
    
    # Determine safety level
    level = "ok"
    reason = "Market conditions normal -- safe to trade"
    safe = True
    
    # Check DANGER conditions first (most severe)
    if ret_1d < -2.0:
        level = "danger"
        reason = f"Shanghai Composite dropped {ret_1d:.1f}% today -- avoid buying"
        safe = False
    elif ret_3d < -4.0:
        level = "danger"
        reason = f"Shanghai Composite dropped {ret_3d:.1f}% in 3 days -- strong downtrend, avoid buying"
        safe = False
    # Check CAUTION conditions
    elif ret_1d < -1.0:
        level = "caution"
        reason = f"Shanghai Composite dropped {ret_1d:.1f}% today -- consider reducing position size"
        safe = True  # caution = still ok but smaller positions
    elif ret_3d < -2.0:
        level = "caution"
        reason = f"Shanghai Composite dropped {ret_3d:.1f}% in 3 days -- mild downtrend, reduce position size"
        safe = True
    
    return {
        "safe": safe,
        "index_return_1d": round(ret_1d, 2),
        "index_return_3d": round(ret_3d, 2),
        "index_return_5d": round(ret_5d, 2),
        "level": level,
        "reason": reason,
        "last_date": last_date,
        "last_close": round(last_close, 4),
    }


def print_market_status(result=None):
    """Print a formatted market safety report."""
    if result is None:
        result = is_market_safe()
    
    level_display = {
        "ok": "[OK]",
        "caution": "[CAUTION]",
        "danger": "[DANGER]",
        "unknown": "[UNKNOWN]",
    }
    
    print("=" * 60)
    print("  Market Safety Filter -- Shanghai Composite (sh.000001)")
    print("=" * 60)
    print(f"  Date:      {result['last_date']}")
    print(f"  Close:     {result['last_close']}")
    print(f"  1-day:     {result['index_return_1d']:+.2f}%")
    print(f"  3-day:     {result['index_return_3d']:+.2f}%")
    print(f"  5-day:     {result['index_return_5d']:+.2f}%")
    print(f"  Level:     {level_display.get(result['level'], result['level'])}")
    print(f"  Safe:      {'YES' if result['safe'] else 'NO'}")
    print(f"  Reason:    {result['reason']}")
    print("=" * 60)


def main():
    result = is_market_safe()
    print_market_status(result)
    # Exit with non-zero code if danger
    if result["level"] == "danger":
        sys.exit(1)


if __name__ == "__main__":
    main()
