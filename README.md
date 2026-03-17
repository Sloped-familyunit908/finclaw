<h1 align="center">🦀 FinClaw</h1>

<p align="center">
  <strong>AI-native quantitative finance engine for Python</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

---

## What is FinClaw?

FinClaw is a lightweight quantitative finance toolkit with built-in AI agent support via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Get market quotes, run backtests, and paper trade — all from Python or through an AI agent.

**Key highlights:**

- 📊 **Real-time quotes** via Yahoo Finance (no API key needed)
- 🔄 **Backtesting engine** with slippage & commission models
- 📡 **MCP Server** — expose FinClaw as tools for Claude, Cursor, or any AI agent
- 🔌 **WebSocket streaming** from Binance, OKX, Bybit
- 📋 **Strategy library** — YAML-configured, extensible via plugin system
- ⚡ **Zero heavy deps** — pure NumPy core, installs in seconds

---

## Quick Start

```bash
# Install from PyPI
pip install finclaw

# Or install from source
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e .
```

```python
from finclaw import FinClaw

fc = FinClaw()
quote = fc.quote("AAPL")
print(f"AAPL: ${quote['price']:.2f} ({quote['change_pct']:+.1f}%)")
```

### Run a Backtest

```python
result = fc.backtest(strategy="momentum", ticker="NVDA", start="2023-01-01")
print(f"Return: {result.total_return:.1%} | Sharpe: {result.sharpe_ratio:.2f}")
```

### MCP Server (AI Agents)

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

Available MCP tools: `finclaw_scan`, `finclaw_backtest`, `finclaw_macro`, `finclaw_info`.

---

## Features

| Feature | Status |
|---------|--------|
| Yahoo Finance quotes | ✅ |
| Backtesting engine | ✅ |
| Paper trading | ✅ |
| MCP Server | ✅ |
| CLI | ✅ |
| WebSocket streaming (Binance, OKX, Bybit) | ✅ |
| Strategy library (YAML) | ✅ |
| HTML backtest reports | ✅ |
| Plugin system | ✅ |

---

## Architecture

```
┌──────────────────────────────────────┐
│          User Interfaces             │
│   CLI  │  MCP Server  │  Python API  │
├──────────────────────────────────────┤
│         Strategy Layer               │
│   Built-in Strategies  │  Plugins    │
├──────────────────────────────────────┤
│  Backtester  │  Paper Trading Engine │
├──────────────────────────────────────┤
│            Data Layer                │
│  Yahoo Finance │ Binance WS │ Cache  │
└──────────────────────────────────────┘
```

---

## Strategy Plugin Ecosystem

FinClaw features an open strategy plugin system — build, share, and reuse trading strategies across the community.

**Compatible with Backtrader strategies and TA-Lib indicators.**

### Built-in Strategies

| Strategy | Description | Risk | Markets |
|----------|-------------|------|---------|
| `trend_following` | Dual MA crossover + ADX filter | Medium | Stocks, Crypto, Forex |
| `mean_reversion` | RSI + Bollinger Bands | Medium | Stocks, Crypto |
| `momentum_jt` | Jegadeesh-Titman momentum | Medium | Stocks |
| `value_momentum` | Value + momentum factor | Low | Stocks |

### Create Your Own Strategy (5 minutes)

```bash
# Generate scaffold
finclaw init-strategy my_strategy

# Edit your logic
cd finclaw-strategy-my_strategy
# ... edit strategy.py ...

# Install & use
pip install -e .
finclaw plugins list
finclaw backtest --strategy plugin:my_strategy --tickers AAPL
```

### Ecosystem Adapters

- **Backtrader** — Wrap any `bt.Strategy` class (13K+ strategies from the community)
- **TA-Lib** — 150+ technical indicators as signal generators (auto-fallback to pure Python)
- **Pine Script** — Parse simple TradingView strategies (SMA, EMA, RSI, MACD, crossover)

```python
# Backtrader adapter
from src.plugin_system.backtrader_adapter import adapt_backtrader
plugin = adapt_backtrader(MyBTStrategy, name="my_bt")

# TA-Lib signal generator
from src.plugin_system.talib_adapter import talib_strategy
rsi_strat = talib_strategy("rsi", period=14, overbought=70, oversold=30)

# Pine Script
from src.plugin_system.pine_parser import from_pine
plugin = from_pine("""
    fast = ta.sma(close, 10)
    slow = ta.sma(close, 50)
    if ta.crossover(fast, slow)
        strategy.entry("Long", strategy.long)
""", name="pine_cross")
```

### Strategy Registry

```python
from src.plugin_system import StrategyRegistry

registry = StrategyRegistry()
registry.load_all()

# Filter strategies
crypto_strats = registry.filter(market="crypto")
safe_strats = registry.filter(risk_level="low")

# Multi-strategy voting
combined = registry.vote(["trend_following", "mean_reversion"], data, threshold=0.5)
```

### Plugin CLI

```bash
finclaw plugins list                          # List all strategy plugins
finclaw plugins info trend_following          # Show plugin details
finclaw init-strategy my_strategy             # Generate plugin scaffold
finclaw backtest --strategy plugin:golden_cross --tickers AAPL
```

---

## Roadmap

> These features are planned but **not yet implemented**:

- [x] PyPI package (`pip install finclaw`)
- [ ] Docker deployment
- [ ] More exchange adapters (Coinbase, Alpaca, Polygon, China A-shares)
- [ ] REST API server
- [ ] ML pipeline (sentiment, regime detection)
- [ ] DeFi / on-chain analytics
- [ ] Complete API documentation

---

## Contributing

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

[MIT](LICENSE)

---

<p align="center">
  Built by <a href="https://github.com/NeuZhou">Kang Zhou</a>
</p>
