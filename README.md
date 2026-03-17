<h1 align="center">🦀 FinClaw</h1>

<p align="center">
  <strong>AI-powered quantitative finance in your terminal</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python"></a>
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="Stars"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/NeuZhou/finclaw/master/docs/demo.gif" alt="FinClaw Demo" width="700">
</p>

```
$ finclaw quote AAPL
  AAPL  $252.82  +2.31 +0.92%
  Bid: 252.82  Ask: 252.83  Vol: 30,091,880

$ finclaw analyze TSLA --indicators rsi,macd,bollinger
  🔬 Technical Analysis: TSLA
  Price: $175.21  |  52w High: $299.29  |  52w Low: $138.80

  RSI(14)        62.4  NEUTRAL     momentum balanced
  MACD          +4.82  BULLISH     histogram expanding
  Bollinger      72%B  NEUTRAL     upper half of band

$ finclaw backtest -t NVDA --start 2023-01-01
  🚀 NVDA | momentum
  Return: +142.3% (+55.2%/yr) | Alpha: +18.7%
  MaxDD: -12.1% | Sharpe: 1.85 | Trades: 47
```

---

## Why FinClaw?

Most quant tools make you configure databases, install heavy dependencies, and write boilerplate before you see your first result. **FinClaw gets you from zero to insight in one command.** Zero API keys needed — it uses Yahoo Finance by default. A pure NumPy core means it installs in seconds, not minutes. And when you're ready for AI-powered strategy generation, MCP agent integration, or multi-exchange live trading — it's all built in.

---

## Quick Start

```bash
pip install finclaw-ai
finclaw demo              # See all features — no API key needed
finclaw quote AAPL        # Real-time stock quote
finclaw copilot           # AI financial assistant
```

---

## Feature Comparison

| Feature | FinClaw | Backtrader | Zipline | Freqtrade |
|---------|:-------:|:----------:|:-------:|:---------:|
| Zero-config install | ✅ | ❌ | ❌ | ❌ |
| CLI interface | ✅ | ❌ | ❌ | ✅ |
| AI strategy generation | ✅ | ❌ | ❌ | ❌ |
| Natural language copilot | ✅ | ❌ | ❌ | ❌ |
| MCP server (AI agents) | ✅ | ❌ | ❌ | ❌ |
| A2A protocol | ✅ | ❌ | ❌ | ❌ |
| Paper trading | ✅ | ❌ | ✅ | ✅ |
| Backtesting | ✅ | ✅ | ✅ | ✅ |
| Multi-exchange (12+) | ✅ | ❌ | ❌ | ✅ |
| Strategy plugins | ✅ | ✅ | ❌ | ✅ |
| No heavy deps (pure NumPy) | ✅ | ❌ | ❌ | ❌ |
| Crypto + Stocks + CN Stocks | ✅ | ✅ | ❌ | ✅* |
| Terminal charts | ✅ | ❌ | ❌ | ❌ |
| YAML strategy DSL | ✅ | ❌ | ❌ | ❌ |
| BTC on-chain metrics | ✅ | ❌ | ❌ | ❌ |
| Funding rate dashboard | ✅ | ❌ | ❌ | ✅ |
| Lightning Network monitor | ✅ | ❌ | ❌ | ❌ |

---

## What You Can Do

### 📊 Quotes & Analysis
```bash
finclaw quote AAPL,MSFT,NVDA        # Multi-ticker quotes
finclaw analyze TSLA --indicators rsi,macd,bollinger,sma50
finclaw chart AAPL --type candle     # Terminal candlestick chart
finclaw news AAPL                    # Financial news
finclaw sentiment TSLA               # Sentiment analysis
```

### 🚀 Backtesting
```bash
finclaw backtest -t AAPL,MSFT --strategy momentum --start 2023-01-01
finclaw backtest -t NVDA --benchmark SPY    # Compare to benchmark
finclaw strategy list                        # 20+ built-in strategies
finclaw strategy backtest trend-following --symbol AAPL
```

### 📋 Paper Trading
```bash
finclaw paper start --balance 100000
finclaw paper buy AAPL 50
finclaw paper sell MSFT 20
finclaw paper dashboard
finclaw paper run-strategy golden-cross --symbols AAPL,MSFT
```

### 🤖 AI Features
```bash
# Generate strategies from plain English or 中文
finclaw generate-strategy "buy when RSI < 30 and MACD golden cross"
finclaw generate-strategy --market crypto --risk high "momentum on volume spike"

# Interactive AI assistant
finclaw copilot
> 分析特斯拉最近走势
> 帮我创建一个均值回归策略

# AI-optimize existing strategies
finclaw optimize-strategy my_strategy.py --data AAPL --period 1y
```

Supports: OpenAI, Anthropic, DeepSeek, Gemini, Ollama (local), Groq, Mistral, Moonshot.

### ⛓️ BTC Metrics & Crypto Tools
```bash
finclaw btc-metrics                  # On-chain dashboard (hashrate, MVRV, miner outflow)
finclaw funding-rates                # Multi-exchange funding rate comparison + arbitrage
finclaw fear-greed --history 7       # Fear & Greed Index with history
```

Features:
- **BTC On-Chain Metrics** — Hashrate, difficulty, mempool, MVRV ratio, miner outflow (via Blockchain.info)
- **Multi-Exchange Funding Dashboard** — Binance, Bybit, OKX funding rates with arbitrage detection
- **Lightning Network Monitor** — Network capacity, node count, channel stats (via 1ML.com)
- **Fear & Greed Index** — Current and historical data (via Alternative.me)
- **Liquidation Tracker** — Track liquidation events across exchanges
- **On-Chain Analytics** — Transaction volume, active addresses

### 🔌 MCP Server (for AI Agents)

Expose FinClaw as tools for Claude, Cursor, VS Code, or OpenClaw:

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

10 MCP tools available: `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`.

### 📈 Strategy Plugin Ecosystem

```bash
# Create a plugin in 5 minutes
finclaw init-strategy my_strategy
cd finclaw-strategy-my_strategy
pip install -e .
finclaw backtest --strategy plugin:my_strategy -t AAPL

# Or use YAML DSL
finclaw strategy create     # Interactive builder
finclaw strategy dsl-backtest my_strategy.yaml --symbol AAPL
finclaw strategy optimize my_strategy.yaml --param rsi_period:10:30:5
```

Compatible with **Backtrader** strategies, **TA-Lib** indicators, and basic **Pine Script**.

### 🌐 12+ Exchange Adapters

**Crypto:** Binance, Bybit, OKX, Coinbase, Kraken (with WebSocket for Binance/Bybit/OKX)
**US Stocks:** Yahoo Finance, Alpaca, Polygon, Alpha Vantage
**CN Stocks:** AkShare, BaoStock, Tushare

```bash
finclaw exchanges list               # See all adapters
finclaw exchanges compare yahoo binance alpaca
finclaw quote BTCUSDT --exchange binance
finclaw history ETHUSDT --exchange bybit --timeframe 1h --limit 50
```

### 🤝 A2A Protocol (Agent-to-Agent)

FinClaw implements the A2A protocol for inter-agent communication:

```bash
finclaw a2a serve --port 8081        # Start A2A server
finclaw a2a card                      # Print agent card
```

---

## Python API

```python
from finclaw import FinClaw

fc = FinClaw()

# Quote
quote = fc.quote("AAPL")
print(f"AAPL: ${quote['price']:.2f} ({quote['change_pct']:+.1f}%)")

# Backtest
result = fc.backtest(strategy="momentum", ticker="NVDA", start="2023-01-01")
print(f"Return: {result.total_return:.1%} | Sharpe: {result.sharpe_ratio:.2f}")
```

Full API documentation: [docs/API.md](docs/API.md)

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│               User Interfaces                     │
│  CLI  │  MCP Server  │  A2A  │  Copilot  │  API  │
├──────────────────────────────────────────────────┤
│           AI Strategy Engine                      │
│  Generator │ Optimizer │ Copilot Chat │ Pine DSL  │
├──────────────────────────────────────────────────┤
│            Strategy Layer                         │
│   Built-in (20+)  │  Plugins  │  YAML DSL        │
├──────────────────────────────────────────────────┤
│   Backtester  │  Paper Trading  │  Risk Engine    │
├──────────────────────────────────────────────────┤
│              Data Layer                           │
│  Yahoo │ Binance WS │ 12+ Exchanges │  Cache      │
├──────────────────────────────────────────────────┤
│            Crypto Layer                           │
│  BTC Metrics │ Funding Rates │ Lightning │ DeFi   │
└──────────────────────────────────────────────────┘
```

---

## Examples

See [`examples/`](examples/) for runnable strategies:

- **[simple_momentum.py](examples/simple_momentum.py)** — SMA + RSI momentum strategy
- **[crypto_rsi.py](examples/crypto_rsi.py)** — Crypto RSI oversold/overbought
- **[ai_generated.py](examples/ai_generated.py)** — BB squeeze mean reversion (AI-generated)

```bash
python examples/simple_momentum.py AAPL
python examples/crypto_rsi.py BTC-USD
python examples/ai_generated.py TSLA
```

---

## Contributing

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE) — Built by [Kang Zhou](https://github.com/NeuZhou)

## 🔗 NeuZhou Ecosystem

FinClaw is part of the NeuZhou open source toolkit for AI agents:

| Project | What it does | Link |
|---------|-------------|------|
| **repo2skill** | Convert any repo into an AI agent skill | [GitHub](https://github.com/NeuZhou/repo2skill) |
| **ClawGuard** | Security scanner for AI agents | [GitHub](https://github.com/NeuZhou/clawguard) |
| **AgentProbe** | Behavioral testing framework for agents | [GitHub](https://github.com/NeuZhou/agentprobe) |
| **FinClaw** | AI-powered financial intelligence engine | *You are here* |

**The workflow:** Generate skills with repo2skill → Scan for vulnerabilities with ClawGuard → Test behavior with AgentProbe → See it in action with FinClaw.
