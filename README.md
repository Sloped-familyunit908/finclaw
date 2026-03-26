# FinClaw 🦀

**Self-Evolving Trading Intelligence — genetic algorithms discover strategies you never would.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-484-orange" alt="484 Factors">
  <img src="https://img.shields.io/badge/tests-5600%2B-brightgreen" alt="5600+ Tests">
  <img src="https://img.shields.io/badge/markets-crypto%20%7C%20A--shares%20%7C%20US-ff69b4" alt="Crypto + A-shares + US">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

> FinClaw doesn't need you to write strategies — its genetic algorithm **discovers and evolves them autonomously** across 484 factor dimensions, then validates them with walk-forward testing and Monte Carlo simulation.

<p align="center">
  <img src="assets/demo-evolve.svg" alt="FinClaw Evolution Demo" width="800">
</p>

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results. Always paper trade first.

---

## Quick Start

```bash
pip install -e .

# See everything in action — zero API keys needed
finclaw demo

# Download crypto market data
finclaw download-crypto --coins BTC,ETH,SOL --days 365

# Evolve a crypto strategy with genetic algorithms
finclaw evolve --market crypto --generations 50

# Real-time quotes
finclaw quote BTC/USDT
finclaw quote AAPL
```

That's it. No API keys, no exchange accounts, no config files.

### What You'll See

<details>
<summary><code>finclaw demo</code> — full feature showcase</summary>

```
███████╗██╗███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝██║████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
█████╗  ██║██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
██╔══╝  ██║██║╚██╗██║██║     ██║     ██╔══██║██║███╗██║
██║     ██║██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
AI-Powered Financial Intelligence Engine

🎬 FinClaw Demo — All features, zero config

━━━ 📊 Real-Time Quotes ━━━

Symbol        Price     Change        %                 Trend
────────────────────────────────────────────────────────────
AAPL                 189.84    +2.31  +1.23%  ▇█▇▆▅▅▅▄▄▄▃▃▂▁   ▁▁▁
NVDA                 875.28   +15.67  +1.82%  ▄▄▆▅▅▃▂▂  ▂▃▃▁▄▅▆▅▇▆
TSLA                 175.21    -3.45  -1.93%    ▁▁▁▂▄▄▄▄▄▂▃▃▃▄▃▄▅▇
MSFT                 415.50    +1.02  +0.25%  █▇▇▆▄▅▅▅▅▄▅▄▂▂     ▁

━━━ 🚀 Backtest: Momentum Strategy on AAPL ━━━

Strategy:  +75.7%  (+32.5%/yr)    Buy&Hold:  +67.7%
Alpha:     +8.0%                  Sharpe:    1.85
MaxDD:     -8.3%                  Win Rate:  63%

━━━ 🤖 AI Features ━━━

MCP Server  — Expose FinClaw as tools for Claude, Cursor, VS Code
Copilot     — Interactive AI financial assistant
Strategy AI — Natural language → trading code
```

</details>

<details>
<summary><code>finclaw quote BTC/USDT</code> — real-time crypto quote</summary>

```
BTC/USDT  $68828.00   -3.53%
Bid: 68828.0  Ask: 68828.1  Vol: 455,860,493
```

</details>

<details>
<summary><code>finclaw evolve --market crypto --generations 50</code> — strategy evolution</summary>

```
🧬 Evolution Engine — Crypto Market
  Population: 30  |  Mutation Rate: 0.3  |  Elite: 5

  Gen  1 │ Best: 0.342 │ Avg: 0.118 │ Sharpe: 0.89 │ ░░░░░░░░░░
  Gen  5 │ Best: 0.567 │ Avg: 0.234 │ Sharpe: 1.12 │ ██░░░░░░░░
  Gen 10 │ Best: 0.723 │ Avg: 0.389 │ Sharpe: 1.45 │ ████░░░░░░
  Gen 25 │ Best: 0.891 │ Avg: 0.512 │ Sharpe: 1.87 │ ██████░░░░
  Gen 50 │ Best: 0.934 │ Avg: 0.601 │ Sharpe: 2.14 │ ████████░░

  ✅ Best DNA saved to evolution_results/best_gen50.json
```

</details>

---

## Why FinClaw?

Most quant tools make **you** write the strategy. FinClaw evolves strategies **for you**.

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| Strategy design | GA evolves 484-dim DNA | You write rules | You write rules | DRL trains agent |
| Runs 24/7 | **Strategy itself evolves** | Bot runs, strategy static | Bot runs, strategy static | Training is offline |
| Walk-forward validation | ✅ Built-in (70/30 + Monte Carlo) | ❌ Plugin needed | ❌ Plugin needed | ⚠️ Partial |
| Anti-overfitting | Arena competition + bias detection | Basic cross-validation | Basic | Varies |
| Zero API keys to start | ✅ `pip install && finclaw demo` | ❌ Needs exchange keys | ❌ Needs keys | ❌ Needs data setup |
| Market coverage | Crypto + A-shares + US stocks | Crypto only | Crypto only | A-shares (Qlib) |
| MCP server (AI agents) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| Factor library | 484 factors, auto-weighted | ~50 manual indicators | Manual indicators | Alpha158 (Qlib) |

### What makes FinClaw unique

- **Self-evolving factors** — A genetic algorithm mutates, breeds, and selects strategy DNA across 484 dimensions. No human decides the signal weights — natural selection does.
- **Walk-forward validation** — Every backtest uses a 70/30 train/test split with Monte Carlo simulation (1,000 iterations, p < 0.05). This is what institutional quants use, not simple in-sample backtesting.
- **Multi-market** — Crypto (via ccxt, 100+ exchanges), China A-shares (AKShare + BaoStock), US stocks (Yahoo Finance). One engine, all markets.
- **AI-native** — Ship with an MCP server so Claude, Cursor, and VS Code can query quotes, run backtests, and analyze portfolios natively.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│             Evolution Engine (Core)                   │
│      Genetic Algorithm → Mutate → Backtest → Select   │
│                                                       │
│      Input: 484 factors × weights = DNA               │
│      Output: Walk-forward validated strategy           │
├──────────────────────────────────────────────────────┤
│                 Factor Sources                        │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│   │Technical │ │Sentiment │ │   DRL    │ │ Davis  │ │
│   │  284     │ │  News    │ │Q-learning│ │Double  │ │
│   │ general  │ │ EN / ZH  │ │ signals  │ │ Play   │ │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│        └─────────────┴────────────┴────────────┘      │
│   + 200 crypto-specific factors                       │
│                All → compute() → [0, 1]               │
├──────────────────────────────────────────────────────┤
│               Quality Assurance                       │
│   ┌────────────┐ ┌─────────────┐ ┌────────────────┐  │
│   │   Arena    │ │    Bias     │ │   Walk-Forward │  │
│   │Competition │ │  Detection  │ │   + Monte Carlo│  │
│   └────────────┘ └─────────────┘ └────────────────┘  │
├──────────────────────────────────────────────────────┤
│               Execution Layer                         │
│   Paper Trading → Live Trading → 100+ Exchanges       │
└──────────────────────────────────────────────────────┘
```

---

## Factor Library (484 factors)

284 general factors + 200 crypto-specific factors, organized across categories:

| Category | Count | Examples |
|----------|-------|---------|
| Crypto-Specific | 200 | Funding rate proxy, session effects, whale detection, liquidation cascade |
| Momentum | 14 | ROC, acceleration, trend strength, quality momentum |
| Volume & Flow | 13 | OBV, smart money, volume-price divergence, Wyckoff VSA |
| Volatility | 13 | ATR, Bollinger squeeze, regime detection, vol-of-vol |
| Mean Reversion | 12 | Z-score, rubber band, Keltner position |
| Trend Following | 14 | ADX, EMA golden cross, higher-highs-lows, MA fan |
| Qlib Alpha158 | 11 | KMID, KSFT, CNTD, CORD, SUMP (Microsoft Qlib compatible) |
| Quality Filter | 11 | Earnings momentum proxy, relative strength, resilience |
| Risk Warning | 11 | Consecutive losses, death cross, gap-down, limit-down |
| Top Escape | 10 | Distribution detection, climax volume, smart money exit |
| Price Structure | 10 | Candlestick patterns, support/resistance, pivot points |
| Davis Double Play | 8 | Revenue acceleration, tech moat, supply exhaustion |
| Alpha | 10 | Various alpha factor implementations |
| Gap Analysis | 8 | Gap fill, gap momentum, gap reversal |
| Market Breadth | 5 | Advance-decline, sector rotation, new highs/lows |
| News Sentiment | 2 | EN/ZH keyword sentiment score + momentum |
| DRL Signals | 2 | Q-learning buy probability + state value estimate |
| ... and more | 130 | Fundamental proxy, pullback, bottom confirmation, regime, etc. |

> **Design principle**: Every signal — technical, sentiment, DRL, fundamental — is expressed as a factor returning `[0, 1]`. The evolution engine decides the weight. No human bias in signal mixing.

---

## Evolution Engine

The genetic algorithm continuously discovers optimal strategies:

1. **Seed** — Initialize population with diverse factor weight configurations
2. **Evaluate** — Backtest each DNA with walk-forward validation
3. **Select** — Keep the top performers
4. **Mutate** — Random weight perturbations, crossover, factor addition/removal
5. **Repeat** — Run 24/7 on your machine

```bash
# Crypto (primary use case)
finclaw evolve --market crypto --generations 50

# A-shares
finclaw evolve --market cn --generations 50

# With custom parameters
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### Evolution Results

| Market | Generation | Annual Return | Sharpe | Max Drawdown |
|--------|-----------|---------------|--------|-------------|
| A-Shares | Gen 89 | 2,756% | 6.56 | 26.5% |
| Crypto | Gen 19 | 16,066% | 12.19 | 7.2% |

> ⚠️ **These are in-sample backtest results** on historical data. Real-world performance will be significantly lower. Walk-Forward out-of-sample validation is now enabled by default — always check OOS metrics before trusting any evolved strategy. Use `finclaw check-backtest` to verify results and `finclaw paper` to paper trade before risking real capital.

---

## Arena Mode (Anti-Overfitting)

Traditional backtesting evaluates each strategy in isolation — overfitted strategies score well on historical data but fail live. FinClaw's **Arena Mode** (inspired by [FinEvo](https://arxiv.org)) solves this:

```
┌──────────────────────────────────────────┐
│         Arena: Shared Market Sim          │
│                                           │
│   DNA-1 ──┐                              │
│   DNA-2 ──┤── Same OHLCV data            │
│   DNA-3 ──┤── Same initial capital        │
│   DNA-4 ──┤── Price impact when crowded   │
│   DNA-5 ──┘── Ranked by final P&L        │
│                                           │
│   Overfitted DNA → poor rank → penalized  │
└──────────────────────────────────────────┘
```

- Multiple DNA strategies trade simultaneously in the same simulated market
- **Crowding penalty**: When >50% of DNA strategies buy the same signal, price impact kicks in
- Overfitted strategies that only work in isolation get penalized by arena ranking

---

## Bias Detection

Catch common backtesting pitfalls before trusting results:

```bash
python -m src.evolution.bias_cli --all
```

| Check | What it catches |
|-------|----------------|
| **Look-ahead bias** | Factors that accidentally peek at future data |
| **Data snooping** | DNA that performs 3x+ better on train vs test (overfit) |
| **Survivorship bias** | Assets that delisted during the backtest period |

---

## CLI Reference

FinClaw ships with 70+ subcommands. Here are the essentials:

```bash
# Quotes & Data
finclaw quote AAPL              # US stock quote
finclaw quote BTC/USDT          # Crypto quote (via ccxt)
finclaw history NVDA            # Historical data
finclaw download-crypto         # Download crypto OHLCV data
finclaw exchanges list          # Show supported exchanges

# Evolution & Backtesting
finclaw evolve --market crypto  # Run genetic algorithm evolution
finclaw backtest -t AAPL        # Backtest a strategy on a stock
finclaw check-backtest          # Verify backtest results

# Analysis & Tools
finclaw analyze TSLA            # Technical analysis
finclaw screen                  # Stock screener
finclaw risk-report             # Portfolio risk analysis
finclaw sentiment               # Market sentiment
finclaw demo                    # Full feature demo
finclaw doctor                  # Check your environment

# AI Features
finclaw copilot                 # AI financial assistant
finclaw generate-strategy       # Natural language → strategy
finclaw mcp serve               # MCP server for AI agents

# Paper Trading
finclaw paper                   # Paper trading mode
finclaw paper-report            # Paper trading results
```

Run `finclaw --help` for the full list.

---

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

---

## Data Sources

| Market | Source | API Key Needed? |
|--------|--------|-----------------|
| Cryptocurrency | ccxt (100+ exchanges) | No (public data) |
| US Stocks | Yahoo Finance | No |
| China A-Shares | AKShare + BaoStock | No |
| News Sentiment | CryptoCompare + AKShare | No |

---

## Dashboard

```bash
cd dashboard && npm install && npm run dev
# Open http://localhost:3000
```

- Real-time prices (Crypto, US stocks, A-Shares)
- TradingView professional charts
- Portfolio tracker with live P&L
- Stock screener with filters + CSV export
- AI chat assistant (OpenAI, Anthropic, DeepSeek, Ollama)

---

## Validation & Quality

- Walk-forward validation (70/30 train/test split)
- Monte Carlo simulation (1,000 iterations, p-value < 0.05)
- Bootstrap 95% confidence intervals
- Arena competition (multi-DNA market simulation)
- Bias detection (lookahead, snooping, survivorship)
- Factor IC/IR analysis with decay curves
- Factor orthogonality matrix (auto-prune redundant factors)
- Turnover penalty in fitness function
- 5,600+ automated tests

---

## Roadmap

- [x] 484-factor evolution engine
- [x] Walk-forward validation + Monte Carlo
- [x] Arena competition mode
- [x] Bias detection suite
- [x] News sentiment + DRL factors
- [x] Davis Double Play factors
- [x] Paper trading infrastructure
- [x] MCP server for AI agents
- [ ] DEX execution (Uniswap V3 / Arbitrum)
- [ ] Multi-timeframe support (1h/4h/1d)
- [ ] Foundation model for price sequences

---

## Contributing

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]"
pytest
```

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute:**
- 🐛 [Report bugs](https://github.com/NeuZhou/finclaw/issues)
- 💡 [Request features](https://github.com/NeuZhou/finclaw/issues)
- 🔧 Submit pull requests
- 📝 Improve documentation
- ⭐ Star the repo if you find it useful

---

## Limitations

FinClaw is a research and education tool. Key limitations:

- **Free data sources** — subject to delays, gaps, and API rate limits
- **Simplified backtesting** — does not model order book depth, partial fills, or market microstructure
- **In-sample bias** — evolved strategies may not perform similarly out-of-sample; always check walk-forward OOS results
- **Dry-run first** — always validate strategies with paper trading before risking real capital

For production trading, combine with proper risk management and position sizing.

---

## License

[MIT](LICENSE)

---

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
