<h1 align="center">🦀 FinClaw</h1>

<p align="center">
  <strong>AI-powered quantitative finance in your terminal</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/finclaw/"><img src="https://img.shields.io/pypi/v/finclaw?color=blue" alt="PyPI"></a>
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
pip install finclaw
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
| Paper trading | ✅ | ❌ | ✅ | ✅ |
| Backtesting | ✅ | ✅ | ✅ | ✅ |
| Multi-exchange | ✅ | ❌ | ❌ | ✅ |
| Strategy plugins | ✅ | ✅ | ❌ | ✅ |
| No heavy deps (pure NumPy) | ✅ | ❌ | ❌ | ❌ |
| Crypto + Stocks | ✅ | ✅ | ❌ | ✅* |
| Terminal charts | ✅ | ❌ | ❌ | ❌ |
| YAML strategy DSL | ✅ | ❌ | ❌ | ❌ |

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
```

Compatible with **Backtrader** strategies, **TA-Lib** indicators, and simple **Pine Script**.

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

---

## Architecture

```
┌────────────────────────────────────────┐
│           User Interfaces              │
│  CLI  │  MCP Server  │  Copilot  │ API │
├────────────────────────────────────────┤
│         AI Strategy Engine             │
│  Generator │ Optimizer │ Copilot Chat  │
├────────────────────────────────────────┤
│          Strategy Layer                │
│   Built-in (20+)  │  Plugins │  YAML  │
├────────────────────────────────────────┤
│   Backtester  │  Paper Trading Engine  │
├────────────────────────────────────────┤
│             Data Layer                 │
│  Yahoo Finance │ Binance WS │  Cache   │
└────────────────────────────────────────┘
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
