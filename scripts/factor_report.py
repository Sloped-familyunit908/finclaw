#!/usr/bin/env python
"""
Factor Quality Report CLI
==========================

Usage::

    python scripts/factor_report.py --data-dir data/a_shares --output factor_quality_report.json

Reads CSV or JSON stock data from ``--data-dir``, loads all factors from
the ``factors/`` directory, runs the IC/IR/decay analysis, and writes
a JSON report.
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Allow running from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evolution.factor_discovery import FactorRegistry
from src.evolution.factor_quality import FactorQualityAnalyzer


def load_stock_data_from_dir(data_dir: str) -> dict:
    """Load stock data from a directory of CSV files.

    Expected CSV columns: date, open, high, low, close, volume.
    Each file name (minus extension) is used as the stock code.
    """
    stock_data: dict = {}
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"[error] data directory not found: {data_dir}")
        return stock_data

    for fp in sorted(data_path.iterdir()):
        if fp.suffix.lower() not in (".csv", ".json"):
            continue
        code = fp.stem
        try:
            if fp.suffix.lower() == ".json":
                with open(fp, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    stock_data[code] = {
                        "date": raw.get("date", []),
                        "open": [float(x) for x in raw.get("open", [])],
                        "high": [float(x) for x in raw.get("high", [])],
                        "low": [float(x) for x in raw.get("low", [])],
                        "close": [float(x) for x in raw.get("close", [])],
                        "volume": [float(x) for x in raw.get("volume", [])],
                    }
            else:
                dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
                with open(fp, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        dates.append(row.get("date", ""))
                        opens.append(float(row.get("open", 0)))
                        highs.append(float(row.get("high", 0)))
                        lows.append(float(row.get("low", 0)))
                        closes.append(float(row.get("close", 0)))
                        volumes.append(float(row.get("volume", 0)))
                stock_data[code] = {
                    "date": dates,
                    "open": opens,
                    "high": highs,
                    "low": lows,
                    "close": closes,
                    "volume": volumes,
                }
        except Exception as e:
            print(f"  [warn] failed to load {fp.name}: {e}")

    return stock_data


def main():
    parser = argparse.ArgumentParser(
        description="Generate factor quality report (IC / IR / decay / tiering)."
    )
    parser.add_argument(
        "--data-dir",
        default="data/a_shares",
        help="Directory containing stock CSV/JSON files (default: data/a_shares)",
    )
    parser.add_argument(
        "--factors-dir",
        default="factors",
        help="Directory containing factor .py files (default: factors)",
    )
    parser.add_argument(
        "--output",
        default="factor_quality_report.json",
        help="Output JSON report path (default: factor_quality_report.json)",
    )
    parser.add_argument(
        "--max-stocks",
        type=int,
        default=100,
        help="Max stocks to sample for speed (default: 100)",
    )
    args = parser.parse_args()

    print(f"[1/4] Loading stock data from {args.data_dir} ...")
    stock_data = load_stock_data_from_dir(args.data_dir)
    if not stock_data:
        print("[error] No stock data loaded. Exiting.")
        sys.exit(1)
    print(f"       Loaded {len(stock_data)} stocks")

    print(f"[2/4] Loading factors from {args.factors_dir} ...")
    registry = FactorRegistry(args.factors_dir)
    n_loaded = registry.load_all()
    print(f"       Loaded {n_loaded} factors")
    if n_loaded == 0:
        print("[error] No factors loaded. Exiting.")
        sys.exit(1)

    print("[3/4] Running IC / IR / decay analysis ...")
    analyzer = FactorQualityAnalyzer(stock_data, registry, max_stocks=args.max_stocks)
    analyzer.analyze_all()

    print("[4/4] Generating report ...")
    report = analyzer.generate_factor_report()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    ts = report["tier_summary"]
    print(f"\n=== Factor Quality Report ===")
    print(f"Total factors : {report['total_factors']}")
    print(f"Tier A (strong) : {ts['A']}")
    print(f"Tier B (useful) : {ts['B']}")
    print(f"Tier C (marginal): {ts['C']}")
    print(f"Tier D (noise)  : {ts['D']}")
    print(f"Keep : {report['recommendations']['keep_count']}")
    print(f"Drop : {report['recommendations']['drop_count']}")
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
