# Getting Started

Get FinClaw running and execute your first analysis in under 3 minutes.

---

## Installation

### From PyPI (recommended)

```bash
pip install finclaw-ai
```

### From Source

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
```

### Verify Installation

```bash
finclaw info
```

---

## Prerequisites

- **Python 3.9+**
- **NumPy** (installed automatically)
- **yfinance** (installed automatically — used for market data)
- Internet connection for fetching live data

---

## Your First Quote

Get a real-time stock quote:

```bash
finclaw scan --market us --style buffett
```

This scans the US market using Warren Buffett's quality + value strategy preset, showing top picks ranked by composite score.

### Available Scan Styles

| Style | Description | Risk | Target Return |
|---|---|---|---|
| `druckenmiller` | Top-3 momentum, max conviction | Very High | 20-35% |
| `soros` | AI narrative + momentum, top-5 | High | 25-30% |
| `lynch` | High growth/vol ratio, top-6 | High | 20-27% |
| `buffett` | Quality + dip recovery, top-8 | Medium-High | 20-30% |
| `dalio` | All-weather, risk parity, top-12 | Medium | 15-20% |
| `momentum` | Top-5 by momentum score | High | 20-30% |
| `mean_reversion` | Buy dips, mean reversion | Medium | 12-18% |
| `aggressive` | Top-5 by walk-forward return | High | 25-35% |
| `balanced` | Top-10 grade-weighted | Medium | 10-15% |
| `conservative` | Top-15 low-vol, safe | Low | 8-12% |

---

## Your First Backtest

Backtest NVIDIA over 5 years:

```bash
finclaw backtest --strategy momentum --ticker NVDA --start 2020-01-01 --end 2025-01-01
```

**Output includes:**

- Annualized return & Sharpe ratio
- Max drawdown & win rate
- Walk-forward validation results
- Overfitting detection score

### Quick Backtest with Multiple Tickers

```bash
finclaw backtest --strategy mean_reversion --ticker AAPL,MSFT,GOOGL --start 2022-01-01
```

---

## Your First Signal

Get real-time trading signals for a stock:

```bash
finclaw signal --ticker MSFT --strategy mean_reversion
```

---

## Interactive Mode

Launch the guided interactive REPL:

```bash
python -m src.interactive
```

This walks you through analysis step-by-step — great for learning.

---

## Start the REST API

```bash
python -m src.api.server --port 8080
```

Then open `http://localhost:8080/api/v1/docs` for Swagger UI.

---

## Start the MCP Server

For AI assistant integration (Claude Desktop, Cursor, etc.):

```bash
python -m src.mcp
```

See [MCP Server](mcp-server.md) for full setup.

---

## Available Markets

| Market | Flag | Exchange Adapters |
|---|---|---|
| US Stocks | 🇺🇸 | Yahoo Finance, Polygon, Alpha Vantage |
| China A-Shares | 🇨🇳 | AkShare, BaoStock, Tushare |
| Hong Kong | 🇭🇰 | Yahoo Finance |
| Japan | 🇯🇵 | Yahoo Finance |
| Korea | 🇰🇷 | Yahoo Finance |
| Crypto | 🌐 | Binance, Bybit, OKX, Coinbase, Kraken |

---

## Next Steps

- [Explore all 12 exchanges →](exchanges.md)
- [Learn the 10 built-in strategies →](strategies.md)
- [Deep dive into backtesting →](backtesting.md)
- [Set up paper trading →](live-trading.md)
