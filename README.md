[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md)

# FinClaw 🦀

**Self-Evolving Trading Intelligence — genetic algorithms discover strategies you never would.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/NeuZhou/finclaw"><img src="https://codecov.io/gh/NeuZhou/finclaw/graph/badge.svg" alt="codecov"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-484-orange" alt="484 Factors">
  <img src="https://img.shields.io/badge/tests-5500%2B-brightgreen" alt="5500+ Tests">
  <img src="https://img.shields.io/badge/markets-crypto%20%7C%20A--shares%20%7C%20US-ff69b4" alt="Crypto + A-shares + US">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <img src="assets/hero-finclaw.png" alt="FinClaw — Self-Evolving Trading Intelligence" width="800">
</p>

> FinClaw doesn't need you to write strategies — its genetic algorithm **discovers and evolves them autonomously** across 484 factor dimensions, then validates them with walk-forward testing and Monte Carlo simulation.

## Disclaimer

This project is for **educational and research purposes only**. Not financial advice. Past performance does not guarantee future results. Always paper trade first.

---

## Quick Start

```bash
pip install -e .

# See everything in action — zero API keys needed
finclaw demo

# Real-time quotes
finclaw quote BTC/USDT
finclaw quote AAPL

# Evolve a crypto strategy with genetic algorithms
finclaw evolve --market crypto --generations 50
```

That's it. No API keys, no exchange accounts, no config files.

---

<details>
<summary>📺 See it in action (click to expand)</summary>

```
$ finclaw demo

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
AAPL                 189.84    +2.31  +1.23%  ▃▃▂ ▂▂▂▃▂ ▄▅▅▇█▇▃▄▄▃
NVDA                 875.28   +15.67  +1.82%    ▃▅▄▁▅▆▇█▄▅▆▇▄▄▄▄▅▄
TSLA                 175.21    -3.45  -1.93%  ▅▃▃▃▃▃▄▆▄▄▆▅▆▅▇█▅▃▂ 
MSFT                 415.50    +1.02  +0.25%  ▁▁▂▅▅▄▄▂▃▅▆▆▆▆▇▇▆▃  

━━━ 🚀 Backtest: Momentum Strategy on AAPL ━━━

Strategy:  +75.7%  (+32.5%/yr)    Buy&Hold:  +67.7%
Alpha:     +8.0%                  Sharpe:    1.85
MaxDD:     -8.3%                  Win Rate:  63%

$ finclaw quote AAPL
AAPL  $248.80  +0.81 +0.33%
Bid: 248.8  Ask: 248.8  Vol: 46,525,772

$ finclaw quote BTC/USDT
BTC/USDT  $66827.70   +0.81%
Bid: 66828.9  Ask: 66829.0  Vol: 384,452,226
```

</details>

---

## Why FinClaw?

Most quant tools make **you** write the strategy. FinClaw evolves strategies **for you**.

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| Strategy design | GA evolves 484-dim DNA | You write rules | You write rules | DRL trains agent |
| Walk-forward validation | ✅ Built-in | ❌ Plugin needed | ❌ Plugin needed | ⚠️ Partial |
| Anti-overfitting | Arena + bias detection | Basic cross-validation | Basic | Varies |
| Zero API keys to start | ✅ `pip install && finclaw demo` | ❌ Needs exchange keys | ❌ Needs keys | ❌ Needs data setup |
| Market coverage | Crypto + A-shares + US | Crypto only | Crypto only | A-shares (Qlib) |
| MCP server (AI agents) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| Factor library | 484 factors, auto-weighted | ~50 manual indicators | Manual indicators | Alpha158 (Qlib) |

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

- [x] 484-factor evolution engine with walk-forward + Monte Carlo
- [x] Arena competition mode + bias detection
- [x] News sentiment + DRL + Davis Double Play factors
- [x] Paper trading + MCP server for AI agents
- [ ] DEX execution (Uniswap V3 / Arbitrum)
- [ ] Multi-timeframe support (1h/4h/1d)
- [ ] Foundation model for price sequences

📖 [Full Documentation](docs/) — Factor library, CLI reference, evolution engine details, MCP server setup

---

## 🌐 Ecosystem

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

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
