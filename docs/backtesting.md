# Backtesting

FinClaw's backtesting engine includes walk-forward analysis, Monte Carlo simulation, realistic order fills, and overfitting detection — all without external dependencies.

---

## Quick Start

```bash
# Backtest a single ticker
finclaw backtest --strategy momentum --ticker NVDA --start 2020-01-01 --end 2025-01-01

# Backtest multiple tickers
finclaw backtest --strategy mean_reversion --ticker AAPL,MSFT,GOOGL --start 2022-01-01

# Compare strategies
finclaw backtest --strategy momentum,mean_reversion,trend_following --ticker NVDA
```

---

## Backtesting Engine Features

### Walk-Forward Analysis

K-fold time-series cross-validation that trains on past data and validates on unseen future data:

```python
from src.backtesting.engine import BacktestEngine

engine = BacktestEngine()
results = engine.run(
    strategy="momentum",
    tickers=["AAPL", "MSFT"],
    start="2020-01-01",
    end="2025-01-01",
    initial_capital=100000,
)
```

### Monte Carlo Simulation

Generates N random return paths to estimate the distribution of outcomes:

```python
from src.backtesting.monte_carlo import MonteCarloSimulator

mc = MonteCarloSimulator(n_simulations=1000)
distribution = mc.simulate(returns)
print(f"95th percentile drawdown: {distribution['p95_drawdown']:.1%}")
```

### Realistic Order Fills

The realistic engine models:

- **Slippage** — Market impact based on order size vs. average volume
- **Commissions** — Configurable fee structure per exchange
- **Partial fills** — Large orders may not fill completely
- **Market impact** — Price movement caused by your own trades

### Overfitting Detection

Automatically flags strategies that may be curve-fitted:

- **Deflated Sharpe Ratio** — Adjusts for multiple hypothesis testing
- **Combinatorial checks** — Tests strategy robustness across parameter variations

---

## Interpreting Results

### Key Metrics

| Metric | Good | Great | Description |
|---|---|---|---|
| Annualized Return | > 10% | > 20% | Yearly return rate |
| Sharpe Ratio | > 1.0 | > 1.5 | Risk-adjusted return |
| Max Drawdown | < -20% | < -10% | Worst peak-to-trough drop |
| Win Rate | > 50% | > 60% | Percentage of winning trades |
| Profit Factor | > 1.5 | > 2.0 | Gross profit / gross loss |
| Calmar Ratio | > 0.5 | > 1.0 | Return / max drawdown |

### Benchmark Comparison

FinClaw compares your strategy against standard benchmarks:

- **Buy & Hold** — Simple hold the asset
- **Equal Weight** — Equal allocation across all tickers
- **60/40** — Classic stock/bond split
- **Risk Parity** — Volatility-weighted allocation

---

## Strategy Comparison

Compare multiple strategies side-by-side:

```python
from src.backtesting.engine import compare_strategies

results = compare_strategies(
    strategies=["momentum_jt", "mean_reversion", "trend_following", "pairs_trading"],
    tickers=["AAPL", "MSFT", "GOOGL"],
    start="2020-01-01",
    capital=100000,
)
# Returns ranking across 8 metrics
```

---

## Common Pitfalls

### 1. Look-Ahead Bias

**Problem:** Using future data in your signals (e.g., today's close to decide today's trade).

**Solution:** FinClaw's engine enforces signal-on-close, trade-on-next-open by default.

### 2. Survivorship Bias

**Problem:** Only backtesting stocks that exist today, ignoring delisted companies.

**Solution:** Use FinClaw's survivorship bias check to include dead stocks in your universe.

### 3. Overfitting

**Problem:** Strategy performs amazingly in backtest but fails in live trading.

**Solution:**
- Use walk-forward analysis (not single train/test split)
- Check the deflated Sharpe ratio
- If your strategy has > 5 tunable parameters, be suspicious
- Out-of-sample performance should be within 50% of in-sample

### 4. Ignoring Transaction Costs

**Problem:** Backtest shows 50% returns, but fees eat 30%.

**Solution:** Always enable the realistic engine with slippage and commissions.

### 5. Small Sample Size

**Problem:** "100% win rate" on 3 trades.

**Solution:** Require minimum 30+ trades for statistical significance. Use Monte Carlo to estimate confidence intervals.

### 6. Regime Change

**Problem:** Strategy optimized for bull market fails in bear market.

**Solution:** Use the Strategy Combiner with regime detection, or test across multiple market cycles.

---

## Advanced: Custom Backtest Configuration

```python
engine = BacktestEngine(
    slippage_bps=10,          # 10 basis points slippage
    commission_pct=0.001,     # 0.1% commission
    partial_fills=True,       # Enable partial fill simulation
    market_impact=True,       # Model price impact
    walk_forward_folds=5,     # 5-fold walk-forward
)
```
