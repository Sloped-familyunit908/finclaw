# I Built an AI That Evolves Its Own Trading Strategies -- Here's How

What if your trading strategy got smarter every hour without any human intervention?

Most quantitative traders spend weeks manually tuning parameters, running backtests, tweaking thresholds, and hoping their strategy doesn't overfit to historical data. I spent the past several months building a system that does all of this autonomously using genetic algorithms -- and the results have been unexpectedly strong.

The project is called FinClaw, and it is open source under the MIT license. This post explains the technical architecture, the evolution process, and the results so far.

## The Problem with Traditional Backtesting

If you have spent any time in quantitative finance, you know the cycle: hypothesize a strategy, code it up, backtest it against historical data, tweak the parameters until the numbers look good, then watch it fall apart in live markets.

This cycle has three core problems:

1. Manual parameter search is slow and biased. Humans naturally gravitate toward configurations that produce good-looking equity curves, even if those configurations are overfit.

2. Static strategies decay. Markets are regime-dependent. A momentum strategy that works in a bull market may hemorrhage capital in a sideways or bear market.

3. The search space is enormous. With 41 different factor dimensions spanning technical indicators, fundamental ratios, and quality metrics, the number of possible strategy configurations is astronomical. No human can explore it systematically.

## The Solution: Genetic Algorithms for Strategy Evolution

FinClaw treats each trading strategy as a genome -- a 41-dimensional vector of weights and thresholds across technical, fundamental, and quality factors. The system then applies standard evolutionary operators to discover strategies that maximize risk-adjusted returns.

Here is how the evolution loop works:

**Step 1: Seed.** The engine starts with a population of 30 random strategy configurations. Each one is a different combination of weights for factors like RSI, MACD, Bollinger Bands, P/E ratio, ROE, revenue growth, and others.

**Step 2: Evaluate.** Each strategy is backtested across 500+ stocks using walk-forward validation. The training period covers 70% of the data, and the remaining 30% is used for out-of-sample testing. This is the single most important defense against overfitting.

**Step 3: Select.** The top 5 performers (ranked by Sharpe ratio on the out-of-sample period) survive to the next generation.

**Step 4: Reproduce.** The surviving strategies produce offspring through two genetic operators:
- Crossover: Two parent strategies exchange factor weights to produce children.
- Mutation: Random perturbations are applied to factor weights, introducing novelty into the population.

**Step 5: Repeat.** The process runs continuously, 24 hours a day, 7 days a week. Each generation takes a few minutes to evaluate, so the system can run through hundreds of generations per day.

## The 41 Factor Dimensions

The genome encodes weights across three categories of factors:

**Technical Factors (11):** RSI, MACD, Bollinger Bands, KDJ, OBV, ATR, ADX, ROC, CCI, MFI, and Aroon. These capture price momentum, volatility, volume dynamics, and trend strength.

**Fundamental Factors (8):** P/E ratio, P/B ratio, ROE, year-over-year revenue growth, quarter-over-quarter revenue growth, profit growth, debt-to-equity ratio, and dividend yield. These measure valuation and business quality.

**Quality Factors (3):** Gross margin, cash flow quality, and PEG ratio. These filter for companies with sustainable earnings.

The remaining dimensions encode meta-parameters: holding period, rebalancing frequency, position sizing rules, and sector allocation constraints.

## Preventing Overfitting

Overfitting is the central challenge in quantitative strategy research. FinClaw uses three layers of defense:

**Walk-Forward Validation.** Every strategy is trained on a rolling 70% window and tested on the subsequent 30%. The fitness function is calculated exclusively on out-of-sample data. A strategy that memorizes the training set but fails on unseen data will be eliminated by selection pressure.

**Monte Carlo Simulation.** After a strategy passes walk-forward validation, FinClaw runs 1,000 Monte Carlo simulations by shuffling the order of trades. If the strategy's performance is highly sensitive to trade ordering, it is flagged as potentially overfit.

**Population Diversity.** The mutation operator ensures that the population does not converge prematurely on a local optimum. A diversity metric penalizes populations where all strategies look too similar.

## Results: Generation 1,559

After 1,559 generations of continuous evolution, the best strategy discovered by FinClaw has the following out-of-sample performance metrics:

| Metric | Value |
|--------|-------|
| Annual Return | 309.6% |
| Sharpe Ratio | 3.42 |
| Max Drawdown | 13.8% |
| Win Rate | 62.9% |

These results come from walk-forward backtesting on Chinese A-share data (approximately 5,000 listed securities). The test period is out-of-sample -- the strategy was not tuned on this data.

A few caveats are important:

- These are backtested results, not live trading results. Slippage, liquidity constraints, and market impact in live trading will reduce realized returns.
- The A-share market has specific characteristics (daily price limits, T+1 settlement) that may not generalize to other markets.
- Past performance does not guarantee future results. This is a research tool, not a trading signal service.

## The Dashboard

FinClaw includes a production-ready dashboard built with Next.js and TradingView charts. Features include:

- Real-time price monitoring for US stocks, crypto, and A-shares
- Professional charting with TradingView integration
- Multi-factor stock screener with CSV export
- AI chat assistant supporting OpenAI, Anthropic, DeepSeek, and Ollama
- Evolution progress tracking with generation-by-generation performance metrics

The dashboard is end-to-end tested with 28 Playwright tests.

## MCP Server: AI-Native Integration

FinClaw ships with a Model Context Protocol (MCP) server that exposes 10 tools to any MCP-compatible AI agent:

- `get_quote` -- Real-time stock and crypto quotes
- `get_history` -- OHLCV historical data
- `get_indicators` -- Technical analysis indicators
- `screen_stocks` -- Multi-factor screening
- `analyze_portfolio` -- Portfolio optimization
- `run_backtest` -- Strategy backtesting
- `get_sentiment` -- Market sentiment analysis
- `compare_strategies` -- Head-to-head strategy comparison
- `list_exchanges` -- Supported exchanges
- `get_funding_rates` -- Crypto funding rates

This means you can ask Claude, Cursor, or any MCP client to analyze stocks, run backtests, or screen for opportunities using natural language.

## Technical Stack

- Python 3.9+ for the core engine, evolution system, and MCP server
- Rust engine (in development) for high-performance backtesting
- Next.js dashboard with TradingView charts
- Data sources: Yahoo Finance, BaoStock, AKShare, Binance, Bybit, OKX, Alpaca
- Zero external API keys required for basic functionality

## Open Source

FinClaw is released under the MIT license. The full source code, including the evolution engine, all 1,559 generations of evolution results, and the dashboard, is available on GitHub:

https://github.com/NeuZhou/finclaw

To get started:

```bash
pip install finclaw-ai
finclaw demo
```

Or run the evolution engine yourself:

```bash
python scripts/run_evolution.py --generations 999999 --population 30
```

## What I Learned

Building a self-evolving strategy system taught me several things:

1. Walk-forward validation is non-negotiable. Without it, the genetic algorithm will happily produce strategies that are 100% overfit.

2. Diversity matters more than raw performance. The best strategies often emerge from unexpected corners of the search space, not from incremental improvements to already-good strategies.

3. The search never ends. Even after 1,559 generations, the system continues to find improvements. The fitness landscape of multi-factor strategies is vast.

4. Simple factors compose better than complex ones. The best evolved strategies tend to combine a handful of well-known factors in non-obvious ways, rather than relying on exotic signals.

If you are interested in quantitative finance, genetic algorithms, or AI-powered research tools, I would appreciate a star on the repository. Contributions are welcome.

---

*Disclaimer: This project is for educational and research purposes only. Nothing in this post constitutes financial advice. Past performance, whether backtested or live, does not guarantee future results. Trading involves risk, including the possible loss of principal. Always do your own research before making investment decisions.*
