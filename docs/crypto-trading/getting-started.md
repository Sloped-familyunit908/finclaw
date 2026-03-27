# Crypto Trading: Getting Started

This guide walks you through setting up FinClaw for crypto trading — from downloading data to running a live dry-run.

## Prerequisites

```bash
pip install finclaw-ai
# or with crypto extras explicitly
pip install "finclaw-ai[crypto]"
```

This installs [ccxt](https://github.com/ccxt/ccxt) which provides access to 100+ cryptocurrency exchanges.

## Step 1: Download Crypto Data

Download OHLCV data for the top 20 cryptocurrencies by market cap:

```bash
# Download Top 20 crypto (default: Binance, 1h candles, 1 year)
finclaw download-crypto

# Customize the download
finclaw download-crypto \
  --exchange binance \
  --symbols BTC/USDT ETH/USDT SOL/USDT \
  --timeframe 4h \
  --since 2025-01-01 \
  --output data/crypto
```

### Supported Timeframes

| Timeframe | Flag | Use Case |
|-----------|------|----------|
| 1 minute | `1m` | Scalping strategies |
| 5 minutes | `5m` | Short-term momentum |
| 15 minutes | `15m` | Intraday patterns |
| 1 hour | `1h` | Default, balanced signal/noise |
| 4 hours | `4h` | Swing trading |
| 1 day | `1d` | Position trading |

## Step 2: Start Evolution

Once you have data, start the genetic algorithm to discover optimal trading strategies:

```bash
# Start 24/7 evolution on crypto data
finclaw evolve \
  --market crypto \
  --data-dir data/crypto \
  --generations 999999 \
  --population 30

# Evolution with specific exchange data
finclaw evolve \
  --market crypto \
  --exchange okx \
  --timeframe 4h \
  --generations 999999
```

### What Happens During Evolution

1. **Generation 0** — Random population of 30 strategies initialized
2. **Each generation** — Strategies are backtested, scored by Sharpe ratio (with turnover penalty)
3. **Selection** — Top 5 strategies survive
4. **Crossover & mutation** — New strategies bred from winners
5. **Checkpointing** — `best_ever.json` updated whenever a new record is set
6. **Hall of Fame** — Timestamped copies of every record-breaking DNA saved

Progress is logged to the console. You can safely stop and resume at any time — `best_ever.json` persists across runs.

## Step 3: Validate Results

Before going live, validate your evolved strategy with a walk-forward backtest:

```bash
# Walk-forward validation
finclaw check-backtest --results evolution_results/best_ever.json

# Full validation with Monte Carlo
finclaw check-backtest \
  --results evolution_results/best_ever.json \
  --monte-carlo 1000 \
  --confidence 0.95
```

The validation report includes:
- In-sample vs out-of-sample performance
- Monte Carlo p-value (should be < 0.05)
- Bootstrap confidence intervals
- Factor IC/IR analysis
- Drawdown analysis

## Step 4: Dry-Run Mode (Paper Trading)

Test your strategy with real market data but simulated trades:

```bash
# Start paper trading on Binance
finclaw paper \
  --market crypto \
  --symbols BTC/USDT ETH/USDT SOL/USDT \
  --strategy evolution_results/best_ever.json

# With specific exchange
finclaw paper \
  --market crypto \
  --exchange bybit \
  --symbols BTC/USDT \
  --initial-capital 10000
```

Paper trading mode:
- Connects to real exchange WebSocket feeds for live prices
- Simulates order execution (no real orders placed)
- Tracks portfolio P&L in real time
- Logs all signals and simulated trades

## Step 5: Telegram Notifications

Get real-time alerts for trades and signals via Telegram.

### Setup

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Configure FinClaw:

```bash
# Set Telegram credentials via environment variables
export FINCLAW_TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
export FINCLAW_TELEGRAM_CHAT_ID="YOUR_CHAT_ID"
```

### Notification Types

| Event | Example |
|-------|---------|
| Trade Signal | 🟢 BUY BTC/USDT @ 67,420 — Confidence: 0.82 |
| Trade Executed | ✅ BOUGHT 0.15 BTC/USDT @ 67,420 |
| Position Closed | 📊 SOLD BTC/USDT @ 69,100 — P&L: +2.49% |
| Daily Summary | 📋 Daily: +1.8% P&L, 3 trades, Sharpe: 2.1 |
| Risk Alert | ⚠️ Drawdown: -8.2% — approaching 10% limit |
| Evolution Update | 🧬 New best strategy! Gen 2,341, Sharpe: 3.12 |

### Enable Notifications

```bash
# Enable for paper trading
finclaw paper --market crypto \
  --symbols BTC/USDT --notify telegram

# Enable for evolution progress
finclaw evolve --market crypto --notify telegram
```

## Risk Management

FinClaw includes several risk management controls:

### Configuration

```yaml
# finclaw.yaml or via CLI flags
risk:
  # Maximum drawdown before stopping
  max_drawdown: 0.10       # 10%

  # Maximum position size per asset
  max_position_pct: 0.20   # 20% of portfolio

  # Maximum number of concurrent positions
  max_positions: 5

  # Stop loss per trade
  stop_loss: 0.05           # 5%

  # Take profit per trade
  take_profit: 0.15         # 15%

  # Maximum daily loss
  max_daily_loss: 0.03      # 3%

  # Cooldown after hitting limits (minutes)
  cooldown_minutes: 60
```

### Command-Line Overrides

```bash
finclaw paper --market crypto \
  --symbols BTC/USDT ETH/USDT \
  --max-drawdown 0.10 \
  --max-position-pct 0.20 \
  --stop-loss 0.05
```

### Risk Best Practices

1. **Start with dry-run** — Always paper trade first, for at least 2 weeks
2. **Small positions** — Begin with 1-5% position sizes when going live
3. **Diversify** — Don't put everything in one pair
4. **Set max drawdown** — 10% is a reasonable starting point
5. **Monitor actively** — Use Telegram alerts to stay informed
6. **Review daily** — Check the daily summary notifications

## Next Steps

- [Strategy Evolution Deep Dive](../evolution.md)
- [Exchange Configuration](../exchanges.md)
- [Live Trading Guide](../live-trading.md)
- [Factor Library Details](../factor_gap_analysis.md)
