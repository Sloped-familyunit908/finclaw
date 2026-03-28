# Strategy YAML Templates

Ready-to-use YAML strategy configurations following the FinClaw [Strategy Specification](../strategy_spec.py).

## Templates

| Template | Strategy | Description |
|----------|----------|-------------|
| `pairs_trading.yaml` | Pairs Trading (Z-Score) | Statistical arbitrage between two correlated assets |
| `breakout_volume.yaml` | Volume-Confirmed Breakout | Donchian channel breakout with volume filter |
| `vwap_reversion.yaml` | VWAP Mean Reversion | Buy below VWAP, sell above — volume-weighted bands |

## Usage

```python
from strategies.strategy_spec import StrategySpec

# Load a template
with open("strategies/templates/pairs_trading.yaml") as f:
    spec = StrategySpec.from_yaml(f.read())

print(spec.metadata.name)        # "pairs-trading-zscore"
print(spec.assets)                # ["KO", "PEP"]
print(spec.exit.take_profit)     # 0.0
print(spec.risk.max_drawdown_pct) # 0.10
```

## Customizing

Copy any template and modify:

```bash
cp strategies/templates/breakout_volume.yaml my_breakout.yaml
# Edit parameters, symbols, risk settings
```

## Adding New Templates

1. Create a new `.yaml` file in this directory
2. Follow the `whale/v1` API schema from `strategy_spec.py`
3. Include `performance` section with backtest results
4. Add your template to the table above
