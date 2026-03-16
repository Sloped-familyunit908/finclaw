# Create a Custom Strategy

Build your own strategy and plug it into FinClaw's backtesting engine.

## Strategy Interface

Every strategy must implement a `generate_signal(prices) → str` method returning `"buy"`, `"sell"`, or `"hold"`.

## Example: Golden Cross Strategy

```python
"""Golden Cross: buy when SMA50 crosses above SMA200."""

import numpy as np
from src.ta import sma


class GoldenCrossStrategy:
    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prev_signal = "hold"

    def generate_signals(self, prices: np.ndarray) -> list[str]:
        """Generate signals for entire price series."""
        fast = sma(prices, self.fast_period)
        slow = sma(prices, self.slow_period)

        signals = []
        for i in range(len(prices)):
            if np.isnan(fast[i]) or np.isnan(slow[i]):
                signals.append("hold")
            elif fast[i] > slow[i] and (i == 0 or fast[i-1] <= slow[i-1]):
                signals.append("buy")
            elif fast[i] < slow[i] and (i == 0 or fast[i-1] >= slow[i-1]):
                signals.append("sell")
            else:
                signals.append("hold")
        return signals
```

## Add Risk Management

```python
from src.risk import StopLossManager, StopLossType, KellyCriterion

class GoldenCrossWithRisk(GoldenCrossStrategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_loss = StopLossManager(
            stop_type=StopLossType.TRAILING,
            percentage=0.05,
        )
        self.kelly = KellyCriterion(win_rate=0.55, avg_win=0.03, avg_loss=0.02)

    def position_size(self, capital: float) -> float:
        return self.kelly.position_size(capital)
```

## Backtest Your Strategy

```python
from src.backtesting import RealisticBacktester, BacktestConfig
from src.data.prices import PriceLoader

loader = PriceLoader()
df = loader.fetch("MSFT", period="5y")
prices = df["Close"].values

strategy = GoldenCrossWithRisk(fast_period=50, slow_period=200)
signals = strategy.generate_signals(prices)

config = BacktestConfig(initial_capital=100000)
bt = RealisticBacktester(config)
result = bt.run(signals=signals, prices=prices)

print(f"Return: {result.total_return:.2%}")
print(f"Sharpe: {result.sharpe_ratio:.2f}")
```

## Register as a Plugin

Create a plugin file `plugins/golden_cross.py`:

```python
def register(manager):
    """Register the Golden Cross strategy as a plugin."""
    manager.add_strategy("golden_cross", GoldenCrossStrategy)
```

Then load it:

```python
from src.plugins import PluginManager

pm = PluginManager()
pm.discover("plugins/")
```

## Multi-Strategy Combiner

Combine your strategy with built-in ones:

```python
from src.strategies import SignalCombiner

combiner = SignalCombiner(weights={
    "golden_cross": 0.4,
    "rsi_reversal": 0.3,
    "momentum": 0.3,
})
combined = combiner.combine(all_signals)
```

## Regime-Adaptive Strategy

Adjust behavior based on market regime:

```python
from src.strategies import RegimeAdaptive

adaptive = RegimeAdaptive(regime_lookback=252)
regime = adaptive.detect_regime(prices)

if regime == "bull":
    # More aggressive parameters
    strategy = GoldenCrossStrategy(fast_period=20, slow_period=50)
elif regime == "bear":
    # Tighter stops, smaller positions
    strategy = GoldenCrossWithRisk(fast_period=50, slow_period=200)
```

## Next Steps

- [Risk Management Guide](risk-management.md)
- [Full API Reference](../api-reference.md)
