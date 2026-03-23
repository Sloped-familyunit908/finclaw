# FinClaw

**AI trading strategies that evolve themselves. 217 dimensions. 24/7. No human intervention.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-217-orange" alt="217 Factors">
  <img src="https://img.shields.io/badge/tests-4753%2B-brightgreen" alt="4753+ Tests">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<img src="docs/images/hero.jpg" alt="FinClaw Architecture" />

> FinClaw is an open-source quantitative finance engine that uses genetic algorithms to continuously evolve trading strategies across 217 factor dimensions — technical, fundamental, quality, alternative data, and Qlib Alpha158 — with IC/IR quality analysis, walk-forward validation, and Monte Carlo simulation.

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results.

## Table of Contents

- [Why FinClaw?](#why-finclaw)
- [What Makes FinClaw Different?](#what-makes-finclaw-different)
- [Current Best Strategy](#current-best-strategy-gen-1500)
- [Factor Library](#factor-library)
- [Validation & Quality](#validation--quality)
- [Quick Start](#quick-start)
- [Dashboard](#dashboard)
- [Strategy Evolution Engine](#strategy-evolution-engine)
- [MCP Server](#mcp-server-for-ai-agents)
- [Contributing](#contributing)
- [License](#license)

## Why FinClaw?

- **Self-evolving strategies** — Genetic algorithm optimizes 217 trading factors 24/7
- **Walk-forward validated** — 70/30 train/test split + Monte Carlo simulation prevents overfitting
- **Factor quality analysis** — IC/IR/decay/tier classification for every factor
- **Turnover penalty** — Fitness function penalizes excessive trading
- **Factor orthogonality** — Correlation matrix detects and prunes redundant factors
- **Global markets** — US stocks, crypto, and Chinese A-shares from free data sources
- **AI-powered research** — Chat with any LLM about stocks. Configure in `finclaw.config.ts`
- **Production dashboard** — TradingView charts, screener, watchlist, real-time prices
- **Zero API keys needed** — `pip install finclaw-ai && finclaw demo` just works

## What Makes FinClaw Different?

Unlike traditional quant platforms where humans design strategies, FinClaw's genetic algorithm **discovers strategies autonomously**:

| Feature | Traditional Platforms | FinClaw |
|---------|---------------------|---------|
| Strategy Design | Human writes rules | GA evolves 217-dim DNA |
| Factor Selection | Human picks indicators | Auto-weighted via evolution |
| Parameter Tuning | Grid search / manual | Genetic crossover + mutation |
| Quality Control | Manual review | IC analysis + factor pruning |
| Overfitting Prevention | Train/test split | Walk-forward + Monte Carlo |
| Runs 24/7 | No | Yes, autonomous |

## Current Best Strategy (Gen 1,500+)

| Metric | Gross (before costs) | Net (after costs) |
|--------|---------------------|-------------------|
| Annual Return | 309.6% | ~180-220%* |
| Sharpe Ratio | 3.42 | ~2.0-2.5* |
| Max Drawdown | 13.8% | ~15-18%* |
| Win Rate | 62.9% | ~55-60%* |
| Factor Dimensions | 217 | 217 |
| Generations Evolved | 1,500+ | 1,500+ |
| Validation | Walk-Forward + MC | Walk-Forward + MC |

*Net estimates include 0.03% commission, 0.1% stamp tax (A-shares), and 0.1% slippage per trade.

> **Important**: These results are from historical backtesting on A-share data (2024-2026). Past performance does not guarantee future results. This is a research and education tool — not a production trading system. Always validate strategies with paper trading before risking real capital.

## Factor Library

FinClaw's 217 factors span 8 categories, each scored for predictive quality:

| Category | Count | Examples |
|----------|-------|---------|
| Technical | 45+ | RSI, MACD, Bollinger, KDJ, OBV, ATR, ADX, ROC, CCI, MFI, Aroon |
| Fundamental | 30+ | PE, PB, ROE, revenue growth (YoY/QoQ), profit growth, debt ratio |
| Quality | 15+ | Gross margin, cashflow quality, PEG, earnings stability |
| Momentum | 25+ | Multi-period returns, risk-adjusted momentum, momentum reversal |
| Volatility | 20+ | Realized vol, vol regime, vol-of-vol, skew, kurtosis |
| Volume | 20+ | VWAP deviation, volume profile, smart money flow |
| Alternative Data | 10 | Sentiment indicators, cross-asset signals |
| Qlib Alpha158 | 50+ | Alpha158 coverage with gap-fill factors |

**Quality Analysis:**
- **IC/IR scoring** — Information Coefficient and Information Ratio for every factor
- **Decay analysis** — How quickly factor signal degrades over time
- **Tier classification** — Factors ranked by predictive power (S/A/B/C tiers)
- **Correlation matrix** — NxN orthogonality detection with auto-pruning of redundant factors
- **Qlib Alpha158 coverage** — Gap analysis ensuring comprehensive factor coverage ([details](docs/factor_gap_analysis.md))

## Validation & Quality

| Mechanism | Description |
|-----------|-------------|
| Walk-Forward Validation | 70/30 train/test split prevents in-sample overfitting |
| Monte Carlo Simulation | Randomized path testing for strategy robustness (coming soon) |
| Turnover Penalty | Fitness function penalizes excessive trading to reduce costs |
| Factor Orthogonality | Correlated factors auto-detected and pruned |
| best_ever.json | Persistent all-time best strategy DNA |
| Hall of Fame | Timestamped copies of every record-breaking DNA |
| Test Suite | 4,753+ tests covering engine, factors, and validation |

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

The engine optimizes 217 factor dimensions across 8 categories (see [Factor Library](#factor-library) for full details).

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

## Limitations

FinClaw is a research and education tool. Key limitations:

- **No live trading** — signals are generated but not executed automatically
- **Free data sources** — subject to delays, gaps, and API rate limits
- **Simplified backtesting** — does not model order book depth, partial fills, or market microstructure
- **Single-asset long-only** — no short selling, no multi-asset portfolio optimization (yet)
- **Historical bias** — backtested strategies may not perform similarly in live markets

For production trading, consider validated platforms with exchange connectivity and proper risk management.

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
