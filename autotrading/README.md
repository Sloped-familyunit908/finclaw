# AutoTrading

Autonomous AI trading strategy research, inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch).

Give an AI agent a backtesting framework and let it experiment autonomously. It modifies the strategy code, backtests for 5 minutes, checks if fitness improved, keeps or discards, and repeats. You wake up to a log of experiments and (hopefully) a better strategy.

## How it works

The core idea: you're not writing trading strategies. Instead, you're programming the `program.md` that guides an AI agent to do the research for you.

Three files:

- `evaluate.py` — fixed backtesting evaluation (not modified by the agent)
- `strategy.py` — the strategy file the agent edits (architecture, signals, parameters)
- `program.md` — instructions for the AI agent

## Quick Start

1. Make sure finclaw data is ready: `python scripts/download_a_shares.py`
2. Point your AI agent (Claude Code, Cursor, OpenClaw) at `program.md`
3. Let it run overnight
4. Wake up to `results.tsv` with experiment logs

## Metrics

- `fitness` — combined score (higher is better): annual_return / max_drawdown * sharpe
- `annual_return` — annualized return percentage
- `max_drawdown` — maximum peak-to-trough decline
- `sharpe` — risk-adjusted return
- `win_rate` — percentage of profitable trades
- `trades` — total number of trades (must be > 20 to be valid)
