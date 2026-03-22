"""
AutoTrading Evaluation Script — DO NOT MODIFY
Runs strategy.py against historical data and reports fitness metrics.

Usage: python evaluate.py
"""
import sys
import os
import time
import json
import importlib

# Add parent directory to path for finclaw imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import numpy as np

def load_stock_data(data_dir: str = "../data/a_shares", max_stocks: int = 200):
    """Load OHLCV data from CSV files."""
    data = {}
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"ERROR: Data directory {data_dir} not found")
        print("Run: python scripts/download_a_shares.py")
        sys.exit(1)
    
    csv_files = sorted(data_path.glob("*.csv"))[:max_stocks]
    for f in csv_files:
        code = f.stem
        try:
            lines = f.read_text(encoding='utf-8').strip().split('\n')
            if len(lines) < 62:  # Need at least 60 days + header
                continue
            header = [h.strip().lower() for h in lines[0].split(',')]
            # Detect column indices from header
            col_map = {name: idx for idx, name in enumerate(header)}
            date_idx = col_map.get('date', 0)
            open_idx = col_map.get('open', 1)
            high_idx = col_map.get('high', 2)
            low_idx = col_map.get('low', 3)
            close_idx = col_map.get('close', 4)
            volume_idx = col_map.get('volume', 5)
            records = []
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) > max(date_idx, open_idx, high_idx, low_idx, close_idx, volume_idx):
                    try:
                        records.append({
                            'date': parts[date_idx],
                            'open': float(parts[open_idx]),
                            'high': float(parts[high_idx]),
                            'low': float(parts[low_idx]),
                            'close': float(parts[close_idx]),
                            'volume': float(parts[volume_idx]) if float(parts[volume_idx]) > 0 else 1.0,
                        })
                    except (ValueError, IndexError):
                        continue
            if len(records) >= 60:
                data[code] = records
        except Exception:
            continue
    return data


def run_backtest(strategy_module, stock_data: dict) -> dict:
    """Run the strategy across all stocks and compute metrics."""
    all_trades = []
    
    for code, records in stock_data.items():
        closes = [r['close'] for r in records]
        volumes = [r['volume'] for r in records]
        highs = [r['high'] for r in records]
        lows = [r['low'] for r in records]
        opens = [r['open'] for r in records]
        dates = [r['date'] for r in records]
        
        # Call strategy's generate_signals function
        try:
            signals = strategy_module.generate_signals(
                code=code,
                closes=closes,
                volumes=volumes,
                highs=highs,
                lows=lows,
                opens=opens,
                dates=dates,
            )
        except Exception as e:
            continue
        
        # signals should be a list of {'action': 'buy'|'sell', 'index': int, 'price': float}
        if not signals:
            continue
        
        # Simulate trades
        position = None
        for sig in signals:
            if sig['action'] == 'buy' and position is None:
                position = {'buy_price': sig['price'], 'buy_idx': sig['index']}
            elif sig['action'] == 'sell' and position is not None:
                pnl = (sig['price'] - position['buy_price']) / position['buy_price']
                all_trades.append(pnl)
                position = None
    
    if len(all_trades) < 20:
        return {
            'fitness': 0.0,
            'annual_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe': 0.0,
            'win_rate': 0.0,
            'trades': len(all_trades),
            'status': 'insufficient_trades',
        }
    
    # Compute metrics
    trade_returns = np.array(all_trades)
    win_rate = np.sum(trade_returns > 0) / len(trade_returns) * 100
    avg_return = np.mean(trade_returns)
    std_return = np.std(trade_returns) if np.std(trade_returns) > 0 else 0.001
    
    # Approximate annualization (assume ~250 trading days, ~5 trades per stock per year)
    annual_return = avg_return * len(all_trades) * 100
    sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
    
    # Compute max drawdown from cumulative returns
    cumulative = np.cumprod(1 + trade_returns)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak
    max_drawdown = abs(np.min(drawdown)) * 100
    if max_drawdown < 0.01:
        max_drawdown = 0.01
    
    # Fitness = annual_return * sharpe / max_drawdown (higher is better)
    fitness = 0.0
    if max_drawdown > 0:
        fitness = abs(annual_return) * max(sharpe, 0) / max_drawdown
        if annual_return < 0:
            fitness = -fitness
    
    return {
        'fitness': round(fitness, 4),
        'annual_return': round(annual_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sharpe': round(sharpe, 2),
        'win_rate': round(win_rate, 1),
        'trades': len(all_trades),
        'status': 'ok',
    }


if __name__ == "__main__":
    start = time.time()
    
    # Load data
    print("Loading data...")
    stock_data = load_stock_data()
    print(f"Loaded {len(stock_data)} stocks")
    
    # Import strategy
    import strategy
    importlib.reload(strategy)
    
    # Run backtest
    print("Running backtest...")
    results = run_backtest(strategy, stock_data)
    
    elapsed = time.time() - start
    
    # Print results in grep-friendly format
    print("---")
    for k, v in results.items():
        print(f"{k}: {v}")
    print(f"elapsed_seconds: {elapsed:.1f}")
