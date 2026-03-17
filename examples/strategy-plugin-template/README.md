# finclaw-strategy-example

> 🦀 Example strategy plugin for [FinClaw](https://github.com/NeuZhou/finclaw) — create your own in 5 minutes!

## Golden Cross Strategy

Classic 50/200 SMA crossover. Buy on golden cross, sell on death cross.

## Install

```bash
pip install finclaw-strategy-example
# or install in development mode:
cd examples/strategy-plugin-template
pip install -e .
```

Once installed, FinClaw auto-discovers it:

```bash
finclaw plugins list
# golden_cross  v1.0.0  50/200 SMA Golden Cross / Death Cross strategy
```

## Create Your Own Strategy in 5 Minutes

### 1. Copy this template

```bash
finclaw init-strategy my_awesome_strategy
# or manually:
cp -r examples/strategy-plugin-template my-strategy
```

### 2. Edit `strategy.py`

```python
from src.plugin_system import StrategyPlugin
import pandas as pd

class MyStrategy(StrategyPlugin):
    name = "my_awesome"
    version = "1.0.0"
    description = "My strategy description"
    author = "Your Name"
    risk_level = "medium"      # low / medium / high
    markets = ["us_stock"]     # us_stock, crypto, forex, cn_stock

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        # data has: Open, High, Low, Close, Volume
        signals = pd.Series(0, index=data.index)
        # Your logic here: 1=buy, -1=sell, 0=hold
        return signals

    def get_parameters(self) -> dict:
        return {"param1": self.param1}
```

### 3. Update `pyproject.toml`

```toml
[project.entry-points."finclaw.strategies"]
my_awesome = "my_package.strategy:MyStrategy"
```

### 4. Install & test

```bash
pip install -e .
finclaw plugins list
finclaw backtest --strategy plugin:my_awesome --tickers AAPL
```

## Run the example

```bash
finclaw backtest --strategy plugin:golden_cross --tickers AAPL,MSFT
```
