# Plugins

FinClaw has a plugin system for extending strategies, indicators, and exchange adapters without modifying core code.

---

## Plugin Architecture

```
src/plugins/
├── plugin_base.py       # Base class for all plugins
├── plugin_manager.py    # Discovery and loading
├── strategy_plugin.py   # Strategy plugin interface
├── indicator_plugin.py  # Indicator plugin interface
└── exchange_plugin.py   # Exchange plugin interface
```

Plugins are Python classes that inherit from a base interface. The plugin manager discovers and loads them at runtime.

---

## Strategy Plugins

Create a custom trading strategy:

```python
# my_strategy.py
from src.plugins.strategy_plugin import StrategyPlugin

class MyAwesomeStrategy(StrategyPlugin):
    """A custom momentum + RSI strategy."""
    
    name = "my_awesome"
    version = "1.0.0"
    description = "Custom momentum strategy with RSI filter"
    
    def __init__(self, rsi_threshold=30, momentum_period=20):
        self.rsi_threshold = rsi_threshold
        self.momentum_period = momentum_period
    
    def generate_signal(self, data):
        """Return 'buy', 'sell', or 'hold' based on data."""
        from src.ta.indicators import rsi, sma
        
        prices = [d["price"] for d in data]
        current_rsi = rsi(prices, period=14)[-1]
        
        if current_rsi < self.rsi_threshold:
            return {"action": "buy", "confidence": 0.8, "reason": "RSI oversold"}
        elif current_rsi > 70:
            return {"action": "sell", "confidence": 0.7, "reason": "RSI overbought"}
        return {"action": "hold", "confidence": 0.5}
    
    def backtest(self, data, capital=100000):
        """Run backtest and return results."""
        # Implement your backtest logic
        pass
```

### Register the Plugin

Place your file in the `plugins/` directory or register programmatically:

```python
from src.plugins.plugin_manager import PluginManager

pm = PluginManager()
pm.register(MyAwesomeStrategy)
pm.list_strategies()  # ['my_awesome', 'momentum_jt', ...]
```

---

## Indicator Plugins

Create a custom technical indicator:

```python
from src.plugins.indicator_plugin import IndicatorPlugin
import numpy as np

class VWAPIndicator(IndicatorPlugin):
    """Volume-Weighted Average Price."""
    
    name = "custom_vwap"
    version = "1.0.0"
    
    def calculate(self, prices, volumes, period=20):
        """Calculate VWAP over a rolling window."""
        prices = np.array(prices)
        volumes = np.array(volumes)
        
        cumulative_tp_vol = np.cumsum(prices * volumes)
        cumulative_vol = np.cumsum(volumes)
        
        return cumulative_tp_vol / cumulative_vol
```

### Use Custom Indicators in Strategies

```python
from src.plugins.plugin_manager import PluginManager

pm = PluginManager()
vwap_plugin = pm.get_indicator("custom_vwap")
vwap_values = vwap_plugin.calculate(prices, volumes)
```

---

## Exchange Plugins

Add a new exchange/data source:

```python
from src.plugins.exchange_plugin import ExchangePlugin

class MyBrokerExchange(ExchangePlugin):
    """Custom broker integration."""
    
    name = "my_broker"
    exchange_type = "stock_us"  # or "crypto", "stock_cn"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("MY_BROKER_KEY")
    
    def get_ticker(self, symbol):
        """Return current quote as dict with 'last', 'bid', 'ask', 'volume'."""
        # Call your broker's API
        response = self._api_call(f"/quote/{symbol}")
        return {
            "symbol": symbol,
            "last": response["price"],
            "bid": response["bid"],
            "ask": response["ask"],
            "volume": response["volume"],
        }
    
    def get_ohlcv(self, symbol, timeframe="1d", limit=50):
        """Return list of candle dicts with 'date', 'open', 'high', 'low', 'close', 'volume'."""
        response = self._api_call(f"/candles/{symbol}?tf={timeframe}&limit={limit}")
        return response["candles"]
```

### Register with the Exchange Registry

```python
from src.exchanges.registry import ExchangeRegistry

ExchangeRegistry.register("my_broker", MyBrokerExchange)

# Now usable everywhere
broker = ExchangeRegistry.get("my_broker")
quote = broker.get_ticker("AAPL")
```

---

## YAML Strategy Definitions

You can also define strategies as YAML files in `strategies/builtin/`:

```yaml
apiVersion: whale/v1
kind: Strategy
metadata:
  name: my-custom-strategy
  version: 1.0.0
  author: your-name
  description: Description of your strategy
  tags: [crypto, momentum]
  difficulty: intermediate

spec:
  assets:
    type: crypto
    symbols: [BTC, ETH]
  timeframe: 1d

  indicators:
    - name: rsi
      type: rsi
      period: 14
    - name: sma_50
      type: sma
      period: 50

  entry:
    logic: AND
    rules:
      - indicator: rsi
        condition: below
        threshold: 30
      - indicator: price
        condition: crosses_above
        value: sma_50

  exit:
    take_profit: 0.10
    stop_loss: 0.05

  risk:
    max_position_pct: 0.15
```

---

## Plugin Discovery

The plugin manager scans these directories for plugins:

1. `src/plugins/` — Built-in plugins
2. `~/.finclaw/plugins/` — User plugins
3. `FINCLAW_PLUGIN_DIR` environment variable — Custom plugin directory
