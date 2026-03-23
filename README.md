# FinClaw 🦀

**Self-evolving crypto trading strategies. 217 dimensions. 24/7. No human intervention.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-217-orange" alt="217 Factors">
  <img src="https://img.shields.io/badge/tests-4800%2B-brightgreen" alt="4800+ Tests">
  <img src="https://img.shields.io/badge/exchanges-100%2B-blueviolet" alt="100+ Exchanges">
  <img src="https://img.shields.io/badge/market-crypto%20%7C%20stocks-ff69b4" alt="Crypto + Stocks">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<img src="docs/images/hero.jpg" alt="FinClaw Architecture" />

> While other bots need you to write strategies, FinClaw's genetic algorithm
> **discovers and evolves them autonomously** across 217 factor dimensions.

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results.

## Table of Contents

- [Why FinClaw?](#why-finclaw)
- [Quick Start](#quick-start)
- [What Makes FinClaw Different?](#what-makes-finclaw-different)
- [Supported Exchanges](#supported-exchanges)
- [Factor Library (217 dimensions)](#factor-library-217-dimensions)
- [Validation & Quality](#validation--quality)
- [Dashboard](#dashboard)
- [Strategy Evolution Engine](#strategy-evolution-engine)
- [MCP Server](#mcp-server-for-ai-agents)
- [Data Sources](#data-sources)
- [Contributing](#contributing)
- [License](#license)

## Why FinClaw?

- **Self-evolving strategies** — Genetic algorithm discovers optimal trading factors 24/7
- **217-dimensional DNA** — Technical, fundamental, on-chain, and crypto-specific factors
- **Walk-forward validated** — 70/30 train/test + Monte Carlo simulation
- **Multi-market** — Crypto (primary), A-shares, US stocks
- **Live trading ready** — Dry-run and live modes via ccxt (Binance, OKX, Bybit, etc.)
- **Telegram alerts** — Real-time trade notifications
- **Zero config start** — `pip install finclaw-ai && finclaw demo`

## Quick Start

### Evolve Your First Crypto Strategy

```bash
pip install finclaw-ai

# Download Top 20 crypto data
finclaw download-crypto

# Start 24/7 evolution
finclaw evolve --market crypto --data-dir data/crypto --generations 999999

# Validate results
finclaw validate --results evolution_results/best_ever.json

# Run live (dry-run mode, safe)
finclaw live --market crypto --symbols BTC/USDT ETH/USDT SOL/USDT
```

### CLI Basics

```bash
finclaw demo          # See all features — zero API keys
finclaw quote BTC/USDT   # Real-time crypto quote
finclaw quote AAPL       # Works for stocks too
```

### Dashboard

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw/dashboard
npm install && npm run dev
# Open http://localhost:3000
```

For a detailed crypto walkthrough, see [Crypto Trading: Getting Started](docs/crypto-trading/getting-started.md).

## What Makes FinClaw Different?

Unlike Freqtrade, 3Commas, or traditional quant platforms where humans design strategies, FinClaw's genetic algorithm **discovers strategies autonomously**:

| Feature | Freqtrade / 3Commas | FinClaw |
|---------|---------------------|---------|
| Strategy Design | Human writes rules | GA evolves 217-dim DNA |
| Factor Discovery | Manual indicators | Auto-discovered via evolution |
| Runs 24/7 | Bot runs, strategy static | Strategy itself evolves 24/7 |
| Validation | Basic backtest | Walk-forward + Monte Carlo + IC analysis |
| Market Coverage | Crypto only | Crypto + A-shares + US stocks |

## Supported Exchanges

Via [ccxt](https://github.com/ccxt/ccxt): **Binance**, **OKX**, **Bybit**, Gate.io, Kraken, Coinbase, KuCoin, Bitget, HTX, and **100+ more**.

```bash
# List all supported exchanges
finclaw list-exchanges

# Use a specific exchange
finclaw evolve --market crypto --exchange binance
```

## Factor Library (217 dimensions)

| Category | Count | Examples |
|----------|-------|---------|
| Technical | 45 | RSI, MACD, Bollinger, KDJ, ATR, ADX |
| Price Action | 40 | Candlestick patterns, support/resistance |
| Momentum | 30 | Rate of change, acceleration, trend strength |
| Volume | 25 | OBV, volume profile, smart money flow |
| Fundamental | 20 | PE, PB, ROE (for stocks) |
| Crypto-Specific | 10 | Volume spikes, hourly seasonality, volatility regime |
| Qlib Alpha158 | 11 | KMID, KSFT, CNTD, CORD |
| Alternative | 10 | Fear/greed proxy, capitulation, sector rotation |
| Quality Metrics | 26 | IC/IR analysis, factor decay, orthogonality |

**Quality Analysis:**
- **IC/IR scoring** — Information Coefficient and Information Ratio for every factor
- **Decay analysis** — How quickly factor signal degrades over time
- **Tier classification** — Factors ranked by predictive power (S/A/B/C tiers)
- **Correlation matrix** — NxN orthogonality detection with auto-pruning
- **Qlib Alpha158 coverage** — Gap analysis ensuring comprehensive factor coverage ([details](docs/factor_gap_analysis.md))

## Validation & Quality

- Walk-forward validation (70/30 split)
- Monte Carlo simulation (1000 iterations, p-value < 0.05)
- Bootstrap 95% confidence intervals
- Factor IC/IR analysis with decay curves
- Factor orthogonality matrix (auto-prune redundant factors)
- Turnover penalty in fitness function
- Anti-look-ahead bias verified (32 E2E tests)
- 4800+ automated tests

## Dashboard

<img src="docs/images/dashboard.jpg" alt="FinClaw Dashboard" />

- Real-time prices (Crypto, US stocks, A-Shares)
- TradingView professional charts
- Crypto portfolio tracker with live P&L
- Stock screener with filters + CSV export
- AI chat assistant (OpenAI, Anthropic, DeepSeek, Ollama)
- E2E tested with Playwright (28 tests)

## Strategy Evolution Engine

FinClaw uses a genetic algorithm to continuously discover optimal trading strategies:

1. **Seed** — Start with basic technical indicators
2. **Mutate** — Random parameter variations (30 per generation)
3. **Backtest** — Test each variant across your chosen market
4. **Select** — Keep the top 5 performers
5. **Repeat** — 24/7 on your compute node

The engine optimizes 217 factor dimensions across 8 categories (see [Factor Library](#factor-library-217-dimensions)).

```bash
# Evolve on crypto (primary use case)
finclaw evolve --market crypto --data-dir data/crypto --generations 999999

# Also works on A-shares
finclaw evolve --market cn --data-dir data/a_shares --generations 999999

# US stocks
finclaw evolve --market us --data-dir data/us_stocks --generations 999999
```

## MCP Server (for AI Agents)

Expose FinClaw as tools for Claude, Cursor, VS Code, or any MCP-compatible client:

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "finclaw",
      "args": ["mcp", "serve"]
    }
  }
}
```

10 tools available: `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`.

## Data Sources

| Market | Source | Coverage |
|--------|--------|----------|
| Cryptocurrency | ccxt (100+ exchanges) | BTC, ETH, SOL, and 10,000+ pairs |
| US Stocks | Yahoo Finance | All NYSE/NASDAQ |
| China A-Shares | AKShare + BaoStock | All SSE/SZSE stocks |
| Indices | Yahoo Finance + Sina | S&P 500, Nasdaq, Shanghai Composite |

No API keys required for basic market data.

## Contributing

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Limitations

FinClaw is a research and education tool. Key limitations:

- **Free data sources** — subject to delays, gaps, and API rate limits
- **Simplified backtesting** — does not model order book depth, partial fills, or market microstructure
- **Historical bias** — backtested strategies may not perform similarly in live markets
- **Dry-run first** — always validate strategies with paper trading before risking real capital

For production trading, combine with proper risk management and position sizing.

## License

[MIT](LICENSE)

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
