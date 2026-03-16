# FinClaw Documentation

**AI-Powered Quantitative Finance Platform**

[![PyPI](https://img.shields.io/pypi/v/finclaw-ai?label=PyPI&color=blue)](https://pypi.org/project/finclaw-ai/)
[![License](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

---

## What is FinClaw?

FinClaw is a full-stack quantitative finance engine built on **pure NumPy** — no TA-Lib, no pandas dependency, no heavy framework lock-in. From signal generation to backtesting to paper trading, everything runs in a single Python package.

### Key Highlights

- 🔬 **17 Technical Indicators** — SMA, EMA, RSI, MACD, Bollinger Bands, Ichimoku, and more — all pure NumPy
- 📊 **10 Built-in Strategies** — From beginner-friendly DCA to expert AI-Sentiment Reversal
- 🤖 **AI Agent Debate Arena** — Multiple AI agents debate trade decisions before execution
- 🧪 **Walk-Forward Backtesting** — Monte Carlo simulation, overfitting detection, realistic fills
- 💹 **12 Exchange Adapters** — Binance, Bybit, OKX, Coinbase, Kraken, Yahoo Finance, Polygon, Alpha Vantage, AkShare, BaoStock, Tushare
- 🔌 **MCP Server** — Plug FinClaw into Claude Desktop, Cursor, OpenClaw, or VS Code
- 🌐 **REST API** — Full HTTP API with auth, rate limiting, and Swagger docs
- 📦 **Plugin System** — Extend with custom strategies, indicators, and exchange adapters

### Performance

| Metric | FinClaw Combiner | Buy & Hold (SPY) |
|---|---|---|
| Annualized Return | 29.1% | 14.2% |
| Sharpe Ratio | 1.42 | 0.85 |
| Max Drawdown | -18.3% | -33.9% |
| Win Rate | 58% | - |

> Validated on 100+ tickers across US, China A-shares, and Hong Kong markets.

---

## Quick Navigation

| Section | Description |
|---|---|
| [Getting Started](getting-started.md) | Install and run your first analysis in 3 minutes |
| [Exchanges](exchanges.md) | Setup guides for all 12 supported exchanges |
| [Strategies](strategies.md) | All 10 built-in strategies with parameters |
| [Backtesting](backtesting.md) | Walk-forward analysis, Monte Carlo, overfitting detection |
| [Live Trading](live-trading.md) | Paper trading → live trading guide |
| [MCP Server](mcp-server.md) | Connect FinClaw to AI assistants |
| [REST API](api-server.md) | HTTP API reference with curl examples |
| [Plugins](plugins.md) | Write custom strategies, indicators, exchanges |
| [DeFi](defi.md) | On-chain analysis, DeFi yield tracking |
| [Portfolio](portfolio.md) | Optimization, rebalancing, attribution |
| [Data Pipeline](data-pipeline.md) | Multi-source data with quality checks |
| [CLI Reference](cli-reference.md) | Full command-line reference |
| [FAQ](faq.md) | Common questions and troubleshooting |

---

## Architecture

```
finclaw/
├── src/
│   ├── ta/              # 17 technical indicators (pure NumPy)
│   ├── strategies/      # 8 core strategies + combiner
│   ├── backtesting/     # Walk-forward, Monte Carlo, realistic engine
│   ├── risk/            # Kelly, VaR, position sizing, stop-loss
│   ├── ml/              # ML models, alpha generation, sentiment
│   ├── derivatives/     # Options pricing (BS, binomial, MC)
│   ├── crypto/          # On-chain analytics, rebalancer
│   ├── defi/            # DeFi yield tracking
│   ├── portfolio/       # Tracker, rebalancer, attribution
│   ├── trading/         # Paper trader, OMS
│   ├── exchanges/       # 12 exchange adapters
│   ├── api/             # REST server + webhooks
│   ├── mcp/             # MCP server for AI agents
│   ├── plugins/         # Plugin system
│   ├── pipeline/        # Data pipeline + cache
│   └── ...
├── strategies/builtin/  # YAML strategy definitions
├── tests/               # 1,100+ tests
└── finclaw.py           # CLI entry point
```

## License

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0) — Free for personal and open-source use. Commercial use requires a license.
