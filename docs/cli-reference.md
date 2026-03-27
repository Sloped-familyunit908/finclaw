# CLI Reference

Complete command reference for the `finclaw` CLI.

---

## Usage

```bash
finclaw <command> [options]
```

---

## Commands

### `scan` — Market Scanner

Scan a market for investment opportunities using a strategy preset.

```bash
finclaw scan --market <market> --style <style>
```

| Option | Values | Default | Description |
|---|---|---|---|
| `--market` | `us`, `china`, `hk`, `japan`, `korea` | `us` | Target market |
| `--style` | See table below | `balanced` | Strategy preset |

**Strategy Presets:**

| Style | Risk | Picks | Target Return |
|---|---|---|---|
| `druckenmiller` | Very High | Top 3 | 20-35% |
| `soros` | High | Top 5 | 25-30% |
| `lynch` | High | Top 6 | 20-27% |
| `buffett` | Medium-High | Top 8 | 20-30% |
| `dalio` | Medium | Top 12 | 15-20% |
| `momentum` | High | Top 5 | 20-30% |
| `mean_reversion` | Medium | Top 8 | 12-18% |
| `aggressive` | High | Top 5 | 25-35% |
| `balanced` | Medium | Top 10 | 10-15% |
| `conservative` | Low | Top 15 | 8-12% |

**Examples:**

```bash
finclaw scan --market us --style soros
finclaw scan --market china --style buffett
finclaw scan --market hk --style momentum
```

---

### `backtest` — Strategy Backtesting

Run a historical backtest on one or more tickers.

```bash
finclaw backtest --strategy <name> --ticker <symbols> [options]
```

| Option | Description |
|---|---|
| `--strategy` | Strategy name (e.g., `momentum`, `mean_reversion`, `trend_following`) |
| `--ticker` | Comma-separated ticker symbols |
| `--start` | Start date (YYYY-MM-DD) |
| `--end` | End date (YYYY-MM-DD, default: today) |
| `--period` | Alternative to start/end (e.g., `5y`, `1y`, `6m`) |
| `--capital` | Initial capital (default: 100000) |

**Examples:**

```bash
finclaw backtest --strategy momentum --ticker NVDA --period 5y
finclaw backtest --strategy mean_reversion --ticker AAPL,MSFT,GOOGL --start 2022-01-01
```

---

### `signal` — Trading Signals

Generate real-time trading signals for a ticker.

```bash
finclaw signal --ticker <symbol> --strategy <name>
```

**Examples:**

```bash
finclaw signal --ticker MSFT --strategy mean_reversion
finclaw signal --ticker BTCUSDT --strategy momentum
```

---

### `optimize` — Parameter Optimization

Optimize strategy parameters over historical data.

```bash
finclaw optimize --strategy <name> --param-grid <file> --data <ticker>
```

---

### `report` — Generate Reports

Create HTML or PDF reports from backtest results.

```bash
finclaw report --input <results.json> --format <html|pdf>
```

---

### `portfolio` — Portfolio Analysis

Optimize portfolio allocation across tickers.

```bash
finclaw portfolio --tickers <symbols> --method <method>
```

| Option | Values |
|---|---|
| `--method` | `equal_weight`, `risk_parity`, `mean_variance`, `min_variance` |

---

### `risk` — Risk Analysis

Run risk analysis on a portfolio.

```bash
finclaw risk --portfolio <portfolio.json>
```

---

### `screen` — Stock Screener

Screen stocks by technical and fundamental criteria.

```bash
finclaw screen --market us --rsi-below 30 --min-volume 1000000
```

---

### `cache` — Cache Management

```bash
finclaw cache --stats    # Show cache statistics
finclaw cache --clear    # Clear all cached data
```

---

### `info` — System Information

Display FinClaw version, installed features, and system info.

```bash
finclaw info
```

---

### `paper` — Paper Trading

Start paper trading simulation.

```bash
finclaw paper --strategy momentum --ticker BTCUSDT --exchange binance --capital 10000
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `BINANCE_API_KEY` | Binance API key |
| `BINANCE_API_SECRET` | Binance API secret |
| `BYBIT_API_KEY` | Bybit API key |
| `BYBIT_API_SECRET` | Bybit API secret |
| `OKX_API_KEY` | OKX API key |
| `OKX_API_SECRET` | OKX API secret |
| `OKX_PASSPHRASE` | OKX passphrase |
| `POLYGON_API_KEY` | Polygon.io API key |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key |
| `TUSHARE_TOKEN` | Tushare token |
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_SECRET_KEY` | Alpaca secret key |
| `FINCLAW_API_KEY` | REST API authentication key |
| `FINCLAW_RATE_LIMIT` | API rate limit (requests/min) |
