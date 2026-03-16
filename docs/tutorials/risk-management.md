# Risk Management Guide

Comprehensive guide to FinClaw's risk management tools.

## Overview

FinClaw provides layered risk management:

1. **Position Sizing** — How much to allocate per trade
2. **Stop-Loss** — When to exit losing positions
3. **Portfolio Risk** — Limits on concentration and drawdown
4. **Value at Risk (VaR)** — Statistical risk measurement
5. **Stress Testing** — Scenario-based risk analysis
6. **Risk Budgeting** — Allocate risk across strategies

## Position Sizing

### Kelly Criterion

Mathematically optimal bet sizing based on win rate and payoff ratio.

```python
from src.risk import KellyCriterion

kelly = KellyCriterion(win_rate=0.55, avg_win=0.03, avg_loss=0.02)

# Full Kelly (aggressive)
full = kelly.optimal_fraction()  # ~0.275

# Half Kelly (recommended for live trading)
size = kelly.position_size(capital=100000, kelly_fraction=0.5)
print(f"Position size: ${size:,.0f}")
```

### Fixed Fractional

Risk a fixed percentage of capital per trade.

```python
from src.risk import FixedFractional

ff = FixedFractional(fraction=0.02)  # Risk 2% per trade
size = ff.position_size(capital=100000, risk_per_share=2.50)
print(f"Shares: {size}")
```

### Volatility-Based Sizing

Scale position size inversely with volatility.

```python
from src.risk import VolatilitySizing

vs = VolatilitySizing(target_vol=0.15, lookback=20)
size = vs.position_size(capital=100000, prices=price_array)
```

## Stop-Loss Management

```python
from src.risk import StopLossManager, StopLossType

# Fixed percentage stop
fixed = StopLossManager(stop_type=StopLossType.FIXED, percentage=0.05)

# Trailing stop
trailing = StopLossManager(stop_type=StopLossType.TRAILING, percentage=0.08)

# ATR-based stop
atr_stop = StopLossManager(stop_type=StopLossType.ATR, atr_multiplier=2.0)

# Check if stop is triggered
triggered = trailing.check(
    entry_price=100,
    current_price=94,
    high_since_entry=110,
)
if triggered:
    print("STOP HIT — exit position")
```

## Value at Risk (VaR)

```python
from src.risk import VaRCalculator

var = VaRCalculator(returns=daily_returns)

# Historical VaR (non-parametric)
var_95 = var.historical(confidence=0.95)
print(f"95% VaR: {var_95:.2%}")

# Parametric VaR (assumes normal distribution)
var_99 = var.parametric(confidence=0.99)

# Conditional VaR (Expected Shortfall)
cvar = var.conditional(confidence=0.95)
print(f"CVaR (Expected Shortfall): {cvar:.2%}")

# Monte Carlo VaR
mc_var = var.monte_carlo(confidence=0.95, simulations=10000)
```

## Portfolio-Level Risk

```python
from src.risk import PortfolioRiskManager

prm = PortfolioRiskManager(
    max_position_pct=0.20,    # No single position > 20%
    max_sector_pct=0.40,      # No sector > 40%
    max_drawdown=0.15,        # Stop trading at 15% portfolio drawdown
    max_correlation=0.80,     # Avoid highly correlated positions
)

# Check before each trade
approved = prm.check_trade(portfolio, proposed_trade)
if not approved:
    print("Trade rejected — risk limit breached")

# Full risk report
report = prm.report(portfolio)
print(report)
```

## Stress Testing

```python
from src.risk import StressTester, Portfolio

portfolio = Portfolio(
    positions={"AAPL": 100, "GOOGL": 50, "MSFT": 75},
    prices=current_prices,
)

tester = StressTester()
results = tester.run_scenarios(portfolio, scenarios=[
    "2008_crisis",      # -50% equities
    "covid_crash",      # -34% in 23 days
    "rate_hike",        # +200bps rates
    "flash_crash",      # -10% intraday
])

for scenario, impact in results.items():
    print(f"{scenario}: portfolio impact {impact:.2%}")
```

## Risk Budgeting

Allocate total portfolio risk across strategies:

```python
from src.risk import RiskBudgeter

budgeter = RiskBudgeter(total_risk_budget=0.10)  # 10% total portfolio vol

allocations = budgeter.allocate(
    strategies=["momentum", "mean_reversion", "trend"],
    vols=[0.15, 0.08, 0.12],
    correlations=corr_matrix,
)

for strategy, alloc in allocations.items():
    print(f"{strategy}: {alloc:.1%} allocation")
```

## Advanced Risk Metrics

```python
from src.risk import AdvancedRiskMetrics

metrics = AdvancedRiskMetrics(returns=strategy_returns)

print(f"Sharpe:    {metrics.sharpe_ratio():.2f}")
print(f"Sortino:   {metrics.sortino_ratio():.2f}")
print(f"Calmar:    {metrics.calmar_ratio():.2f}")
print(f"Omega:     {metrics.omega_ratio():.2f}")
print(f"Max DD:    {metrics.max_drawdown():.2%}")
print(f"Tail:      {metrics.tail_ratio():.2f}")
```

## Putting It All Together

```python
from src.risk import (
    KellyCriterion, StopLossManager, StopLossType,
    PortfolioRiskManager, VaRCalculator,
)
from src.backtesting import RealisticBacktester, BacktestConfig

# 1. Size positions with Kelly
kelly = KellyCriterion(win_rate=0.55, avg_win=0.03, avg_loss=0.02)

# 2. Set trailing stops
stop = StopLossManager(stop_type=StopLossType.TRAILING, percentage=0.08)

# 3. Portfolio limits
prm = PortfolioRiskManager(max_position_pct=0.15, max_drawdown=0.10)

# 4. Backtest with realistic costs
config = BacktestConfig(initial_capital=100000)
bt = RealisticBacktester(config)
result = bt.run(signals=signals, prices=prices)

# 5. Measure risk
var = VaRCalculator(returns=result.daily_returns)
print(f"Daily VaR (95%): {var.historical(0.95):.2%}")
```

## Next Steps

- [Full API Reference](../api-reference.md)
- [Architecture](../architecture.md)
