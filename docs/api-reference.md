# FinClaw API Reference

> **Version 3.7.0** — Complete Python API documentation

---

## Table of Contents

- [Strategy Classes](#strategy-classes)
- [Technical Analysis Indicators](#technical-analysis-indicators)
- [Machine Learning](#machine-learning)
- [Risk Management](#risk-management)
- [Backtesting Engine](#backtesting-engine)
- [Data & Pipeline](#data--pipeline)
- [Crypto & DeFi](#crypto--defi)
- [Derivatives](#derivatives)
- [Analytics](#analytics)
- [Events & Plugins](#events--plugins)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)

---

## Strategy Classes

All strategies live in `src/strategies/`.

### MeanReversionStrategy

Z-score based mean reversion on price deviations from moving average.

```python
from src.strategies import MeanReversionStrategy

strategy = MeanReversionStrategy(
    lookback=20,        # Moving average lookback period
    entry_z=2.0,        # Z-score threshold to enter
    exit_z=0.5,         # Z-score threshold to exit
    stop_loss=0.05,     # Stop-loss percentage
)
signal = strategy.generate_signal(prices)  # returns: buy / sell / hold
```

### MomentumJTStrategy

Jegadeesh-Titman cross-sectional momentum strategy.

```python
from src.strategies import MomentumJTStrategy

strategy = MomentumJTStrategy(
    formation_period=12,  # Months of lookback for ranking
    holding_period=3,     # Months to hold positions
    skip_period=1,        # Skip most recent month
    top_pct=0.2,          # Top quintile = long
    bottom_pct=0.2,       # Bottom quintile = short
)
```

### TrendFollowingStrategy

Multi-indicator trend following with SMA crossover, MACD, and ADX confirmation.

```python
from src.strategies import TrendFollowingStrategy

strategy = TrendFollowingStrategy(
    fast_period=10,       # Fast SMA period
    slow_period=50,       # Slow SMA period
    atr_period=14,        # ATR period for stop placement
    adx_threshold=25,     # Minimum ADX for trend confirmation
)
```

### ValueMomentumStrategy

Combined value + momentum factor model.

```python
from src.strategies import ValueMomentumStrategy

strategy = ValueMomentumStrategy(
    value_weight=0.5,        # Weight for value factor
    momentum_weight=0.5,     # Weight for momentum factor
    rebalance_frequency=21,  # Trading days between rebalances
)
```

### PairsTradingStrategy

Statistical arbitrage on cointegrated pairs.

```python
from src.strategies import PairsTradingStrategy

strategy = PairsTradingStrategy(
    lookback=60,         # Lookback for spread calculation
    entry_z=2.0,         # Z-score entry threshold
    exit_z=0.0,          # Z-score exit threshold
    max_holding=20,      # Max holding period (days)
)
```

### SectorRotation

Rotates into strongest sectors based on relative momentum.

```python
from src.strategies import SectorRotation, SectorSignal

rotation = SectorRotation(
    momentum_period=63,   # 3-month momentum lookback
    top_n=3,              # Number of sectors to hold
    rebalance_days=21,    # Rebalance frequency
)
signal: SectorSignal = rotation.analyze(sector_data)
```

### SignalCombiner

Combines signals from multiple strategies with configurable weights.

```python
from src.strategies import SignalCombiner, CombinedSignal

combiner = SignalCombiner(weights={"momentum": 0.4, "trend": 0.3, "value": 0.3})
combined: CombinedSignal = combiner.combine(signals)
```

### RegimeAdaptive

Adapts strategy weights based on detected market regime (bull/bear/sideways).

```python
from src.strategies import RegimeAdaptive, RegimeSignal

adaptive = RegimeAdaptive(
    regime_lookback=252,   # Lookback for regime detection
    vol_threshold=0.2,     # Volatility boundary
)
signal: RegimeSignal = adaptive.analyze(prices)
```

### StrategyCombiner

Meta-strategy that combines multiple strategy adapters with weighted voting.

```python
from src.strategies import StrategyCombiner, MomentumAdapter, TrendFollowingAdapter

combiner = StrategyCombiner(strategies=[
    MomentumAdapter(weight=0.5),
    TrendFollowingAdapter(weight=0.5),
])
```

### Crypto Strategies

```python
from src.strategies.crypto_strategies import GridBot, DCAStrategy, ArbitrageDetector

# Grid Trading
grid = GridBot(lower=25000, upper=35000, grids=10, amount_per_grid=100)

# Dollar-Cost Averaging
dca = DCAStrategy(amount=500, frequency="weekly")

# Cross-exchange arbitrage detection
arb = ArbitrageDetector(min_spread_pct=0.5)
```

---

## Technical Analysis Indicators

All indicators are **pure NumPy** — zero TA-Lib dependency. Located in `src/ta/`.

### Moving Averages

| Function | Description | Signature |
|----------|-------------|-----------|
| `sma(data, period)` | Simple Moving Average | `Array → Array` |
| `ema(data, period)` | Exponential Moving Average | `Array → Array` |
| `wma(data, period)` | Weighted Moving Average | `Array → Array` |
| `dema(data, period)` | Double EMA | `Array → Array` |
| `tema(data, period)` | Triple EMA | `Array → Array` |

### Oscillators

| Function | Description | Returns |
|----------|-------------|---------|
| `rsi(data, period=14)` | Relative Strength Index | `Array` (0–100) |
| `stochastic_rsi(data, rsi_period=14, stoch_period=14)` | Stochastic RSI | `(K, D)` tuple |
| `macd(data, fast=12, slow=26, signal_period=9)` | MACD | `(line, signal, histogram)` |
| `mfi(high, low, close, volume, period=14)` | Money Flow Index | `Array` |

### Volatility & Trend

| Function | Description | Returns |
|----------|-------------|---------|
| `bollinger_bands(data, period=20, num_std=2.0)` | Bollinger Bands | `dict` with upper/middle/lower/pct_b/bandwidth |
| `atr(high, low, close, period=14)` | Average True Range | `Array` |
| `adx(high, low, close, period=14)` | Average Directional Index | `Array` |
| `parabolic_sar(high, low, af_start=0.02, af_step=0.02, af_max=0.2)` | Parabolic SAR | `Array` |

### Volume Indicators

| Function | Description | Returns |
|----------|-------------|---------|
| `obv(close, volume)` | On-Balance Volume | `Array` |
| `cmf(high, low, close, volume, period=20)` | Chaikin Money Flow | `Array` |

### Ichimoku Cloud

```python
from src.ta import ichimoku

cloud = ichimoku(high, low, close, tenkan_period=9, kijun_period=26,
                 senkou_b_period=52, displacement=26)
# Returns: {tenkan, kijun, senkou_a, senkou_b, chikou}
```

### Multi-Timeframe TA

```python
from src.ta.multi_timeframe import MultiTimeframeTAEngine

engine = MultiTimeframeTAEngine()
result = engine.analyze(ohlcv_data, timeframes=["1d", "1w", "1M"])
```

### Real-Time TA

```python
from src.ta.realtime_ta import RealtimeTAEngine

rt = RealtimeTAEngine(indicators=["rsi", "macd", "bollinger"])
rt.on_tick(price)  # incremental update
signals = rt.get_signals()
```

---

## Machine Learning

All ML modules are in `src/ml/`. Models are **numpy-only** (no sklearn required for core).

### FeatureEngine

Generates 20+ technical features from price data.

```python
from src.ml import FeatureEngine

engine = FeatureEngine()
features = engine.build_features(prices)
# Returns dict of feature arrays: returns_1d, returns_5d, vol_20d, rsi_14, ...
```

### Models

```python
from src.ml import LinearRegression, MAPredictor, RegimeClassifier, EnsembleModel

# Linear regression
lr = LinearRegression()
lr.fit(X_train, y_train)
predictions = lr.predict(X_test)

# Moving average predictor
ma = MAPredictor(period=20)
ma.fit(prices)

# Regime classifier (bull/bear/sideways)
rc = RegimeClassifier(n_regimes=3, vol_lookback=60)
regimes = rc.classify(returns)

# Ensemble of multiple models
ensemble = EnsembleModel(models=[lr, ma], weights=[0.6, 0.4])
ensemble_pred = ensemble.predict(X_test)
```

### AlphaModel

Multi-signal alpha generation with information coefficient (IC) tracking.

```python
from src.ml import AlphaModel, Signal

alpha = AlphaModel()
alpha.add_signal(Signal(name="momentum", values=mom_scores, ic=0.05))
alpha.add_signal(Signal(name="value", values=val_scores, ic=0.03))
combined = alpha.combine()  # IC-weighted combination
```

### WalkForwardPipeline

Rolling train/test ML pipeline with walk-forward validation.

```python
from src.ml import WalkForwardPipeline

pipeline = WalkForwardPipeline(
    model=LinearRegression(),
    train_size=252,
    test_size=63,
    step_size=21,
)
results = pipeline.run(features, targets)
```

### FeatureStore

Centralized feature storage and versioning.

```python
from src.ml import FeatureStore

store = FeatureStore(path="features.db")
store.save("momentum_features", features, version="v1")
loaded = store.load("momentum_features", version="v1")
```

### SimpleSentiment

Keyword-based news sentiment analyzer.

```python
from src.ml import SimpleSentiment

sentiment = SimpleSentiment()
score = sentiment.analyze("Fed raises rates amid inflation concerns")
# Returns: float between -1.0 (bearish) and 1.0 (bullish)
```

---

## Risk Management

Located in `src/risk/`.

### Position Sizing

```python
from src.risk import KellyCriterion, FixedFractional, VolatilitySizing

# Kelly Criterion
kelly = KellyCriterion(win_rate=0.55, avg_win=0.03, avg_loss=0.02)
fraction = kelly.optimal_fraction()
size = kelly.position_size(capital=100000)

# Fixed fractional
ff = FixedFractional(fraction=0.02)
size = ff.position_size(capital=100000, risk_per_share=2.50)

# Volatility-based sizing
vs = VolatilitySizing(target_vol=0.15, lookback=20)
size = vs.position_size(capital=100000, prices=price_array)
```

### Stop-Loss Manager

```python
from src.risk import StopLossManager, StopLossType

sl = StopLossManager(
    stop_type=StopLossType.TRAILING,
    percentage=0.05,       # 5% trailing stop
    atr_multiplier=2.0,    # or ATR-based
)
triggered = sl.check(entry_price=100, current_price=93, high_since_entry=110)
```

### VaR Calculator

```python
from src.risk import VaRCalculator

var = VaRCalculator(returns=daily_returns)
var_95 = var.historical(confidence=0.95)
var_99 = var.parametric(confidence=0.99)
cvar = var.conditional(confidence=0.95)
mc_var = var.monte_carlo(confidence=0.95, simulations=10000)
```

### AdvancedRiskMetrics

```python
from src.risk import AdvancedRiskMetrics

metrics = AdvancedRiskMetrics(returns=returns)
metrics.sharpe_ratio(risk_free=0.04)
metrics.sortino_ratio()
metrics.calmar_ratio()
metrics.omega_ratio(threshold=0.0)
metrics.max_drawdown()
metrics.tail_ratio()
```

### StressTester

```python
from src.risk import StressTester, Portfolio

portfolio = Portfolio(positions={"AAPL": 100, "GOOGL": 50}, prices=current_prices)
tester = StressTester()
results = tester.run_scenarios(portfolio, scenarios=["2008_crisis", "covid_crash", "rate_hike"])
```

### RiskBudgeter

```python
from src.risk import RiskBudgeter

budgeter = RiskBudgeter(total_risk_budget=0.10)
allocations = budgeter.allocate(
    strategies=["momentum", "mean_rev", "trend"],
    vols=[0.15, 0.08, 0.12],
    correlations=corr_matrix,
)
```

### PortfolioRiskManager

```python
from src.risk import PortfolioRiskManager

prm = PortfolioRiskManager(max_position_pct=0.20, max_sector_pct=0.40, max_drawdown=0.15)
approved = prm.check_trade(portfolio, proposed_trade)
risk_report = prm.report(portfolio)
```

---

## Backtesting Engine

Located in `src/backtesting/`.

### Event-Driven Backtester (v3.6)

Full event-driven architecture with market/signal/order/fill events.

```python
from src.backtesting import EventDrivenBacktester, EventType

bt = EventDrivenBacktester(
    initial_capital=100000,
    commission_rate=0.001,
    slippage_bps=5,
)
result = bt.run(strategy=my_strategy, data=ohlcv_data)
print(result.total_return, result.sharpe_ratio, result.max_drawdown)
```

### RealisticBacktester

Production-grade with slippage, commissions, market impact, partial fills.

```python
from src.backtesting import RealisticBacktester, BacktestConfig

config = BacktestConfig(
    initial_capital=100000,
    slippage_model=SlippageModel(bps=5),
    commission_model=CommissionModel(rate=0.001),
    market_impact=MarketImpactModel(factor=0.1),
)
bt = RealisticBacktester(config)
result = bt.run(signals=signals, prices=prices)
```

### Walk-Forward Optimization

```python
from src.backtesting import WalkForwardOptimizer

wfo = WalkForwardOptimizer(
    train_window=252,
    test_window=63,
    step_size=21,
    metric="sharpe",
)
result: WalkForwardResult = wfo.optimize(strategy_class, param_grid, data)
```

### Monte Carlo Simulation

```python
from src.backtesting import MonteCarloSimulator

mc = MonteCarloSimulator(n_simulations=10000, confidence=0.95)
mc_result = mc.run(returns=strategy_returns)
print(mc_result.median_return, mc_result.var_95, mc_result.probability_of_loss)
```

### Benchmarks

```python
from src.backtesting import BuyAndHold, EqualWeight, ClassicPortfolio, run_all_benchmarks

# Individual
bh = BuyAndHold()
result = bh.run(prices)

# All benchmarks at once
results = run_all_benchmarks(prices, tickers)
```

### Strategy Comparator

```python
from src.backtesting import StrategyComparator

comp = StrategyComparator()
comp.add("Momentum", momentum_results)
comp.add("MeanRev", meanrev_results)
comparison = comp.compare()  # Ranked by 8 metrics
```

### Overfit Detection & Survivorship Bias

```python
from src.backtesting import OverfitDetector, SurvivorshipBiasChecker

# Overfit detection
od = OverfitDetector()
od.check(in_sample_sharpe=2.5, out_of_sample_sharpe=0.3)

# Survivorship bias
sbc = SurvivorshipBiasChecker()
report = sbc.check(universe_with_delistings, universe_survivors_only)
```

---

## Data & Pipeline

### Price Data

```python
from src.data.prices import PriceLoader

loader = PriceLoader()
data = loader.fetch("AAPL", period="5y")  # Uses yfinance
```

### Data Cache

```python
from src.data.cache import DataCache

cache = DataCache(db_path="cache.db")
cache.set("key", dataframe, ttl_hours=24)
cached = cache.get("key", max_age_hours=24)
```

### Multi-Asset Support

```python
from src.data.multi_asset import MultiAssetLoader

loader = MultiAssetLoader()
data = loader.fetch(["AAPL", "BTC-USD", "GC=F"], period="2y")
```

### Data Quality Validation

```python
from src.pipeline.validator import DataValidator

validator = DataValidator()
report = validator.validate(df)  # Checks gaps, outliers, staleness
```

### Market Data Router (v3.5)

```python
from src.data.data_router import DataRouter

router = DataRouter()
data = router.fetch("AAPL")  # Auto-selects best source
```

---

## Crypto & DeFi

```python
from src.crypto import OnChainAnalytics, CryptoRebalancer
from src.defi import YieldTracker

# On-chain analytics
oc = OnChainAnalytics()
whales = oc.detect_whale_transactions("BTC", min_value_usd=1_000_000)

# Portfolio rebalancing
rebalancer = CryptoRebalancer(target_weights={"BTC": 0.5, "ETH": 0.3, "SOL": 0.2})
trades = rebalancer.rebalance(current_holdings)

# DeFi yield tracking
yt = YieldTracker()
yields = yt.scan_yields(protocols=["aave", "compound"])
```

---

## Derivatives

```python
from src.derivatives.options_pricing import BlackScholes, BinomialTree, MonteCarloPricer
from src.derivatives.greeks import GreeksCalculator
from src.derivatives.vol_surface import VolSurface

# Black-Scholes
bs = BlackScholes(S=100, K=105, T=0.25, r=0.05, sigma=0.20)
price = bs.call_price()
greeks = bs.greeks()  # delta, gamma, theta, vega, rho

# Binomial Tree
bt = BinomialTree(S=100, K=105, T=0.25, r=0.05, sigma=0.20, steps=100)
american_put = bt.price(option_type="put", american=True)

# Monte Carlo
mc = MonteCarloPricer(S=100, K=105, T=0.25, r=0.05, sigma=0.20, n_paths=100000)
exotic = mc.price(payoff_fn=my_barrier_payoff)

# Volatility Surface
vs = VolSurface()
vs.fit(strikes, expiries, market_vols)
iv = vs.interpolate(strike=105, expiry=0.25)
```

---

## Analytics

```python
from src.analytics import (
    AttributionAnalyzer,     # Brinson-style attribution
    DrawdownAnalyzer,        # Drawdown decomposition
    TradeAnalyzer,           # Win/loss, P&L per trade
    RollingMetrics,          # Rolling Sharpe, vol, beta
    RegimeDetector,          # HMM-based regime detection
    CorrelationAnalyzer,     # Dynamic correlation tracking
    TCAAnalyzer,             # Transaction cost analysis
    LiquidityAnalyzer,       # Bid-ask, volume analysis
    SensitivityAnalyzer,     # Parameter sensitivity
    TaxCalculator,           # Tax lot tracking
)
```

---

## Events & Plugins

### Event Bus

```python
from src.events import EventBus, Event

bus = EventBus()

@bus.on("signal")
def on_signal(event: Event):
    print(f"Signal: {event.data}")

bus.emit("signal", data={"ticker": "AAPL", "action": "buy"})
```

### Plugin System

```python
from src.plugins import PluginManager

pm = PluginManager()
pm.discover("plugins/")    # Auto-discover plugins
pm.load("my_plugin")       # Load specific plugin

# Plugin types: strategy, data_source, indicator, exporter
# Plugins must expose a register(manager) function
```

---

## CLI Commands

```bash
# Backtest a strategy
finclaw backtest --tickers AAPL,MSFT --strategy momentum --start 2020-01-01

# Screen stocks
finclaw screen --criteria "rsi<30 AND volume>1000000"

# Analyze a ticker
finclaw analyze --ticker AAPL

# Track portfolio
finclaw portfolio --tickers AAPL,GOOGL,MSFT --weights 0.4,0.3,0.3

# Get current price
finclaw price --ticker AAPL

# Options pricing
finclaw options --ticker AAPL --strike 150 --expiry 2026-06-20

# Paper trading
finclaw paper-trade --strategy trend_following --tickers AAPL,MSFT

# Generate report
finclaw report --ticker AAPL --format html

# Interactive mode
finclaw interactive
```

---

## Configuration

FinClaw uses `finclaw.yml` for configuration:

```yaml
# finclaw.yml
data:
  provider: yfinance          # Data source
  cache_ttl_hours: 24         # Cache duration

backtest:
  initial_capital: 100000
  commission: 0.001            # 0.1% per trade
  slippage_bps: 5              # 5 basis points
  benchmark: SPY

risk:
  max_position_pct: 0.20      # Max 20% in one position
  max_drawdown: 0.15           # Stop at 15% drawdown
  stop_loss_pct: 0.05          # Default 5% stop loss

ml:
  train_window: 252
  test_window: 63
  features:
    - returns_1d
    - returns_5d
    - vol_20d
    - rsi_14
    - macd_signal

notifications:
  slack_webhook: null
  discord_webhook: null
  telegram_token: null
  telegram_chat_id: null

api:
  host: 0.0.0.0
  port: 8000
```

### ConfigManager API

```python
from src.config_manager import ConfigManager

config = ConfigManager.load("finclaw.yml")
capital = config.get("backtest.initial_capital", 100000)
config.set("risk.max_drawdown", 0.10)
config.save()
```
