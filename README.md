[English](README.md) | [??](README.zh-CN.md) | [???](README.ko.md) | [???](README.ja.md)

# FinClaw 🦀

**Self-Evolving Trading Intelligence — genetic algorithms discover strategies you never would.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/NeuZhou/finclaw"><img src="https://codecov.io/gh/NeuZhou/finclaw/graph/badge.svg" alt="codecov"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-484-orange" alt="484 Factors">
  <img src="https://img.shields.io/badge/tests-4900%2B-brightgreen" alt="4900+ Tests">
  <img src="https://img.shields.io/badge/markets-crypto%20%7C%20A--shares%20%7C%20US-ff69b4" alt="Crypto + A-shares + US">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <img src="assets/hero-finclaw.png" alt="FinClaw — Self-Evolving Trading Intelligence" width="800">
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=Y3wY9rj0PmE">
    <img src="https://img.youtube.com/vi/Y3wY9rj0PmE/maxresdefault.jpg" alt="FinClaw Demo Video" width="600">
  </a>
  <br>
  <em>▶️ Watch: How FinClaw's Self-Evolving Engine Works (2 min)</em>
</p>

> FinClaw doesn't need you to write strategies — its genetic algorithm **discovers and evolves them autonomously** across 484 factor dimensions, then validates them with walk-forward testing and Monte Carlo simulation.

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results. Always paper trade first.

---

## 🚀 Quick Start

```bash
pip install finclaw-ai
finclaw demo          # See it in action
finclaw quote AAPL    # Real-time quotes
finclaw quote BTC/USDT # Crypto too
```

No API keys, no exchange accounts, no config files needed.

---

<details>
<summary>?? See it in action (click to expand)</summary>

```
$ finclaw demo

??? ?? Real-Time Quotes ???

Symbol        Price     Change        %          Trend
--------------------------------------------------------
AAPL         189.84    +2.31  +1.23%  ???????_??█??
NVDA         875.28   +15.67  +1.82%  ?????_?????__
BTC/USDT  66,458.10    -1.24  -0.53%  ????__???_???

??? ?? Strategy Evolution Engine ???

FinClaw's core: genetic algorithms evolve strategies autonomously.
Population: 30  |  484 factor dimensions  |  Walk-forward validated

  Gen    Return    Fitness   Sharpe  Progress
  ---    ------    -------   ------  --------
    1     12.3%       45.2     1.2   ██████████
   10     34.5%      123.7     2.1   ██████████
   25     89.2%      456.3     3.4   ██████████
   50    234.7%     1205.8     4.8   ██████████
   75    567.3%     2890.4     5.6   ██████████
   89   2756.4%     4487.8     6.6   ██████████ ??

DNA evolved across 484 factors:
  Top weights: RSI ?0.34, Momentum ?0.25, MACD ?0.18, Volume ?0.12
  Walk-forward validated: ?  Monte Carlo robust: ?

??? ?? Backtest Results ???

Strategy:  +75.7%  (+32.5%/yr)    Buy&Hold:  +67.7%
Alpha:     +8.0%                  Sharpe:    1.85
MaxDD:     -8.3%                  Win Rate:  63%

??? ?? Paper Trading Portfolio ???

Symbol     Shares   Avg Cost      Price         P&L
----------------------------------------------------
AAPL           50     178.50     189.84  +$5,650.00
NVDA           20     810.00     875.28  +$1,305.60
BTC/USDT    0.015  66,458.00  66,458.00      $0.00
----------------------------------------------------
TOTAL                                   +$6,955.60

??? ?? AI Features ???

MCP Server  ? Expose FinClaw as tools for Claude, Cursor, VS Code
Copilot     ? Interactive AI financial assistant
Strategy AI ? Natural language ? trading code

Try it yourself:
  finclaw evolve --market crypto    # Run strategy evolution
  finclaw quote BTC/USDT            # Live crypto quote
  finclaw analyze TSLA              # Technical analysis
  finclaw copilot                   # AI financial chat
```

</details>

---

## Why FinClaw?

Most quant tools make **you** write the strategy. FinClaw evolves strategies **for you**.

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| Strategy design | GA evolves 484-dim DNA | You write rules | You write rules | DRL trains agent |
| Continuous evolution | **Strategy itself evolves** | Bot runs, strategy fixed | Bot runs, strategy fixed | Training offline |
| Walk-forward validation | ✅ Built-in (70/30 + Monte Carlo) | ❌ Plugin needed | ❌ Plugin needed | ⚠️ Partial |
| Anti-overfitting | Arena + bias detection | Basic cross-validation | Basic | Varies |
| Zero API keys to start | ✅ `pip install && finclaw demo` | ❌ Needs exchange keys | ❌ Needs keys | ❌ Needs data setup |
| Market coverage | Crypto + A-shares + US | Crypto only | Crypto only | A-shares (Qlib) |
| MCP server (AI agents) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| Factor library | 484 factors, auto-weighted | ~50 manual indicators | Manual indicators | Alpha158 (Qlib) |

---

## 📊 484 Factor Dimensions

284 general factors + 200 crypto-native factors, organized by category:

| Category | Count | Examples |
|----------|-------|----------|
| Crypto-Native | 200 | Funding rate proxy, session effects, whale detection, liquidation cascade |
| Momentum | 14 | ROC, acceleration, trend strength, quality momentum |
| Volume & Flow | 13 | OBV, smart money, volume-price divergence, Wyckoff VSA |
| Volatility | 13 | ATR, Bollinger squeeze, regime detection, vol-of-vol |
| Mean Reversion | 12 | Z-score, rubber band, Keltner channel position |
| Trend Following | 14 | ADX, EMA golden cross, higher-highs/higher-lows, MA fan |
| Qlib Alpha158 | 11 | KMID, KSFT, CNTD, CORD, SUMP (Microsoft Qlib compatible) |
| Quality Filter | 11 | Earnings momentum proxy, relative strength, resilience |
| Risk Warning | 11 | Consecutive losses, death cross, gap-down, limit-down |
| Top Escape | 10 | Distribution detection, climax volume, smart money exit |
| Price Structure | 10 | Candlestick patterns, support/resistance, pivot points |
| Davis Double Play | 8 | Revenue acceleration, tech moat, supply exhaustion |
| Gap Analysis | 8 | Gap fill, gap momentum, gap reversal |
| Market Breadth | 5 | Advance/decline, sector rotation, new highs/lows |
| News Sentiment | 2 | EN/ZH keyword sentiment score + momentum |
| DRL Signal | 2 | Q-learning buy probability + state value estimate |

> **Design principle**: Technical, sentiment, DRL, fundamental — all signals are unified as factors returning `[0, 1]`. Weights are determined by the evolution engine, eliminating human bias from signal synthesis.

---

## 🧬 Self-Evolution Engine

The genetic algorithm continuously discovers optimal strategies:

1. **Seed** — Initialize population with diverse factor weight configurations
2. **Evaluate** — Walk-forward backtest each DNA across all assets
3. **Select** — Keep top performers by fitness (Sharpe × Return / MaxDrawdown)
4. **Mutate** — Random weight perturbation, crossover, factor add/drop
5. **Repeat** — Runs 7×24 on your machine

```bash
finclaw evolve --market crypto --generations 50   # Crypto (main use case)
finclaw evolve --market cn --generations 50       # A-shares
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### Evolution Results

| Market | Generation | Annual Return | Sharpe | Max Drawdown |
|--------|-----------|--------------|--------|-------------|
| A-Shares | Gen 89 | 2,756% | 6.56 | 26.5% |
| Crypto | Gen 19 | 16,066% | 12.19 | 7.2% |

> ⚠️ These are **in-sample** backtest results on historical data. Real performance will be significantly lower. Walk-forward out-of-sample validation is enabled by default — always check OOS metrics before trusting any evolved strategy. Run `finclaw check-backtest` to verify, and `finclaw paper` to paper trade before risking real capital.

---

## 🏟️ Arena Mode (Anti-Overfitting)

Traditional backtests evaluate each strategy in isolation — overfitted strategies look great on history but fail live. FinClaw's **Arena Mode** fixes this:

- Multiple DNA strategies trade simultaneously in the same simulated market
- **Crowding penalty**: When >50% of DNAs buy on the same signal, price impact kicks in
- Overfitted strategies that only work in isolation get penalized in Arena rankings

---

## ✅ Quality Assurance

- Walk-forward validation (70/30 train/test split)
- Monte Carlo simulation (1,000 iterations, p-value < 0.05)
- Bootstrap 95% confidence intervals
- Arena competition (multi-DNA market simulation)
- Bias detection (look-ahead, snooping, survivorship)
- Factor IC/IR analysis with decay curves
- Factor orthogonal matrix (auto-remove redundant factors)
- Turnover penalty in fitness function
- 4,900+ automated tests

---

## 💻 CLI Reference

FinClaw ships with 170+ CLI commands. Here are the essentials:

| Command | Description |
|---------|-------------|
| `finclaw demo` | See all features in action |
| `finclaw quote AAPL` | Real-time US stock quote |
| `finclaw quote BTC/USDT` | Crypto quote via ccxt |
| `finclaw evolve --market crypto` | Run genetic algorithm evolution |
| `finclaw backtest -t AAPL` | Backtest a strategy on a stock |
| `finclaw check-backtest` | Verify backtest results |
| `finclaw analyze TSLA` | Technical analysis |
| `finclaw screen` | Stock screener |
| `finclaw risk-report` | Portfolio risk report |
| `finclaw sentiment` | Market sentiment |
| `finclaw copilot` | AI financial assistant |
| `finclaw generate-strategy` | Natural language → strategy code |
| `finclaw mcp serve` | Start MCP server for AI agents |
| `finclaw paper` | Paper trading mode |
| `finclaw doctor` | Environment check |

Run `finclaw --help` for the full list.

---

## 🤖 MCP Server (AI Agents)

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

Provides 10 tools: `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`.

---

## 📡 Data Sources

| Market | Source | API Key Required? |
|--------|--------|-----------------|
| Crypto | ccxt (100+ exchanges) | No (public data) |
| US Stocks | Yahoo Finance | No |
| A-Shares | AKShare + BaoStock | No |
| News Sentiment | CryptoCompare + AKShare | No |

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
│   Technical(284) │ Sentiment │ DRL │ Davis │ Crypto(200)│
│       All → compute() → [0, 1]                        │
├──────────────────────────────────────────────────────┤
│   Arena Competition │ Bias Detection │ Monte Carlo     │
├──────────────────────────────────────────────────────┤
│   Paper Trading → Live Trading → 100+ Exchanges       │
└──────────────────────────────────────────────────────┘
```

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

## 🌐 Ecosystem

FinClaw is part of the NeuZhou AI agent toolkit:

| Project | Description |
|---------|-------------|
| **[FinClaw](https://github.com/NeuZhou/finclaw)** | AI-native quantitative finance engine |
| **[ClawGuard](https://github.com/NeuZhou/clawguard)** | AI Agent Immune System — 285+ threat patterns, zero dependencies |
| **[AgentProbe](https://github.com/NeuZhou/agentprobe)** | Playwright for AI Agents — test, record, replay agent behaviors |

---

## Contributing

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]" && pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. [Report bugs](https://github.com/NeuZhou/finclaw/issues) · [Request features](https://github.com/NeuZhou/finclaw/issues)

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
