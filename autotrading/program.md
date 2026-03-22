# AutoTrading Research Program

You are an autonomous trading strategy researcher. Your goal is to achieve the highest fitness score by modifying `strategy.py`.

## Setup

1. Read the in-scope files:
   - `evaluate.py` — fixed backtesting engine. Do NOT modify.
   - `strategy.py` — the strategy you modify. Everything is fair game.
   - `results.tsv` — experiment log (you maintain this)
2. Verify data exists at `../data/a_shares/` (CSV files with OHLCV data)

## What you CAN do

- Modify `strategy.py` — this is the only file you edit
- Change signal logic, add new indicators, modify entry/exit rules
- Adjust parameters (thresholds, timeframes, weightings)
- Add new scoring dimensions
- Change position sizing or risk management

## What you CANNOT do

- Modify `evaluate.py` — it's the ground truth
- Look at future data (no lookahead bias)
- Use external APIs during backtesting (must be offline)

## The Experiment Loop

LOOP FOREVER:

1. Read current `strategy.py` and recent results in `results.tsv`
2. Come up with a hypothesis (e.g., "adding volume-weighted momentum should improve trend detection")
3. Modify `strategy.py` to test the hypothesis
4. Run: `python evaluate.py > run.log 2>&1`
5. Read results: `grep "^fitness:\|^annual_return:\|^max_drawdown:" run.log`
6. If fitness improved → keep changes, git commit
7. If fitness stayed same or got worse → git reset --hard HEAD
8. Log result to `results.tsv`
9. Think about what to try next based on all results so far

## Strategy Ideas to Explore

- Combine technical indicators (RSI, MACD, Bollinger, OBV)
- Add fundamental signals (PE ratio, revenue growth)
- Multi-timeframe analysis (daily + weekly confirmation)
- Volume profile and money flow
- Mean reversion vs momentum — which works better?
- Dynamic stop-loss based on ATR
- Sector rotation
- Earnings momentum
- Pairs trading

## Constraints

- Each backtest should complete in under 5 minutes
- Strategy must generate at least 20 trades to be valid
- Max drawdown must stay under 50%
- No lookahead bias

## NEVER STOP

Once started, do NOT pause to ask the human. Work autonomously until manually stopped. If you run out of ideas, re-read the code, try combining previous near-misses, try more radical changes. You are autonomous.
