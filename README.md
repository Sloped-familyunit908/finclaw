# FinClaw

**AI trading strategies that evolve themselves. 41 dimensions. 24/7. No human intervention.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<img src="docs/images/hero.jpg" alt="FinClaw Architecture" />

> FinClaw is an open-source quantitative finance engine that uses genetic algorithms to continuously evolve trading strategies across 41 factor dimensions — technical, fundamental, and quality — without human intervention.

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results.

## Table of Contents

- [Why FinClaw?](#why-finclaw)
- [Current Best Strategy](#current-best-strategy-gen-1500)
- [Quick Start](#quick-start)
- [Dashboard](#dashboard)
- [Strategy Evolution Engine](#strategy-evolution-engine)
- [MCP Server](#mcp-server-for-ai-agents)
- [Contributing](#contributing)
- [License](#license)

## Why FinClaw?

- **Self-evolving strategies** — Genetic algorithm optimizes 41 trading factors 24/7
- **Walk-forward validated** — 70/30 train/test split + Monte Carlo simulation prevents overfitting
- **Global markets** — US stocks, crypto, and Chinese A-shares from free data sources
- **AI-powered research** — Chat with any LLM about stocks. Configure in `finclaw.config.ts`
- **Production dashboard** — TradingView charts, screener, watchlist, real-time prices
- **Zero API keys needed** — `pip install finclaw-ai && finclaw demo` just works

## Current Best Strategy (Gen 1,500+)

| Metric | Value |
|--------|-------|
| Annual Return | 309.6% |
| Sharpe Ratio | 3.42 |
| Max Drawdown | 13.8% |
| Win Rate | 62.9% |
| Factor Dimensions | 41 |
| Generations Evolved | 1,500+ |

> These results are from walk-forward backtesting on A-share data. Past performance does not guarantee future results. Not financial advice.

## Quick Start

### CLI (no dashboard needed)

```bash
pip install finclaw-ai
finclaw demo          # See all features — zero API keys
finclaw quote AAPL    # Real-time quote
```

### Dashboard

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw/dashboard
npm install && npm run dev
# Open http://localhost:3000
```

## Dashboard

<img src="docs/images/dashboard.jpg" alt="FinClaw Dashboard" />

- Real-time prices (US, Crypto, A-Shares)
- TradingView professional charts
- Stock screener with filters + CSV export
- AI chat assistant (OpenAI, Anthropic, DeepSeek, Ollama)
- E2E tested with Playwright (28 tests)

## Strategy Evolution Engine

FinClaw uses a genetic algorithm to continuously discover optimal trading strategies:

1. **Seed** — Start with basic technical indicators
2. **Mutate** — Random parameter variations (30 per generation)
3. **Backtest** — Test each variant across 500+ stocks
4. **Select** — Keep the top 5 performers
5. **Repeat** — 24/7 on your compute node

The engine optimizes 41 factor dimensions:

| Category | Factors |
|----------|---------|
| Technical | RSI, MACD, Bollinger, KDJ, OBV, ATR, ADX, ROC, CCI, MFI, Aroon |
| Fundamental | PE, PB, ROE, revenue growth (YoY/QoQ), profit growth, debt ratio |
| Quality | Gross margin, cashflow quality, PEG ratio |

```bash
# Start 24/7 evolution
python scripts/run_evolution.py --generations 999999 --population 30
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

FinClaw pulls real-time and historical data from multiple sources:

| Market | Source | Coverage |
|--------|--------|----------|
| US Stocks | Yahoo Finance | All NYSE/NASDAQ |
| Cryptocurrency | ccxt (100+ exchanges) | BTC, ETH, SOL, and 10,000+ pairs |
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

## License

[MIT](LICENSE)

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
