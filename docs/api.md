# FinClaw API Reference

## Technical Analysis (`src.ta`)

All functions accept NumPy arrays and return NumPy arrays.

### Moving Averages

| Function | Signature | Description |
|---|---|---|
| `sma(data, period)` | `Array → Array` | Simple Moving Average |
| `ema(data, period)` | `Array → Array` | Exponential Moving Average |
| `wma(data, period)` | `Array → Array` | Weighted Moving Average |
| `dema(data, period)` | `Array → Array` | Double EMA |
| `tema(data, period)` | `Array → Array` | Triple EMA |

### Oscillators

| Function | Signature | Returns |
|---|---|---|
| `rsi(data, period=14)` | `Array → Array` | Relative Strength Index (0-100) |
| `stochastic_rsi(data, rsi_period=14, stoch_period=14)` | `Array → (K, D)` | Stochastic RSI tuple |
| `mfi(high, low, close, volume, period=14)` | `4×Array → Array` | Money Flow Index |

### Trend

| Function | Signature | Returns |
|---|---|---|
| `macd(data, fast=12, slow=26, signal_period=9)` | `Array → (line, signal, histogram)` | MACD tuple |
| `adx(high, low, close, period=14)` | `3×Array → Array` | Average Directional Index |
| `parabolic_sar(high, low, af_start=0.02, af_step=0.02, af_max=0.2)` | `2×Array → Array` | Parabolic SAR |
| `ichimoku(high, low, close, ...)` | `3×Array → dict` | Ichimoku Cloud (tenkan, kijun, senkou_a, senkou_b, chikou) |

### Volatility

| Function | Signature | Returns |
|---|---|---|
| `bollinger_bands(data, period=20, num_std=2.0)` | `Array → dict` | `{upper, middle, lower, pct_b, bandwidth}` |
| `atr(high, low, close, period=14)` | `3×Array → Array` | Average True Range |

### Volume

| Function | Signature | Returns |
|---|---|---|
| `obv(close, volume)` | `2×Array → Array` | On-Balance Volume |
| `cmf(high, low, close, volume, period=20)` | `4×Array → Array` | Chaikin Money Flow |

---

## Strategies (`src.strategies`)

All strategies implement a common interface with `generate_signal(prices, **kwargs)` returning a signal score.

### `MomentumJTStrategy`

Jegadeesh-Titman cross-sectional momentum.

```python
from src.strategies import MomentumJTStrategy
s = MomentumJTStrategy(lookback=12, holding=1)
signal = s.generate_signal(prices)
```

### `MeanReversionStrategy`

Bollinger Band + RSI mean reversion.

```python
from src.strategies import MeanReversionStrategy
s = MeanReversionStrategy(bb_period=20, rsi_period=14)
signal = s.generate_signal(prices)
```

### `PairsTradingStrategy`

Statistical arbitrage on correlated pairs.

```python
from src.strategies import PairsTradingStrategy
s = PairsTradingStrategy(lookback=60, entry_z=2.0, exit_z=0.5)
signal = s.generate_signal(prices_a, prices_b)
```

### `TrendFollowingStrategy`

ADX + MACD trend detection.

```python
from src.strategies import TrendFollowingStrategy
s = TrendFollowingStrategy(adx_threshold=25)
signal = s.generate_signal(prices, high=high, low=low)
```

### `ValueMomentumStrategy`

Combined value and momentum scoring.

```python
from src.strategies import ValueMomentumStrategy
s = ValueMomentumStrategy()
signal = s.generate_signal(prices, fundamentals=fundamentals)
```

### `StrategyCombiner`

Weighted ensemble of multiple strategies.

```python
from src.strategies import StrategyCombiner, MomentumAdapter, MeanReversionAdapter
combiner = StrategyCombiner()
combiner.add(MomentumAdapter(), weight=0.6)
combiner.add(MeanReversionAdapter(), weight=0.4)
signal = combiner.generate_signal(prices)
```

---

## Backtesting (`src.backtesting`)

### `WalkForwardAnalyzer`

```python
WalkForwardAnalyzer(n_splits=5, train_ratio=0.7)
  .analyze(strategy, prices) → dict
```

Walk-forward optimization with configurable train/test splits.

### `MonteCarloSimulator`

```python
MonteCarloSimulator(n_simulations=1000, seed=None)
  .simulate(returns) → dict
```

Monte Carlo simulation of return paths. Returns percentile statistics.

### `MultiTimeframeBacktester`

```python
MultiTimeframeBacktester(timeframes=["1d", "1w", "1m"])
  .run(strategy, prices) → dict
```

### `BenchmarkComparison`

```python
BenchmarkComparison()
  .compare(strategy_returns, benchmark_returns) → dict
```

---

## Risk Management (`src.risk`)

### `KellyCriterion`

```python
KellyCriterion(win_rate, avg_win, avg_loss)
  .optimal_fraction() → float
  .half_kelly() → float
```

### `VaRCalculator`

```python
VaRCalculator(confidence=0.95, method="historical")
  .calculate(returns) → float
  .conditional_var(returns) → float
```

### `FixedFractional` / `VolatilitySizing`

```python
FixedFractional(fraction=0.02)
  .size(capital, price) → int

VolatilitySizing(target_vol=0.15)
  .size(capital, price, atr_value) → int
```

### `StopLossManager`

```python
StopLossManager(stop_type=StopLossType.TRAILING, pct=0.08)
  .check(current_price, entry_price, high_since_entry) → bool
```

`StopLossType`: `FIXED`, `TRAILING`, `ATR_BASED`, `TIME_BASED`

### `PortfolioRiskManager`

```python
PortfolioRiskManager()
  .max_position_risk(capital, max_pct=0.05) → float
  .portfolio_var(weights, cov_matrix, confidence=0.95) → float
```

---

## ML Pipeline (`src.ml`)

### `FeatureEngine`

```python
FeatureEngine()
  .build(prices, volumes) → ndarray  # Feature matrix
```

### Models

```python
LinearRegression().fit(X, y).predict(X) → ndarray
MAPredictor(period=20).fit(X, y).predict(X) → ndarray
RegimeClassifier(n_regimes=3).fit(X, y).predict(X) → ndarray
EnsembleModel(models=[...]).fit(X, y).predict(X) → ndarray
```

### `AlphaModel`

```python
AlphaModel()
  .fit(X, y) → self
  .predict(X) → list[Signal]
```

`Signal` dataclass: `ticker`, `score`, `confidence`, `timestamp`

### `SimpleSentiment`

```python
SimpleSentiment()
  .analyze(text) → float  # -1.0 to 1.0
```

### `WalkForwardPipeline`

```python
WalkForwardPipeline(model, feature_engine, n_splits=5)
  .run(prices, volumes) → dict
```

---

## Portfolio (`src.portfolio`)

### `PortfolioTracker`

```python
PortfolioTracker(initial_cash=100_000)
  .execute_trade(ticker, shares, price) → None
  .snapshot() → Snapshot
  .positions → dict[str, Position]
  .total_value(prices: dict) → float
```

### `PortfolioRebalancer`

```python
PortfolioRebalancer(threshold=0.05)
  .rebalance(current, target) → list[RebalanceAction]
```

`RebalanceAction`: `ticker`, `action` ("buy"/"sell"), `weight_change`

---

## Analytics (`src.analytics`)

| Class | Purpose |
|---|---|
| `AttributionAnalysis` | Performance attribution by factor |
| `CorrelationAnalyzer` | Cross-asset correlation analysis |
| `RegimeDetector` | Market regime classification |
| `RollingAnalytics` | Rolling Sharpe, beta, alpha |
| `ExecutionAnalytics` | Slippage and fill analysis |

---

## API Server (`src.api`)

### `FinClawServer`

```python
from src.api.server import FinClawServer
server = FinClawServer(port=8080)
server.start()  # blocking
```

### Endpoints

| Method | Path | Query Params |
|---|---|---|
| GET | `/api/signal` | `ticker`, `strategy` |
| GET | `/api/backtest` | `ticker`, `strategy`, `start`, `end` |
| GET | `/api/portfolio` | `tickers`, `method` |
| GET | `/api/screen` | `rsi_lt`, `rsi_gt`, `volume_gt`, etc. |
| GET | `/api/health` | — |

### `WebhookManager`

```python
from src.api.webhooks import WebhookManager
wh = WebhookManager()
wh.register("signal_change", url, format="slack")
wh.dispatch("signal_change", payload)
```

Supported formats: `json`, `slack`, `discord`, `teams`

---

## Alerts (`src.alerts`)

### `AlertEngine`

```python
from src.alerts import AlertEngine, AlertCondition
engine = AlertEngine()
engine.add(AlertCondition(ticker="AAPL", field="rsi", op="<", value=30))
alerts = engine.check()
```

---

## Screener (`src.screener`)

### `StockScreener`

```python
from src.screener import StockScreener
screener = StockScreener()
results = screener.screen({"rsi_lt": 30, "volume_gt": 1.5})
```

---

## Events (`src.events`)

### `EventBus`

```python
from src.events import EventBus
bus = EventBus()
bus.subscribe("signal", handler_fn)
bus.publish("signal", data)
```
