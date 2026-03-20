"""
Ensemble Backtest - Compare Single vs Multi-Strategy
=====================================================
Three plans:
  A) Best single strategy (cn_scanner v3 score >= 6)
  B) 5-strategy vote, >= 3 votes (strict consensus)
  C) 5-strategy vote, >= 2 votes (loose consensus)

Rules:
  - T+1 buy (next day open price)
  - Can't buy if limit-up (open >= prev_close * 1.095)
  - Can't sell if limit-down (open <= prev_close * 0.905)
  - 2-day hold (sell on 3rd day open)
  - Stop loss 3%, take profit 20%
  - Commission 0.1%
  - Capital: 1,000,000 CNY
  - Max 2 positions at a time

Usage:
    python scripts/ensemble_backtest.py [--stocks 100] [--period 2024-01-01:2025-12-31]
"""

import sys
import os
import glob
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.strategies.ensemble import StrategyEnsemble


# ─── CSV loader ──────────────────────────────────────────────

def load_csv_data(csv_path: str) -> dict:
    """Load a single CSV file into arrays.
    
    CSV columns: date,code,open,high,low,close,volume,amount,turn
    
    Returns dict with dates, opens, highs, lows, closes, volumes, code, name.
    """
    dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
    code = ""
    
    with open(csv_path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 7:
                continue
            # Skip rows with empty/invalid volume (suspended days)
            vol_str = parts[6].strip()
            if not vol_str:
                continue
            try:
                vol = float(vol_str)
            except ValueError:
                continue
            dates.append(parts[0])
            code = parts[1]
            opens.append(float(parts[2]))
            highs.append(float(parts[3]))
            lows.append(float(parts[4]))
            closes.append(float(parts[5]))
            volumes.append(vol)
    
    if not dates:
        return None
    
    return {
        "dates": np.array(dates),
        "opens": np.array(opens, dtype=np.float64),
        "highs": np.array(highs, dtype=np.float64),
        "lows": np.array(lows, dtype=np.float64),
        "closes": np.array(closes, dtype=np.float64),
        "volumes": np.array(volumes, dtype=np.float64),
        "code": code,
        "name": code,  # We don't have names in CSV, use code
    }


def load_all_stocks(data_dir: str, max_stocks: int = 0) -> dict:
    """Load all CSV files from data directory.
    
    Returns {code: data_dict}.
    """
    pattern = os.path.join(data_dir, "*.csv")
    csv_files = sorted(glob.glob(pattern))
    
    if max_stocks > 0:
        csv_files = csv_files[:max_stocks]
    
    all_data = {}
    for csv_path in csv_files:
        data = load_csv_data(csv_path)
        if data is None or len(data["closes"]) < 60:
            continue
        code = data["code"]
        all_data[code] = data
    
    return all_data


# ─── Backtest engine ─────────────────────────────────────────

class BacktestEngine:
    """Realistic A-share backtest with T+1, limit up/down, commission."""
    
    def __init__(
        self,
        capital: float = 1_000_000,
        max_positions: int = 2,
        hold_days: int = 2,
        stop_loss: float = 0.03,
        take_profit: float = 0.20,
        commission: float = 0.001,
    ):
        self.initial_capital = capital
        self.max_positions = max_positions
        self.hold_days = hold_days
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.commission = commission
    
    def is_limit_up(self, open_price: float, prev_close: float) -> bool:
        """Can't buy if opening at limit-up."""
        if prev_close <= 0:
            return False
        return open_price / prev_close >= 1.095
    
    def is_limit_down(self, open_price: float, prev_close: float) -> bool:
        """Can't sell if opening at limit-down."""
        if prev_close <= 0:
            return False
        return open_price / prev_close <= 0.905
    
    def run_backtest(
        self,
        all_data: dict,
        signal_generator,
        plan_name: str = "Plan",
    ) -> dict:
        """Run backtest over all stocks.
        
        Args:
            all_data: {code: data_dict}
            signal_generator: callable(ensemble, data_dict, day_idx) -> bool
                Returns True if this stock should be bought on day_idx.
            plan_name: name for reporting
        
        Returns:
            Backtest result dict.
        """
        # Build a day-by-day timeline across all stocks
        # Collect all unique dates
        all_dates = set()
        for code, data in all_data.items():
            for d in data["dates"]:
                all_dates.add(d)
        
        sorted_dates = sorted(all_dates)
        if len(sorted_dates) < 60:
            return self._empty_result(plan_name)
        
        # Build date→index mapping for each stock
        stock_date_idx = {}
        for code, data in all_data.items():
            date_to_idx = {d: i for i, d in enumerate(data["dates"])}
            stock_date_idx[code] = date_to_idx
        
        # Simulation state
        cash = self.initial_capital
        positions = []  # list of {code, entry_price, entry_date, entry_day_idx, shares}
        trades = []     # completed trades
        equity_curve = []
        
        ensemble = StrategyEnsemble()
        
        # Start from day 60 (need lookback)
        start_day = 60
        
        for day_i, date in enumerate(sorted_dates):
            if day_i < start_day:
                equity_curve.append(self.initial_capital)
                continue
            
            # 1. Check exits for existing positions
            positions_to_remove = []
            for pos_i, pos in enumerate(positions):
                code = pos["code"]
                if code not in stock_date_idx or date not in stock_date_idx[code]:
                    continue
                
                idx = stock_date_idx[code][date]
                data = all_data[code]
                
                days_held = day_i - pos["entry_day_idx"]
                
                should_exit = False
                exit_reason = ""
                
                # Check stop loss / take profit using close
                current_price = data["closes"][idx]
                ret = (current_price - pos["entry_price"]) / pos["entry_price"]
                
                if ret <= -self.stop_loss:
                    should_exit = True
                    exit_reason = "stop_loss"
                elif ret >= self.take_profit:
                    should_exit = True
                    exit_reason = "take_profit"
                elif days_held >= self.hold_days:
                    should_exit = True
                    exit_reason = "time_exit"
                
                if should_exit:
                    # Try to sell at today's open (T+1 rule: we signal yesterday)
                    sell_price = data["opens"][idx]
                    prev_close = data["closes"][idx - 1] if idx > 0 else sell_price
                    
                    # Check limit-down: can't sell
                    if self.is_limit_down(sell_price, prev_close):
                        continue  # Can't sell, wait
                    
                    proceeds = pos["shares"] * sell_price * (1 - self.commission)
                    cash += proceeds
                    
                    trade_ret = (sell_price / pos["entry_price"] - 1) * 100
                    trades.append({
                        "code": code,
                        "entry_date": pos["entry_date"],
                        "exit_date": date,
                        "entry_price": pos["entry_price"],
                        "exit_price": sell_price,
                        "return_pct": trade_ret,
                        "hold_days": days_held,
                        "exit_reason": exit_reason,
                    })
                    positions_to_remove.append(pos_i)
            
            # Remove closed positions (reverse order to preserve indices)
            for idx in sorted(positions_to_remove, reverse=True):
                positions.pop(idx)
            
            # 2. Check entries (only if we have capacity)
            if len(positions) < self.max_positions:
                # Scan all stocks for signals
                candidates = []
                for code, data in all_data.items():
                    if code in [p["code"] for p in positions]:
                        continue  # Already holding
                    
                    if date not in stock_date_idx.get(code, {}):
                        continue
                    
                    idx = stock_date_idx[code][date]
                    if idx < 60 or idx >= len(data["closes"]) - 1:
                        continue
                    
                    # Generate signal using data up to today
                    has_signal = signal_generator(
                        ensemble, data, idx
                    )
                    
                    if has_signal:
                        # Buy at tomorrow's open (T+1)
                        buy_idx = idx + 1
                        if buy_idx >= len(data["opens"]):
                            continue
                        
                        buy_price = data["opens"][buy_idx]
                        prev_close = data["closes"][idx]
                        
                        # Can't buy if limit-up
                        if self.is_limit_up(buy_price, prev_close):
                            continue
                        
                        candidates.append({
                            "code": code,
                            "buy_price": buy_price,
                            "buy_date": data["dates"][buy_idx] if buy_idx < len(data["dates"]) else date,
                            "buy_day_idx": day_i + 1,
                        })
                
                # Take top candidates (by signal order)
                slots = self.max_positions - len(positions)
                for cand in candidates[:slots]:
                    per_position = cash / (slots - len([c for c in candidates[:slots] if c == cand]) + 1)
                    invest = min(per_position, cash) * 0.95  # Keep 5% cash buffer
                    if invest < 1000 or cand["buy_price"] <= 0:
                        continue
                    
                    shares = int(invest / cand["buy_price"] / 100) * 100  # Round to 100 shares
                    if shares <= 0:
                        continue
                    
                    cost = shares * cand["buy_price"] * (1 + self.commission)
                    if cost > cash:
                        continue
                    
                    cash -= cost
                    positions.append({
                        "code": cand["code"],
                        "entry_price": cand["buy_price"],
                        "entry_date": cand["buy_date"],
                        "entry_day_idx": cand["buy_day_idx"],
                        "shares": shares,
                    })
            
            # 3. Calculate equity
            portfolio_value = cash
            for pos in positions:
                code = pos["code"]
                if code in stock_date_idx and date in stock_date_idx[code]:
                    idx = stock_date_idx[code][date]
                    portfolio_value += pos["shares"] * all_data[code]["closes"][idx]
                else:
                    portfolio_value += pos["shares"] * pos["entry_price"]
            
            equity_curve.append(portfolio_value)
        
        # Close remaining positions at last available price
        for pos in positions:
            code = pos["code"]
            data = all_data[code]
            sell_price = data["closes"][-1]
            proceeds = pos["shares"] * sell_price * (1 - self.commission)
            cash += proceeds
            trade_ret = (sell_price / pos["entry_price"] - 1) * 100
            trades.append({
                "code": code,
                "entry_date": pos["entry_date"],
                "exit_date": "end",
                "entry_price": pos["entry_price"],
                "exit_price": sell_price,
                "return_pct": trade_ret,
                "hold_days": 0,
                "exit_reason": "end_of_data",
            })
        
        return self._compute_stats(plan_name, trades, equity_curve)
    
    def _compute_stats(self, plan_name: str, trades: list, equity_curve: list) -> dict:
        """Compute backtest statistics."""
        if not trades:
            return self._empty_result(plan_name)
        
        eq = np.array(equity_curve, dtype=np.float64)
        returns = [t["return_pct"] for t in trades]
        winning = [r for r in returns if r > 0]
        
        # Total return
        final_eq = eq[-1] if len(eq) > 0 else self.initial_capital
        total_return = (final_eq / self.initial_capital - 1) * 100
        
        # Annualised return
        trading_days = len(equity_curve)
        years = trading_days / 252.0
        if years > 0 and final_eq > 0:
            ann_return = ((final_eq / self.initial_capital) ** (1.0 / years) - 1) * 100
        else:
            ann_return = 0.0
        
        # Max drawdown
        peak = np.maximum.accumulate(eq)
        dd = np.where(peak > 0, (eq - peak) / peak, 0.0)
        max_dd = abs(float(np.min(dd))) * 100
        
        # Win rate
        win_rate = len(winning) / len(trades) * 100 if trades else 0.0
        
        # Sharpe ratio (daily returns → annualised)
        if len(eq) > 1:
            daily_rets = np.diff(eq) / eq[:-1]
            daily_rets = daily_rets[np.isfinite(daily_rets)]
            if len(daily_rets) > 1 and np.std(daily_rets) > 0:
                sharpe = np.mean(daily_rets) / np.std(daily_rets) * np.sqrt(252)
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0
        
        return {
            "plan": plan_name,
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "win_rate": round(win_rate, 1),
            "total_return": round(total_return, 1),
            "annualized_return": round(ann_return, 1),
            "max_drawdown": round(max_dd, 1),
            "sharpe": round(sharpe, 2),
            "avg_return": round(float(np.mean(returns)), 2) if returns else 0.0,
            "trades": trades,
        }
    
    def _empty_result(self, plan_name: str) -> dict:
        return {
            "plan": plan_name,
            "total_trades": 0,
            "winning_trades": 0,
            "win_rate": 0.0,
            "total_return": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "avg_return": 0.0,
            "trades": [],
        }


# ─── Signal generators ───────────────────────────────────────

def signal_single_strategy(ensemble: StrategyEnsemble, data: dict, idx: int) -> bool:
    """Plan A: Single best strategy (cn_scanner v3 score >= 6)."""
    closes = data["closes"][:idx + 1]
    volumes = data["volumes"][:idx + 1]
    opens = data["opens"][:idx + 1]
    highs = data["highs"][:idx + 1]
    lows = data["lows"][:idx + 1]
    
    score = ensemble.score_cn_scanner(closes, volumes, opens, highs, lows)
    return score >= 6.0


def signal_strict_consensus(ensemble: StrategyEnsemble, data: dict, idx: int) -> bool:
    """Plan B: 5-strategy vote, >= 3 votes to buy."""
    closes = data["closes"][:idx + 1]
    volumes = data["volumes"][:idx + 1]
    opens = data["opens"][:idx + 1]
    highs = data["highs"][:idx + 1]
    lows = data["lows"][:idx + 1]
    dates = data["dates"][:idx + 1]
    
    sig = ensemble.evaluate_stock(dates, opens, highs, lows, closes, volumes)
    return sig.votes >= 3


def signal_loose_consensus(ensemble: StrategyEnsemble, data: dict, idx: int) -> bool:
    """Plan C: 5-strategy vote, >= 2 votes to buy."""
    closes = data["closes"][:idx + 1]
    volumes = data["volumes"][:idx + 1]
    opens = data["opens"][:idx + 1]
    highs = data["highs"][:idx + 1]
    lows = data["lows"][:idx + 1]
    dates = data["dates"][:idx + 1]
    
    sig = ensemble.evaluate_stock(dates, opens, highs, lows, closes, volumes)
    return sig.votes >= 2


# ─── Output formatting ───────────────────────────────────────

def format_comparison(results: list) -> str:
    """Format comparison table."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  SINGLE vs ENSEMBLE BACKTEST COMPARISON")
    lines.append("=" * 70)
    lines.append("")
    
    # Header
    header = f"  {'Metric':<16}"
    for r in results:
        header += f" {r['plan']:<18}"
    lines.append(header)
    lines.append("  " + "-" * (16 + 18 * len(results)))
    
    # Rows
    metrics = [
        ("年化", "annualized_return", "%"),
        ("总收益", "total_return", "%"),
        ("回撤", "max_drawdown", "%"),
        ("胜率", "win_rate", "%"),
        ("交易数", "total_trades", ""),
        ("Sharpe", "sharpe", ""),
        ("平均收益", "avg_return", "%"),
    ]
    
    for label, key, suffix in metrics:
        row = f"  {label:<16}"
        for r in results:
            val = r[key]
            if suffix:
                row += f" {val:>14.1f}{suffix}  "
            else:
                row += f" {val:>15}   "
        lines.append(row)
    
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ensemble Backtest Comparison")
    parser.add_argument("--stocks", type=int, default=200,
                        help="Max stocks to test (0=all)")
    parser.add_argument("--data-dir", type=str,
                        default=str(Path(__file__).resolve().parent.parent / "data" / "a_shares"),
                        help="Directory with CSV data files")
    args = parser.parse_args()
    
    print(f"\n📊 Loading stock data from {args.data_dir}...")
    all_data = load_all_stocks(args.data_dir, max_stocks=args.stocks)
    print(f"  Loaded {len(all_data)} stocks")
    
    if not all_data:
        print("❌ No data found!")
        return
    
    engine = BacktestEngine(
        capital=1_000_000,
        max_positions=2,
        hold_days=2,
        stop_loss=0.03,
        take_profit=0.20,
        commission=0.001,
    )
    
    # Plan A: Single strategy
    print("\n🔄 Running Plan A (single strategy: cn_scanner v3)...")
    result_a = engine.run_backtest(all_data, signal_single_strategy, "方案A(单策略)")
    print(f"  Trades: {result_a['total_trades']}, Return: {result_a['total_return']:.1f}%")
    
    # Plan B: Strict consensus (>= 3 votes)
    print("\n🔄 Running Plan B (strict consensus: ≥3 votes)...")
    result_b = engine.run_backtest(all_data, signal_strict_consensus, "方案B(≥3票)")
    print(f"  Trades: {result_b['total_trades']}, Return: {result_b['total_return']:.1f}%")
    
    # Plan C: Loose consensus (>= 2 votes)
    print("\n🔄 Running Plan C (loose consensus: ≥2 votes)...")
    result_c = engine.run_backtest(all_data, signal_loose_consensus, "方案C(≥2票)")
    print(f"  Trades: {result_c['total_trades']}, Return: {result_c['total_return']:.1f}%")
    
    # Print comparison
    print(format_comparison([result_a, result_b, result_c]))
    
    # Analysis
    print("\n📝 Analysis:")
    best = max([result_a, result_b, result_c], key=lambda r: r["sharpe"])
    print(f"  Best Sharpe ratio: {best['plan']} ({best['sharpe']:.2f})")
    
    safest = min([result_a, result_b, result_c], key=lambda r: r["max_drawdown"])
    print(f"  Lowest drawdown: {safest['plan']} ({safest['max_drawdown']:.1f}%)")
    
    most_trades = max([result_a, result_b, result_c], key=lambda r: r["total_trades"])
    print(f"  Most active: {most_trades['plan']} ({most_trades['total_trades']} trades)")


if __name__ == "__main__":
    main()
