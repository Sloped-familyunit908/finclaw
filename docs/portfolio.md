# Portfolio Management

Portfolio optimization, rebalancing, attribution analytics, and tax tracking.

---

## Portfolio Tracker

Track holdings across multiple accounts and exchanges:

```python
from src.portfolio.tracker import PortfolioTracker

portfolio = PortfolioTracker()
portfolio.add_holding("AAPL", shares=100, cost_basis=150.00)
portfolio.add_holding("MSFT", shares=50, cost_basis=300.00)
portfolio.add_holding("BTC", shares=0.5, cost_basis=60000.00)

summary = portfolio.get_summary()
print(f"Total Value: ${summary['total_value']:,.2f}")
print(f"Total P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:.1%})")
```

---

## Portfolio Optimization

### Risk Parity

```bash
python finclaw.py portfolio --tickers AAPL,MSFT,GOOGL,AMZN --method risk_parity
```

```python
from src.portfolio.optimizer import PortfolioOptimizer

optimizer = PortfolioOptimizer()
weights = optimizer.optimize(
    tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "BTC-USD"],
    method="risk_parity",       # or "mean_variance", "equal_weight", "min_variance"
    start="2023-01-01",
)
# {'AAPL': 0.22, 'MSFT': 0.18, 'GOOGL': 0.20, 'AMZN': 0.15, 'BTC-USD': 0.25}
```

### Available Methods

| Method | Description |
|---|---|
| `equal_weight` | 1/N allocation |
| `risk_parity` | Weight by inverse volatility |
| `mean_variance` | Markowitz mean-variance (max Sharpe) |
| `min_variance` | Minimum variance portfolio |

---

## Rebalancing

Automated portfolio rebalancing with configurable triggers:

```python
from src.portfolio.rebalancer import Rebalancer

rebalancer = Rebalancer(
    target_weights={"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.25},
    threshold=0.05,           # Rebalance when 5% off target
    frequency="monthly",      # or "weekly", "quarterly", "threshold_only"
)

trades = rebalancer.calculate_trades(current_holdings)
```

---

## Attribution Analytics

Understand what drove your returns:

```python
from src.portfolio.attribution import AttributionAnalyzer

analyzer = AttributionAnalyzer()
report = analyzer.analyze(
    portfolio_returns=portfolio.get_returns(),
    benchmark_returns=benchmark.get_returns(),
)

print(f"Alpha: {report['alpha']:.2%}")
print(f"Beta: {report['beta']:.2f}")
print(f"Selection Effect: {report['selection']:.2%}")
print(f"Allocation Effect: {report['allocation']:.2%}")
```

---

## Transaction Cost Analysis

Decompose trading costs:

```python
from src.analytics.tca import TransactionCostAnalyzer

tca = TransactionCostAnalyzer()
costs = tca.analyze(trades)

print(f"Total Commission: ${costs['commission']:,.2f}")
print(f"Estimated Slippage: ${costs['slippage']:,.2f}")
print(f"Market Impact: ${costs['impact']:,.2f}")
print(f"Total Cost: ${costs['total']:,.2f} ({costs['total_bps']:.1f} bps)")
```

---

## Risk Metrics

```python
from src.risk.portfolio_risk import PortfolioRiskAnalyzer

risk = PortfolioRiskAnalyzer(portfolio)

print(f"Portfolio VaR (95%): {risk.var_95:.2%}")
print(f"Concentration (HHI): {risk.hhi:.2f}")
print(f"Max Correlation: {risk.max_correlation:.2f}")
print(f"Sector Exposure: {risk.sector_exposure}")
```

---

## Tax Tracking

Track realized gains/losses for tax reporting:

```python
from src.portfolio.tracker import PortfolioTracker

portfolio = PortfolioTracker()
# ... add holdings and trades ...

tax_report = portfolio.get_tax_report(year=2025)
print(f"Short-term gains: ${tax_report['short_term_gains']:,.2f}")
print(f"Long-term gains: ${tax_report['long_term_gains']:,.2f}")
print(f"Wash sale adjustments: ${tax_report['wash_sales']:,.2f}")
```

---

## CLI Commands

```bash
# Optimize portfolio allocation
python finclaw.py portfolio --tickers AAPL,MSFT,GOOGL --method risk_parity

# Portfolio risk analysis
python finclaw.py risk --portfolio portfolio.json

# Generate HTML report
python finclaw.py report --input backtest_results.json --format html
```
