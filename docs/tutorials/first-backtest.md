# Write Your First Backtest

This tutorial walks you through backtesting a momentum strategy on real market data.

## Prerequisites

```bash
pip install finclaw-ai
```

## Step 1: Fetch Price Data

```python
from src.data.prices import PriceLoader
import numpy as np

loader = PriceLoader()
df = loader.fetch("AAPL", period="5y")

prices = np.array(df["Close"].values, dtype=np.float64)
print(f"Loaded {len(prices)} data points")
```

## Step 2: Generate Signals

Use technical indicators to create buy/sell signals:

```python
from src.ta import rsi, macd, sma

# Calculate indicators
rsi_values = rsi(prices, period=14)
macd_line, signal_line, histogram = macd(prices)
sma_50 = sma(prices, 50)
sma_200 = sma(prices, 200)

# Simple signal: buy when RSI < 30 and price above SMA200
signals = []
for i in range(len(prices)):
    if rsi_values[i] < 30 and prices[i] > sma_200[i]:
        signals.append("buy")
    elif rsi_values[i] > 70:
        signals.append("sell")
    else:
        signals.append("hold")
```

## Step 3: Run the Backtest

### Quick Way — CLI

```bash
finclaw backtest --tickers AAPL --strategy momentum --start 2020-01-01 --end 2025-01-01
```

### Programmatic Way — RealisticBacktester

```python
from src.backtesting import RealisticBacktester, BacktestConfig, SlippageModel, CommissionModel

config = BacktestConfig(
    initial_capital=100000,
    slippage_model=SlippageModel(bps=5),
    commission_model=CommissionModel(rate=0.001),
)

bt = RealisticBacktester(config)
result = bt.run(signals=signals, prices=prices)

print(f"Total Return:  {result.total_return:.2%}")
print(f"Sharpe Ratio:  {result.sharpe_ratio:.2f}")
print(f"Max Drawdown:  {result.max_drawdown:.2%}")
print(f"Win Rate:      {result.win_rate:.2%}")
```

## Step 4: Compare Against Benchmarks

```python
from src.backtesting import run_all_benchmarks, StrategyComparator

benchmarks = run_all_benchmarks(prices, tickers=["AAPL"])

comp = StrategyComparator()
comp.add("My Strategy", result)
for name, bm_result in benchmarks.items():
    comp.add(name, bm_result)

comparison = comp.compare()
print(comparison)
```

## Step 5: Walk-Forward Validation

Ensure your strategy isn't overfit:

```python
from src.backtesting import WalkForwardOptimizer

wfo = WalkForwardOptimizer(
    train_window=252,   # 1 year train
    test_window=63,     # 3 months test
    step_size=21,       # Monthly roll
    metric="sharpe",
)
wf_result = wfo.optimize(strategy_class=MomentumJTStrategy,
                          param_grid={"formation_period": [6, 9, 12]},
                          data=prices)
print(f"Walk-forward Sharpe: {wf_result.avg_test_sharpe:.2f}")
```

## Step 6: Generate a Report

```python
from src.reports.html_report import HTMLReportGenerator

report = HTMLReportGenerator()
report.generate(result, output="backtest_report.html")
# Opens an interactive HTML report with equity curves, drawdown charts, etc.
```

## Event-Driven Backtester (Advanced)

For more realistic simulation with event-by-event processing:

```python
from src.backtesting import EventDrivenBacktester

bt = EventDrivenBacktester(
    initial_capital=100000,
    commission_rate=0.001,
    slippage_bps=5,
)
result = bt.run(strategy=my_strategy, data=ohlcv_data)
```

## Next Steps

- [Create a Custom Strategy](custom-strategy.md)
- [Risk Management Guide](risk-management.md)
- [Full API Reference](../api-reference.md)
