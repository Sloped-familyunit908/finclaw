# Quickstart: Get Running in 5 Minutes

## Install

```bash
pip install finclaw-ai
```

Or from source:

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[all]"
```

## Your First Analysis

```bash
# Check a stock price
finclaw price --ticker AAPL

# Analyze a ticker with TA indicators
finclaw analyze --ticker AAPL
```

## Run a Quick Backtest

```bash
finclaw backtest --tickers AAPL --strategy momentum --start 2022-01-01
```

This runs a momentum strategy on Apple stock from 2022 and prints returns, Sharpe ratio, and max drawdown.

## Screen for Opportunities

```bash
finclaw screen --criteria "rsi<30"
```

Finds oversold stocks across the default universe.

## Interactive Mode

```bash
finclaw interactive
```

Opens an interactive REPL where you can run commands, explore strategies, and analyze markets conversationally.

## Generate an HTML Report

```bash
finclaw report --ticker AAPL --format html
```

Creates a rich HTML backtest report with charts and metrics.

## Configuration

Create `finclaw.yml` in your project root:

```yaml
data:
  provider: yfinance
  cache_ttl_hours: 24

backtest:
  initial_capital: 100000
  commission: 0.001
  benchmark: SPY
```

## Python API

```python
from src.ta import rsi, macd, bollinger_bands
from src.strategies import MomentumJTStrategy
from src.backtesting import RealisticBacktester, BacktestConfig
import numpy as np

# Calculate RSI
prices = np.array([...])  # your price data
rsi_values = rsi(prices, period=14)

# Run a strategy
strategy = MomentumJTStrategy(formation_period=12, holding_period=3)
```

## Next Steps

- [Write Your First Backtest](first-backtest.md)
- [Create a Custom Strategy](custom-strategy.md)
- [Risk Management Guide](risk-management.md)
- [Full API Reference](../api-reference.md)
