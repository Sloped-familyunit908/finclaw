# awesome-mcp-servers PR Content

## Target Repository

https://github.com/punkpeye/awesome-mcp-servers

## PR Title

Add FinClaw MCP Server (Finance & Fintech)

## Category

Finance & Fintech (existing category in the repo)

## Entry to Add

Add the following line under the `Finance & Fintech` section, in alphabetical order:

```markdown
- [FinClaw](https://github.com/NeuZhou/finclaw) 🐍 ☁️ 🏠 🍎 🪟 🐧 - AI-native quantitative finance engine with 10 MCP tools: real-time quotes, OHLCV history, technical indicators, stock screening, portfolio analysis, backtesting, sentiment analysis, and multi-exchange support. Features a genetic algorithm that evolves trading strategies across 41 factor dimensions 24/7. `pip install finclaw-ai && finclaw mcp serve`
```

## PR Description

```
Add FinClaw MCP Server to Finance & Fintech category.

FinClaw is an open-source (MIT) quantitative finance engine that exposes 10 MCP tools:

- `get_quote` - Real-time stock/crypto quotes
- `get_history` - OHLCV historical data
- `get_indicators` - Technical analysis indicators
- `screen_stocks` - Multi-factor stock screening
- `analyze_portfolio` - Portfolio analysis and optimization
- `run_backtest` - Strategy backtesting with walk-forward validation
- `get_sentiment` - Market sentiment analysis
- `compare_strategies` - Strategy comparison
- `list_exchanges` - Supported exchange listing
- `get_funding_rates` - Crypto funding rate data

Supports US stocks, crypto (Binance, Bybit, OKX), and Chinese A-shares.
Built with Python 3.9+. Zero API keys needed for basic usage.

GitHub: https://github.com/NeuZhou/finclaw
PyPI: https://pypi.org/project/finclaw-ai/
```

## Installation Verification

```bash
pip install finclaw-ai
finclaw mcp serve
```

## MCP Client Configuration

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
