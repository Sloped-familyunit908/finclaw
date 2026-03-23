"""
Daily A-Share Data Update Script
=================================
Downloads today's A-share data and appends to existing CSVs in data/a_shares/.
Uses AKShare (ak.stock_zh_a_spot_em()) for real-time/today's market snapshot.

Run after market close (15:00 Beijing time = 07:00 UTC):
  python scripts/update_daily_data.py

CSV format: date,code,open,high,low,close,volume,amount,turn
Only updates stocks that already have local CSV files.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Project root
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "a_shares"

# Beijing timezone offset
BJT = timezone(timedelta(hours=8))


def get_today_str():
    """Get today's date string in Beijing time (YYYY-MM-DD)."""
    return datetime.now(BJT).strftime("%Y-%m-%d")


def update_all(dry_run=False):
    """Download today's A-share data and append to existing stock CSVs.
    
    Args:
        dry_run: If True, only print what would be done without writing files.
    """
    try:
        import akshare as ak
    except ImportError:
        print("ERROR: akshare not installed. Install with:")
        print("  pip install akshare")
        sys.exit(1)

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        print("Run download_a_shares.py first to create the initial dataset.")
        sys.exit(1)

    today = get_today_str()
    print(f"[update_daily_data] Date: {today}")
    print(f"[update_daily_data] Data dir: {DATA_DIR}")

    # Get all A-share spot data (real-time / today's snapshot)
    print("[update_daily_data] Fetching A-share spot data via AKShare...")
    t0 = time.time()
    try:
        df = ak.stock_zh_a_spot_em()
    except Exception as e:
        print(f"ERROR: Failed to fetch data from AKShare: {e}")
        sys.exit(1)
    elapsed = time.time() - t0
    print(f"[update_daily_data] Got {len(df)} stocks in {elapsed:.1f}s")

    # Log available columns for debugging
    print(f"[update_daily_data] Columns: {list(df.columns)}")

    # Map AKShare column names to our CSV format
    # AKShare stock_zh_a_spot_em() typical columns:
    #   序号, 代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额,
    #   振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, ...
    col_map = {
        "code": "代码",
        "open": "今开",
        "high": "最高",
        "low": "最低",
        "close": "最新价",
        "volume": "成交量",
        "amount": "成交额",
        "turn": "换手率",
    }

    # Verify all required columns exist
    missing = [v for v in col_map.values() if v not in df.columns]
    if missing:
        print(f"WARNING: Missing columns in AKShare data: {missing}")
        print(f"Available columns: {list(df.columns)}")
        # Try alternative column names
        alt_map = {
            "换手率": ["换手率(%)", "turnover"],
        }
        for col in missing:
            for alt in alt_map.get(col, []):
                if alt in df.columns:
                    # Find the key that maps to this col
                    for k, v in col_map.items():
                        if v == col:
                            col_map[k] = alt
                            print(f"  Using alternative: {col} -> {alt}")
                            break
                    break

    updated = 0
    skipped_nofile = 0
    skipped_exists = 0
    skipped_nodata = 0
    errors = 0

    for _, row in df.iterrows():
        try:
            code = str(row[col_map["code"]]).strip()
        except (KeyError, ValueError):
            continue

        # Determine exchange prefix
        if code.startswith("6") or code.startswith("688"):
            prefix = "sh"
        elif code.startswith("0") or code.startswith("3"):
            prefix = "sz"
        else:
            # Skip BJ/other exchange stocks
            continue

        filename = f"{prefix}_{code}.csv"
        filepath = DATA_DIR / filename

        # Only update stocks that already have local CSV files
        if not filepath.exists():
            skipped_nofile += 1
            continue

        # Check if today's data already exists (check last line)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                if today in last_line:
                    skipped_exists += 1
                    continue
        except Exception as e:
            errors += 1
            continue

        # Extract values from AKShare row
        try:
            open_val = row.get(col_map["open"], 0)
            high_val = row.get(col_map["high"], 0)
            low_val = row.get(col_map["low"], 0)
            close_val = row.get(col_map["close"], 0)
            volume_val = row.get(col_map["volume"], 0)
            amount_val = row.get(col_map["amount"], 0)
            turn_val = row.get(col_map["turn"], 0)

            # Skip if no trading data (suspended stocks, etc.)
            if close_val is None or close_val == 0 or str(close_val) == "nan":
                skipped_nodata += 1
                continue
            if open_val is None or open_val == 0 or str(open_val) == "nan":
                skipped_nodata += 1
                continue

            # Format values to match existing CSV precision
            # Volume in AKShare is in units (shares), same as BaoStock
            # Amount is in yuan
            # Turn is percentage (e.g., 1.23 means 1.23%)
            # Convert turn from percentage to decimal if needed
            turn_float = float(turn_val) if turn_val and str(turn_val) != "nan" else 0
            # AKShare stores turn as percentage (e.g., 10.03 means 10.03%)
            # BaoStock stores turn as a fraction (e.g., 0.1003 for 10.03%)
            # BUT for indices, BaoStock turn can be > 1.0 (e.g., 1.37 = 137%)
            # AKShare values are always in percentage form, so always divide by 100
            turn_decimal = turn_float / 100.0

            code_prefix = f"{prefix}.{code}"
            new_row = (
                f"{today},{code_prefix},"
                f"{float(open_val):.10f},{float(high_val):.10f},"
                f"{float(low_val):.10f},{float(close_val):.10f},"
                f"{int(float(volume_val))},{float(amount_val):.4f},"
                f"{turn_decimal:.6f}"
            )
        except Exception as e:
            errors += 1
            continue

        if dry_run:
            if updated < 5:
                print(f"  [dry-run] Would append to {filename}: {new_row}")
            updated += 1
            continue

        # Append new row
        try:
            # Ensure file ends with newline before appending
            needs_newline = False
            if lines and not lines[-1].endswith("\n"):
                needs_newline = True

            with open(filepath, "a", encoding="utf-8") as f:
                if needs_newline:
                    f.write("\n")
                f.write(new_row + "\n")
            updated += 1
        except Exception as e:
            errors += 1

    mode_str = "[dry-run] " if dry_run else ""
    print(f"\n=== {mode_str}Update Summary for {today} ===")
    print(f"  Updated:          {updated}")
    print(f"  Already current:  {skipped_exists}")
    print(f"  No local file:    {skipped_nofile}")
    print(f"  No trading data:  {skipped_nodata}")
    print(f"  Errors:           {errors}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Update daily A-share data")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without writing files")
    args = parser.parse_args()
    update_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
