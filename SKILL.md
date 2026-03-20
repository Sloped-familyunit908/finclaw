---
name: finclaw
description: >
  AI-native quantitative finance toolkit for OpenClaw. Use when: querying stock/crypto prices,
  running backtests, scanning stocks (US + China A-shares + Crypto), generating trading strategies
  from natural language, detecting market regimes, or checking backtest plausibility.
  Triggers: stock quote, backtest, trading strategy, market analysis, RSI, MACD, portfolio,
  paper trading, regime detection, A-share scanner, crypto signals, DeFi yields.
  NOT for: general math, non-financial data analysis, or web scraping.
---

# FinClaw 🦀📈

AI-native quantitative finance engine. Zero API keys needed for basic features.

## Install

```bash
pip install finclaw-ai
```

## Core Commands

### Quotes & Analysis
```bash
finclaw quote AAPL              # Stock quote
finclaw quote BTC-USDT          # Crypto quote
finclaw analyze TSLA --indicators rsi,macd,bollinger
finclaw chart AAPL --type candle
```

### Backtesting
```bash
finclaw backtest -t AAPL --strategy momentum --start 2023-01-01
finclaw strategy list           # 20+ built-in strategies
```

### AI Features
```bash
finclaw generate-strategy "buy when RSI < 30 and MACD golden cross"
finclaw copilot                 # Interactive AI assistant
finclaw regime --symbol AAPL    # Market regime detection (stable/volatile/crash)
finclaw check-backtest --sharpe 3.5 --win-rate 0.85  # Overfitting detection
```

### A-Share Scanner (China)
```bash
finclaw scan-cn                 # Scan 322 A-share stocks
finclaw scan-cn --top 10        # Top picks
```

### Crypto
```bash
finclaw crypto signals          # BTC/ETH/SOL RSI signals
finclaw defi scan               # DeFi yield scanner
finclaw defi recommend --budget 2000
```

### Paper Trading
```bash
finclaw paper-report --init     # Initialize $100K portfolio
finclaw paper-report            # Daily report
```

### MCP Server (for AI agents)
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

## Key Differentiators

- **First quant tool with MCP support** — Claude/Cursor can call financial tools directly
- **Natural language → strategy code** — Describe in English/Chinese, get production code
- **Market regime detection** — Auto-adjusts strategy for bull/bear/crash markets
- **12+ exchange adapters** — US stocks, crypto, China A-shares in one tool
- **Economic plausibility checker** — Detects overfitted backtest results

## Supported LLM Providers

OpenAI, Anthropic, DeepSeek, Gemini, Ollama (local), Groq, Mistral, Moonshot.

## Python API

```python
from finclaw import FinClaw
fc = FinClaw()
quote = fc.quote("AAPL")
result = fc.backtest(strategy="momentum", ticker="NVDA", start="2023-01-01")
```
