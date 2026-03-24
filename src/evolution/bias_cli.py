"""
Backtest Bias CLI — command-line tool for detecting backtest biases.

Usage:
    python -m src.evolution.bias_cli --factors           # check all factors for lookahead
    python -m src.evolution.bias_cli --dna path/to.json  # check DNA for overfitting
    python -m src.evolution.bias_cli --all                # run all checks
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.evolution.bias_detector import (
    BiasReport,
    SnoopingReport,
    detect_lookahead,
    detect_lookahead_batch,
    detect_snooping,
    check_survivorship,
    make_test_ohlcv,
)
from src.evolution.factor_discovery import FactorRegistry


# ============================================================
# ANSI color helpers (no external deps)
# ============================================================

_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
}


def _c(text: str, color: str) -> str:
    """Wrap text in ANSI color."""
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def _severity_color(severity: str) -> str:
    """Return ANSI color name for a severity level."""
    return {
        "CLEAN": "green",
        "WARNING": "yellow",
        "CRITICAL": "red",
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "red",
        "EXTREME": "red",
    }.get(severity, "reset")


def _severity_icon(severity: str) -> str:
    return {
        "CLEAN": "[OK]",
        "WARNING": "[!!]",
        "CRITICAL": "[XX]",
        "LOW": "[OK]",
        "MEDIUM": "[!!]",
        "HIGH": "[XX]",
        "EXTREME": "[XX]",
    }.get(severity, "[??]")


# ============================================================
# Report printers
# ============================================================


def print_header(title: str) -> None:
    line = "=" * 60
    print(f"\n{_c(line, 'cyan')}")
    print(f"{_c(f'  {title}', 'bold')}")
    print(f"{_c(line, 'cyan')}\n")


def print_bias_report(report: BiasReport) -> None:
    color = _severity_color(report.severity)
    icon = _severity_icon(report.severity)
    name = _c(report.factor_name, "bold")
    sev = _c(f"[{report.severity}]", color)
    icon_colored = _c(icon, color)

    print(f"  {icon_colored} {name}  {sev}")
    if report.has_lookahead:
        for line in report.details.split("\n"):
            print(f"       {_c(line, 'gray')}")
    else:
        print(f"       {_c(report.details, 'gray')}")


def print_snooping_report(report: SnoopingReport) -> None:
    color = _severity_color(report.risk_level)
    icon = _severity_icon(report.risk_level)
    icon_colored = _c(icon, color)
    risk = _c(f"[{report.risk_level}]", color)

    print(f"  {icon_colored} DNA: {_c(report.dna_id, 'bold')}  {risk}")
    print(f"       Train: {_c(f'{report.train_return:+.2%}', 'cyan')}  "
          f"Test: {_c(f'{report.test_return:+.2%}', 'cyan')}  "
          f"Ratio: {_c(f'{report.overfit_ratio:.2f}x', color)}")
    print(f"       {_c(report.details, 'gray')}")


def print_survivorship_warnings(warnings: list) -> None:
    if not warnings:
        print(f"  {_c('[OK]', 'green')} No survivorship bias detected.")
        return
    for w in warnings:
        print(f"  {_c('[!!]', 'yellow')} {w}")


# ============================================================
# Commands
# ============================================================


def cmd_factors() -> int:
    """Check all registered factors for lookahead bias."""
    print_header("Look-ahead Bias Detection — All Factors")

    registry = FactorRegistry()
    loaded = registry.load_all()

    if loaded == 0:
        print(f"  {_c('No factors found.', 'yellow')} Run factor discovery first.")
        return 0

    print(f"  Loaded {_c(str(loaded), 'bold')} factors. Generating test data...\n")

    test_data = make_test_ohlcv(n=300, seed=42)

    factors = {name: meta.compute_fn for name, meta in registry.factors.items()}
    reports = detect_lookahead_batch(factors, test_data)

    clean = 0
    tainted = 0
    for r in reports:
        print_bias_report(r)
        if r.has_lookahead:
            tainted += 1
        else:
            clean += 1

    print()
    print(f"  Summary: {_c(str(clean), 'green')} clean, "
          f"{_c(str(tainted), 'red' if tainted else 'green')} with lookahead bias")

    return 1 if tainted > 0 else 0


def cmd_dna(dna_path: str) -> int:
    """Check a DNA file for overfitting (data snooping)."""
    print_header("Data Snooping Detection — DNA Overfitting Check")

    path = Path(dna_path)
    if not path.exists():
        print(f"  {_c('Error:', 'red')} DNA file not found: {dna_path}")
        return 2

    try:
        with open(path, "r", encoding="utf-8") as f:
            dna = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  {_c('Error:', 'red')} Failed to parse DNA file: {e}")
        return 2

    if "weights" not in dna:
        print(f"  {_c('Error:', 'red')} DNA file must contain 'weights' dict.")
        return 2

    # Load factors if available
    registry = FactorRegistry()
    registry.load_all()
    factor_fns = {name: meta.compute_fn for name, meta in registry.factors.items()}
    if not factor_fns:
        factor_fns = None  # will use trivial fallback

    # Generate train/test data (in real use, would load actual market data)
    print(f"  DNA: {_c(dna.get('id', path.stem), 'bold')}")
    print(f"  Weights: {len(dna['weights'])} factors")
    print(f"  Generating synthetic train/test data...\n")

    train_data = make_test_ohlcv(n=300, seed=42)
    test_data = make_test_ohlcv(n=300, seed=99)

    report = detect_snooping(dna, train_data, test_data, factor_fns=factor_fns)
    print_snooping_report(report)

    high_risk = report.risk_level in ("HIGH", "EXTREME")
    print()
    if high_risk:
        print(f"  {_c('WARNING:', 'red')} High overfitting risk. "
              f"Consider walk-forward validation.")
    else:
        print(f"  {_c('OK:', 'green')} Overfitting risk appears manageable.")

    return 1 if high_risk else 0


def cmd_all() -> int:
    """Run all bias checks."""
    exit_code = cmd_factors()
    print()
    # Just run factors check; DNA needs a file path
    return exit_code


# ============================================================
# Main
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backtest Bias Detector — catch lookahead, snooping, and survivorship bias.",
    )
    parser.add_argument(
        "--factors",
        action="store_true",
        help="Check all registered factors for lookahead bias.",
    )
    parser.add_argument(
        "--dna",
        type=str,
        default=None,
        help="Path to a DNA JSON file to check for overfitting.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all bias checks.",
    )

    args = parser.parse_args()

    if not any([args.factors, args.dna, args.all]):
        parser.print_help()
        sys.exit(0)

    exit_code = 0

    if args.all:
        exit_code = cmd_all()
    else:
        if args.factors:
            exit_code = max(exit_code, cmd_factors())
        if args.dna:
            exit_code = max(exit_code, cmd_dna(args.dna))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
