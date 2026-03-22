# Show HN: FinClaw -- Self-evolving trading strategies via genetic algorithms (open-source)

https://github.com/NeuZhou/finclaw

FinClaw is an open-source quantitative finance engine (Python, MIT license) that uses genetic algorithms to evolve trading strategies without human intervention.

The core idea: encode a trading strategy as a 41-dimensional vector of factor weights (RSI, MACD, P/E, ROE, etc.), then apply mutation, crossover, and selection to discover optimal configurations. The fitness function uses walk-forward validation (70/30 train/test split) so the genetic algorithm optimizes on out-of-sample performance, not memorized patterns. Monte Carlo simulation adds a second layer of overfitting defense.

After 1,559 generations of continuous evolution, the best discovered strategy achieved 309.6% annual return with a 3.42 Sharpe ratio on out-of-sample A-share data. These are backtested results -- not live trading -- and real-world performance will differ due to slippage and liquidity constraints.

FinClaw also ships as an MCP server with 10 tools (quotes, backtesting, screening, portfolio analysis, sentiment), so you can use it from Claude, Cursor, or any MCP client. Supports US stocks, crypto (Binance/Bybit/OKX), and Chinese A-shares. Zero API keys needed for basic usage.

```
pip install finclaw-ai && finclaw demo
```

Tech stack: Python 3.9+, Next.js dashboard with TradingView, BaoStock/AKShare/Yahoo Finance data, Rust engine in development.

Not financial advice. For research and education only.
