# MCP Server

FinClaw implements the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), enabling AI assistants to use FinClaw as a tool for financial analysis.

---

## Available MCP Tools

| Tool | Description |
|---|---|
| `get_quote` | Real-time quote for any symbol from any exchange |
| `get_history` | OHLCV candle history |
| `list_exchanges` | List all available exchange adapters |
| `run_backtest` | Run a strategy backtest |
| `analyze_portfolio` | Portfolio analysis with risk metrics |
| `get_indicators` | Calculate technical indicators (SMA, RSI, MACD, BBands) |
| `screen_stocks` | Screen stocks by technical criteria |
| `get_sentiment` | Market sentiment analysis |
| `compare_strategies` | Compare multiple strategies |
| `get_funding_rates` | Crypto perpetual futures funding rates |

---

## Setup: Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "python",
      "args": ["-m", "src.mcp"],
      "cwd": "/path/to/finclaw"
    }
  }
}
```

**Config file locations:**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Restart Claude Desktop after saving. You'll see FinClaw tools in the tool picker.

---

## Setup: Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "python",
      "args": ["-m", "src.mcp"],
      "cwd": "/path/to/finclaw"
    }
  }
}
```

---

## Setup: OpenClaw

Add to your OpenClaw skill or workspace config:

```yaml
mcp:
  finclaw:
    command: python
    args: ["-m", "src.mcp"]
    cwd: /path/to/finclaw
```

Or install the finclaw skill which auto-configures MCP:

```bash
clawhub install finclaw
```

---

## Setup: VS Code

Add to your VS Code `settings.json`:

```json
{
  "mcp.servers": {
    "finclaw": {
      "command": "python",
      "args": ["-m", "src.mcp"],
      "cwd": "/path/to/finclaw"
    }
  }
}
```

---

## Usage Examples

Once connected, ask your AI assistant:

- *"Get me a quote for NVDA"*
- *"Backtest momentum strategy on AAPL from 2020 to 2025"*
- *"Calculate RSI and MACD for BTCUSDT"*
- *"Compare momentum vs mean_reversion on MSFT,GOOGL"*
- *"Screen these stocks for RSI below 30: AAPL,MSFT,GOOGL,AMZN,META"*
- *"What are the current funding rates for BTCUSDT and ETHUSDT on Binance?"*
- *"Analyze my portfolio: 100 shares AAPL at $150, 50 shares MSFT at $300"*

---

## Running the MCP Server Manually

```bash
# Default: stdio transport
python -m src.mcp

# The server communicates via JSON-RPC over stdin/stdout
# Protocol version: 2024-11-05
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| "Module not found" | Ensure FinClaw is installed: `pip install -e .` from the repo root |
| Tools not appearing | Restart your AI client after config change |
| Timeout on backtest | Backtests can be slow — increase client timeout or reduce date range |
| Exchange errors | Set required API key environment variables |
