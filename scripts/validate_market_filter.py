"""
Validate Market Filter Against Local A-Share Data
====================================================
Uses local data/a_shares/ CSV files to simulate cn_scanner stock selection
with and without broad market filter, comparing first-day loss rates.

Requires sh_000001.csv (上证指数) in data/a_shares/.
If missing, downloads it via BaoStock.

Outputs report to docs/market-filter-report.md
"""

from __future__ import annotations

import csv
import os
import sys
import numpy as np
from collections import defaultdict

# Project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "data", "a_shares")
DOCS_DIR = os.path.join(ROOT, "docs")
INDEX_FILE = os.path.join(DATA_DIR, "sh_000001.csv")


def ensure_index_data():
    """Download sh.000001 (上证指数) via BaoStock if not present."""
    if os.path.exists(INDEX_FILE):
        return True
    print("Downloading sh.000001 index via BaoStock...")
    try:
        import baostock as bs
        lg = bs.login()
        if lg.error_code != '0':
            print(f"BaoStock login failed: {lg.error_msg}")
            return False
        rs = bs.query_history_k_data_plus(
            "sh.000001",
            "date,code,open,high,low,close,volume,amount,turn",
            start_date="2024-03-01",
            end_date="2026-12-31",
            frequency="d",
            adjustflag="3",
        )
        rows = []
        while rs.error_code == '0' and rs.next():
            rows.append(rs.get_row_data())
        bs.logout()
        if len(rows) < 30:
            print(f"Only got {len(rows)} rows for sh.000001")
            return False
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(INDEX_FILE, 'w', encoding='utf-8', newline='') as f:
            f.write("date,code,open,high,low,close,volume,amount,turn\n")
            for row in rows:
                f.write(','.join(row) + '\n')
        print(f"Downloaded {len(rows)} bars to {INDEX_FILE}")
        return True
    except ImportError:
        print("baostock not installed. Run: pip install baostock")
        return False
    except Exception as e:
        print(f"Error downloading index data: {e}")
        return False


def load_csv(path: str) -> dict:
    """Load a CSV file into arrays. Returns {date, open, high, low, close, volume}."""
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return {}
    dates = [r['date'] for r in rows]
    close = np.array([float(r['close']) for r in rows], dtype=np.float64)
    open_ = np.array([float(r['open']) for r in rows], dtype=np.float64)
    high = np.array([float(r['high']) for r in rows], dtype=np.float64)
    low = np.array([float(r['low']) for r in rows], dtype=np.float64)
    vol_raw = [r.get('volume', '0') for r in rows]
    volume = np.array([float(v) if v else 0.0 for v in vol_raw], dtype=np.float64)
    return {
        'dates': dates, 'open': open_, 'high': high,
        'low': low, 'close': close, 'volume': volume,
    }


def align_dates(stock_dates, index_dates, index_close):
    """Return index close prices aligned to stock trading dates."""
    idx_map = {d: i for i, d in enumerate(index_dates)}
    aligned = []
    for d in stock_dates:
        if d in idx_map:
            aligned.append(index_close[idx_map[d]])
        else:
            aligned.append(np.nan)
    return np.array(aligned, dtype=np.float64)


def run_validation():
    """Main validation logic."""
    from src.cn_scanner import compute_score_v3, CN_UNIVERSE
    from src.market_filter import MarketFilter

    if not ensure_index_data():
        print("Cannot proceed without index data.")
        return

    index_data = load_csv(INDEX_FILE)
    if not index_data:
        print("Failed to load index data.")
        return

    index_dates = index_data['dates']
    index_close = index_data['close']
    print(f"Index data: {len(index_dates)} bars ({index_dates[0]} to {index_dates[-1]})")

    # Build ticker → local filename mapping
    universe_codes = {}
    for ticker, name, sector in CN_UNIVERSE:
        code = ticker.split('.')[0]
        exchange = ticker.split('.')[1]
        if exchange == 'SS':
            csv_name = f"sh_{code}.csv"
        elif exchange == 'SZ':
            csv_name = f"sz_{code}.csv"
        else:
            continue  # Skip HK stocks
        csv_path = os.path.join(DATA_DIR, csv_name)
        if os.path.exists(csv_path):
            universe_codes[ticker] = (csv_path, name, sector)

    print(f"Found {len(universe_codes)} stocks with local data out of {len(CN_UNIVERSE)} universe")

    # Walk-forward simulation
    LOOKBACK = 30  # bars needed for scoring
    HOLD_DAYS = 1  # first-day analysis
    MIN_SCORE = 6  # buy threshold

    # Test multiple filter parameter combinations
    param_combos = [
        {"ma_short": 5, "ma_long": 20, "label": "MA5/20 (default)"},
        {"ma_short": 3, "ma_long": 10, "label": "MA3/10 (aggressive)"},
        {"ma_short": 5, "ma_long": 10, "label": "MA5/10 (tight)"},
        {"ma_short": 10, "ma_long": 30, "label": "MA10/30 (smooth)"},
    ]

    results = {}  # label → {with_filter, without_filter stats}

    # No-filter baseline: walk through each trading day
    print("\n=== Running walk-forward simulation ===")

    # Collect all trades without filter
    no_filter_trades = []
    filter_trades = {combo["label"]: [] for combo in param_combos}

    # For each evaluation day
    for day_idx in range(LOOKBACK + 5, len(index_dates) - HOLD_DAYS):
        eval_date = index_dates[day_idx]

        # Evaluate market filter for this day (using index data up to this day)
        idx_up_to = index_close[:day_idx + 1]

        # Score each stock
        for ticker, (csv_path, name, sector) in universe_codes.items():
            stock_data = load_csv(csv_path)
            if not stock_data:
                continue

            # Find this date in stock data
            try:
                stock_day_idx = stock_data['dates'].index(eval_date)
            except ValueError:
                continue  # stock not traded on this date

            if stock_day_idx < LOOKBACK or stock_day_idx >= len(stock_data['close']) - HOLD_DAYS:
                continue

            # Compute score using data up to eval_date
            close_slice = stock_data['close'][:stock_day_idx + 1]
            volume_slice = stock_data['volume'][:stock_day_idx + 1]
            open_slice = stock_data['open'][:stock_day_idx + 1]
            high_slice = stock_data['high'][:stock_day_idx + 1]
            low_slice = stock_data['low'][:stock_day_idx + 1]

            result = compute_score_v3(close_slice, volume_slice, open_slice, high_slice, low_slice)
            score = result['score']

            if score >= MIN_SCORE:
                # Trade: buy at close, sell next day close
                entry_price = stock_data['close'][stock_day_idx]
                exit_price = stock_data['close'][stock_day_idx + HOLD_DAYS]
                if entry_price <= 0:
                    continue
                first_day_return = (exit_price / entry_price - 1) * 100
                is_loss = first_day_return < 0

                trade = {
                    'ticker': ticker,
                    'name': name,
                    'date': eval_date,
                    'score': score,
                    'entry': entry_price,
                    'exit': exit_price,
                    'return': first_day_return,
                    'is_loss': is_loss,
                }
                no_filter_trades.append(trade)

                # Check each filter combo
                for combo in param_combos:
                    mf = MarketFilter(
                        idx_up_to,
                        ma_short=combo["ma_short"],
                        ma_long=combo["ma_long"],
                    )
                    if mf.is_favorable():
                        filter_trades[combo["label"]].append(trade)

        if day_idx % 50 == 0:
            print(f"  Day {day_idx}/{len(index_dates)}: {len(no_filter_trades)} trades so far")

    # ── Compute statistics ───────────────────────────────────────
    def calc_stats(trades):
        if not trades:
            return {"count": 0, "loss_rate": 0, "avg_return": 0, "total_return": 0, "win_rate": 0}
        returns = [t['return'] for t in trades]
        losses = sum(1 for t in trades if t['is_loss'])
        wins = sum(1 for t in trades if not t['is_loss'])
        return {
            "count": len(trades),
            "loss_rate": losses / len(trades) * 100,
            "avg_return": sum(returns) / len(returns),
            "total_return": sum(returns),
            "win_rate": wins / len(trades) * 100,
            "best": max(returns) if returns else 0,
            "worst": min(returns) if returns else 0,
        }

    baseline = calc_stats(no_filter_trades)
    print(f"\n=== Baseline (no filter) ===")
    print(f"  Total trades: {baseline['count']}")
    print(f"  First-day loss rate: {baseline['loss_rate']:.1f}%")
    print(f"  Avg first-day return: {baseline['avg_return']:.3f}%")
    print(f"  Win rate: {baseline['win_rate']:.1f}%")

    combo_stats = {}
    best_combo = None
    best_improvement = -999

    for combo in param_combos:
        label = combo["label"]
        stats = calc_stats(filter_trades[label])
        combo_stats[label] = stats
        improvement = baseline['loss_rate'] - stats['loss_rate']
        if improvement > best_improvement and stats['count'] > 0:
            best_improvement = improvement
            best_combo = label

        print(f"\n=== {label} ===")
        print(f"  Trades passed: {stats['count']} / {baseline['count']} ({stats['count']/max(baseline['count'],1)*100:.0f}%)")
        print(f"  First-day loss rate: {stats['loss_rate']:.1f}% (Δ {baseline['loss_rate'] - stats['loss_rate']:+.1f}pp)")
        print(f"  Avg first-day return: {stats['avg_return']:.3f}%")
        print(f"  Win rate: {stats['win_rate']:.1f}%")

    # ── Generate Report ──────────────────────────────────────────
    os.makedirs(DOCS_DIR, exist_ok=True)
    report_path = os.path.join(DOCS_DIR, "market-filter-report.md")

    report = []
    report.append("# Market Filter Validation Report\n")
    report.append(f"**Generated:** {index_dates[-1] if index_dates else 'N/A'}\n")
    report.append(f"**Index:** sh.000001 (上证指数)")
    report.append(f"**Period:** {index_dates[0]} to {index_dates[-1]}")
    report.append(f"**Scanner:** cn_scanner v3 (score >= {MIN_SCORE})")
    report.append(f"**Hold:** {HOLD_DAYS} day (first-day analysis)\n")

    report.append("## Baseline (No Filter)\n")
    report.append(f"| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| Total Trades | {baseline['count']} |")
    report.append(f"| First-Day Loss Rate | {baseline['loss_rate']:.1f}% |")
    report.append(f"| Avg First-Day Return | {baseline['avg_return']:.3f}% |")
    report.append(f"| Win Rate | {baseline['win_rate']:.1f}% |")
    report.append(f"| Best Trade | {baseline.get('best', 0):+.2f}% |")
    report.append(f"| Worst Trade | {baseline.get('worst', 0):+.2f}% |\n")

    report.append("## Filter Comparison\n")
    report.append("| Filter Config | Trades | Loss Rate | Δ Loss Rate | Avg Return | Win Rate |")
    report.append("|--------------|--------|-----------|-------------|------------|----------|")
    report.append(f"| No Filter (baseline) | {baseline['count']} | {baseline['loss_rate']:.1f}% | — | {baseline['avg_return']:.3f}% | {baseline['win_rate']:.1f}% |")
    for combo in param_combos:
        label = combo["label"]
        s = combo_stats[label]
        delta = baseline['loss_rate'] - s['loss_rate']
        marker = " ⭐" if label == best_combo else ""
        report.append(f"| {label}{marker} | {s['count']} | {s['loss_rate']:.1f}% | {delta:+.1f}pp | {s['avg_return']:.3f}% | {s['win_rate']:.1f}% |")

    if best_combo:
        report.append(f"\n## Best Filter: {best_combo}\n")
        report.append(f"- Loss rate improvement: **{best_improvement:+.1f}pp**")
        report.append(f"- Trades filtered out: {baseline['count'] - combo_stats[best_combo]['count']} ({(1 - combo_stats[best_combo]['count']/max(baseline['count'],1))*100:.0f}%)")
        report.append(f"- This means the filter blocked approximately {(1 - combo_stats[best_combo]['count']/max(baseline['count'],1))*100:.0f}% of trades")
        report.append(f"  while reducing first-day losses by {best_improvement:.1f} percentage points.")

    report.append("\n## Methodology\n")
    report.append("1. Walk-forward simulation over the full data period")
    report.append("2. Each day, run cn_scanner v3 scoring on all stocks with local data")
    report.append("3. When score >= 6 (BUY signal), record entry at close, exit next day close")
    report.append("4. MarketFilter checks index (sh.000001) conditions on the entry day")
    report.append("5. Compare loss rates with and without the market filter")
    report.append("\n## Conclusion\n")
    if best_combo and best_improvement > 0:
        report.append(f"The market filter ({best_combo}) reduces first-day loss rate by {best_improvement:.1f}pp, ")
        report.append(f"from {baseline['loss_rate']:.1f}% to {combo_stats[best_combo]['loss_rate']:.1f}%.")
        report.append("This confirms the hypothesis that checking the broad market environment before buying improves outcomes.")
    else:
        report.append("The market filter did not show significant improvement in this dataset.")
        report.append("Consider adjusting parameters or using a different index/signal combination.")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report) + '\n')
    print(f"\n✅ Report saved to {report_path}")


if __name__ == "__main__":
    run_validation()
