# Live Trading

Guide for transitioning from paper trading to live trading with proper risk management.

---

## Paper Trading

Paper trading simulates live trading with fake money. Always start here.

### Start Paper Trading

```bash
finclaw paper --strategy momentum --ticker BTCUSDT --exchange binance --capital 10000
```

### How It Works

1. Strategy generates signals from real-time data
2. Paper trader simulates order execution with realistic fills
3. Portfolio tracker records all trades, P&L, and risk metrics
4. No real money is at risk

### Paper Trading Checklist

Before going live, verify:

- [ ] Paper traded for at least 2 weeks
- [ ] Strategy performs within expected parameters
- [ ] Max drawdown stayed within tolerance
- [ ] Slippage estimates match real order book depth
- [ ] No unexpected errors or crashes
- [ ] Webhooks/alerts are working correctly

---

## Going Live

### Step 1: Configure Exchange API Keys

```bash
# Example: Binance
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# Example: Alpaca (US stocks)
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
export ALPACA_BASE_URL="https://api.alpaca.markets"  # live endpoint
```

!!! warning "API Key Security"
    - **Never** commit API keys to git
    - Use environment variables or a `.env` file (gitignored)
    - Enable IP whitelisting on your exchange
    - Use sub-accounts with limited permissions (trade-only, no withdraw)

### Step 2: Set Risk Limits

Configure risk management before any live trade:

```python
from src.risk.manager import RiskManager

risk = RiskManager(
    max_position_pct=0.10,       # Max 10% per position
    max_total_exposure=0.60,     # Max 60% invested
    max_daily_loss_pct=0.03,     # Stop trading after 3% daily loss
    max_drawdown_pct=0.15,       # Halt at 15% drawdown
    kelly_fraction=0.25,         # Quarter-Kelly for safety
)
```

### Step 3: Start with Small Size

Start at 10-25% of your intended allocation. Scale up over weeks as you gain confidence.

### Step 4: Enable Alerts

Set up webhook notifications:

```python
from src.notifications import setup_webhooks

setup_webhooks(
    slack_url="https://hooks.slack.com/services/...",
    discord_url="https://discord.com/api/webhooks/...",
    teams_url="https://outlook.office.com/webhook/...",
)
```

---

## Risk Management

### Position Sizing Methods

| Method | Description | Best For |
|---|---|---|
| Kelly Criterion | Optimal bet sizing based on edge | Experienced traders |
| Risk Parity | Weight by inverse volatility | Diversified portfolios |
| Equal Weight | Same $ amount per position | Beginners |
| Volatility Target | Target a specific portfolio vol | Institutional |

### Stop-Loss Types

| Type | Description |
|---|---|
| Fixed | Exit at X% loss from entry |
| Trailing | Exit at X% from highest price since entry |
| ATR-based | Exit at N × ATR from entry (adapts to volatility) |
| Time-based | Exit after N days regardless of P&L |

### Value-at-Risk (VaR)

```python
from src.risk.var import calculate_var

var_95 = calculate_var(returns, confidence=0.95, method="historical")
print(f"95% VaR: {var_95:.2%}")  # Max daily loss with 95% confidence
```

---

## Risk Dashboard

Launch the real-time HTML risk dashboard:

```bash
python -m src.dashboard.risk_dashboard --port 3000
```

Displays:
- Live P&L and portfolio value
- Position exposure by asset and sector
- Drawdown chart
- VaR and Kelly metrics
- Active alerts

---

## Common Live Trading Rules

1. **Never risk more than 2% of capital on a single trade**
2. **Set a daily loss limit** — walk away after hitting it
3. **Diversify across uncorrelated assets and strategies**
4. **Monitor latency** — delayed signals = bad fills
5. **Have a kill switch** — be able to flatten all positions instantly
6. **Log everything** — use the trade journal for post-trade analysis

---

## Trade Journal

```python
from src.journal.tracker import TradeJournal

journal = TradeJournal()
journal.log_trade(
    symbol="BTCUSDT",
    side="buy",
    price=65000,
    quantity=0.1,
    strategy="momentum",
    notes="Golden cross confirmed by AI debate",
)
journal.export("trades_march_2026.csv")
```
