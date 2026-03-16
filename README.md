<h1 align="center">🦀 FinClaw</h1>

<p align="center">
  <strong>The AI-native quantitative finance engine for Python</strong><br>
  <em>From market data to backtesting to live paper trading — in one package.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue&label=PyPI" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/License-AGPL_v3-blue.svg" alt="License: AGPL v3"></a>
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-mcp-server--ai-agents">MCP Server</a> •
  <a href="#-code-examples">Examples</a> •
  <a href="#-comparison">Comparison</a> •
  <a href="docs/README_zh.md">中文</a> •
  <a href="docs/README_ja.md">日本語</a>
</p>

---

## Why FinClaw?

- 🧠 **AI-Native** — Built-in ML pipeline, sentiment analysis, and regime detection. Not bolted-on, built-in.
- ⚡ **Zero Heavy Dependencies** — Pure NumPy core. No TA-Lib, no pandas lock-in, installs in seconds.
- 🔌 **MCP Server** — Expose FinClaw as tools for Claude, Cursor, or any AI agent. This is the future of finance tooling.
- 🏭 **Full Stack** — 12 exchange adapters, 10 strategies, backtesting, paper trading, risk management, REST API — one `pip install`.

---

## 🚀 Quick Start

```bash
pip install finclaw-ai
```

```python
from finclaw import FinClaw

fc = FinClaw()
quote = fc.quote("AAPL")
print(f"AAPL: ${quote.price:.2f} ({quote.change_pct:+.1f}%)")
```

That's it. No API keys needed for basic quotes.

---

## ✨ Features

### 📊 12 Exchange Adapters

Connect to any market. Unified interface, one API.

| Exchange | Type | Real-time WS |
|----------|------|:------------:|
| **Binance** | Crypto | ✅ |
| **OKX** | Crypto | ✅ |
| **Bybit** | Crypto | ✅ |
| **Coinbase** | Crypto | — |
| **Kraken** | Crypto | — |
| **Alpaca** | US Stocks | — |
| **Polygon** | US Stocks | — |
| **Yahoo Finance** | Global | — |
| **Alpha Vantage** | Global | — |
| **Tushare** | China A-shares | — |
| **AKShare** | China A-shares | — |
| **Baostock** | China A-shares | — |

### 🤖 10 Built-in Strategies

Production-ready, YAML-configured, backtested on real data:

- Golden Cross Momentum · RSI Mean Reversion · MACD Divergence
- Bollinger Squeeze · Volume Profile Breakout · Multi-Timeframe Trend
- Grid Trading · DCA Smart · AI Sentiment Reversal · More...

### 📡 Real-time WebSocket Streaming

```python
from src.exchanges import BinanceWS

async with BinanceWS() as ws:
    async for tick in ws.subscribe("BTC/USDT"):
        print(f"BTC: {tick.price}")
```

### 🔌 Plugin System

Extend FinClaw with custom strategies, indicators, and exchange adapters. ABC-based plugin interfaces with discover/load/unload lifecycle.

### 🌐 REST API + MCP Server

- **REST API** — FastAPI server with auth, rate limiting, OpenAPI docs
- **MCP Server** — Expose FinClaw as tools for any AI agent (see below)

### 📈 HTML Reports & Tearsheets

Generate professional backtest reports with equity curves, drawdown analysis, and performance metrics.

### 🛡️ Risk Management & Paper Trading

Position sizing, stop-loss/take-profit, drawdown limits, and a full paper trading engine for strategy validation.

### 🔗 DeFi & On-chain Analysis

DEX data, on-chain metrics, and crypto-native analytics built in.

### 🧠 ML Pipeline

Feature engineering → model selection → prediction tracking. Three built-in models with walk-forward validation and overfitting detection.

---

## 💻 Code Examples

### Get a Quote

```python
from finclaw import FinClaw

fc = FinClaw()
quote = fc.quote("TSLA")
print(f"Tesla: ${quote.price:.2f} | Vol: {quote.volume:,}")
```

### Run a Backtest

```python
from finclaw import FinClaw

fc = FinClaw()
result = fc.backtest(
    strategy="golden-cross-momentum",
    ticker="NVDA",
    start="2020-01-01",
    end="2025-01-01",
)
print(f"Return: {result.total_return:.1%}")
print(f"Sharpe: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.1%}")
result.export_html("nvda_report.html")
```

### Paper Trading (Live Simulation)

```python
from finclaw import FinClaw

fc = FinClaw()
fc.paper_trade(
    strategy="rsi-mean-reversion",
    symbols=["AAPL", "MSFT", "GOOGL"],
    capital=100_000,
)
# Runs continuously, connects to real-time data
# View dashboard at http://localhost:8501
```

---

## 🤖 MCP Server — AI Agents

**This is the killer feature.** FinClaw exposes a [Model Context Protocol](https://modelcontextprotocol.io/) server, turning your quant engine into tools that any AI agent can call.

### With Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "python",
      "args": ["-m", "finclaw", "mcp"],
      "env": {}
    }
  }
}
```

Now Claude can:
- *"Scan the market for oversold stocks using RSI mean reversion"*
- *"Backtest golden cross on NVDA for the last 5 years"*
- *"What's the current macro environment?"*

### With Cursor / OpenClaw

Same MCP protocol — add FinClaw as a tool server and your AI coding assistant becomes a quant analyst.

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `finclaw_scan` | Scan market with any strategy |
| `finclaw_backtest` | Backtest a ticker with strategy |
| `finclaw_macro` | Current macro environment snapshot |
| `finclaw_info` | List available strategies & capabilities |

---

## 📊 Comparison

| Feature | FinClaw | ccxt | freqtrade | backtrader | vnpy |
|---------|:-------:|:----:|:---------:|:----------:|:----:|
| Exchange Adapters | 12 | 100+ | 10+ | — | 40+ |
| Built-in Strategies | ✅ 10 | ❌ | ✅ | ❌ | ❌ |
| ML/AI Pipeline | ✅ | ❌ | ❌ | ❌ | ❌ |
| MCP Server (AI agents) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Backtesting | ✅ | ❌ | ✅ | ✅ | ✅ |
| Paper Trading | ✅ | ❌ | ✅ | ❌ | ✅ |
| REST API | ✅ | ❌ | ✅ | ❌ | ✅ |
| WebSocket Streaming | ✅ | ✅ | ✅ | ❌ | ✅ |
| DeFi/On-chain | ✅ | ❌ | ❌ | ❌ | ❌ |
| Plugin System | ✅ | ❌ | ✅ | ❌ | ✅ |
| Zero Heavy Deps | ✅ | ✅ | ❌ | ❌ | ❌ |
| China A-shares | ✅ | ❌ | ❌ | ❌ | ✅ |

**FinClaw's niche:** The only quant platform with native AI agent integration (MCP), ML pipeline, AND full-stack trading — in a single lightweight package.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Interfaces                    │
│   CLI  ·  REST API  ·  MCP Server  ·  Dashboard     │
├─────────────────────────────────────────────────────┤
│                  Strategy Layer                       │
│   10 Built-in  ·  YAML Config  ·  Plugin System      │
├──────────────┬──────────────┬───────────────────────┤
│  Analysis    │  Execution   │  Risk Management       │
│  17 TA Ind.  │  Paper Trade │  Position Sizing       │
│  3 ML Models │  Live Trade  │  Stop-Loss/TP          │
│  Regime Det. │  Order Route │  Drawdown Limits       │
├──────────────┴──────────────┴───────────────────────┤
│                   Data Layer                         │
│  12 Exchange Adapters  ·  WebSocket  ·  Cache        │
│  Yahoo · Binance · OKX · Tushare · AKShare · ...    │
└─────────────────────────────────────────────────────┘
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
pytest
```

---

## 🌟 Star History

<a href="https://star-history.com/#NeuZhou/finclaw&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
 </picture>
</a>

---

## 📄 License

[AGPL-3.0](LICENSE) — Free for open source. Commercial use requires a license.

---

<p align="center">
  Built with 🦀 by <a href="https://github.com/NeuZhou">Kang Zhou</a><br>
  <sub>If FinClaw saves you time, consider giving it a ⭐</sub>
</p>
