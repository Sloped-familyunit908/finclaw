# Strategy Evolution Engine

FinClaw includes a self-improving **evolution engine** that automatically optimizes trading strategies through iterative mutation and evaluation. Inspired by evolutionary algorithms, it evolves your YAML strategy definitions to find better parameters and rule combinations.

---

## How It Works

The evolution loop follows these steps:

1. **Seed** — Evaluate the initial strategy and add it to the frontier
2. **Select** — Pick the best strategy from the frontier as a parent
3. **Analyze** — Identify weaknesses (losing trades, poor risk metrics)
4. **Propose** — Generate mutation proposals (parameter tweaks, rule changes)
5. **Mutate** — Apply the best proposal to create a child strategy
6. **Evaluate** — Backtest the mutated child strategy
7. **Update** — Accept the child if it outperforms the worst in the frontier
8. **Repeat** — Continue until `max_generations` or early-stop

---

## Quick Start

### CLI

```bash
# Evolve a strategy YAML with default settings
finclaw evolve my_strategy.yaml --symbol AAPL --generations 20

# With custom parameters
finclaw evolve my_strategy.yaml \
  --symbol NVDA \
  --generations 50 \
  --frontier-size 5 \
  --start 2022-01-01
```

### Python API

```python
from src.evolution.engine import EvolutionEngine, EvolutionConfig
from src.strategy.expression import OHLCVData

# Load your OHLCV data
data = OHLCVData(dates=dates, opens=opens, highs=highs,
                 lows=lows, closes=closes, volumes=volumes)

# Read your seed strategy
with open("strategies/builtin/golden-cross-momentum.yaml") as f:
    seed = f.read()

# Configure and run
config = EvolutionConfig(
    max_generations=20,     # Max iterations
    frontier_size=3,        # Keep top-N strategies
    no_improvement_limit=5, # Stop after N stale generations
)
engine = EvolutionEngine(config=config)

result = engine.run(seed, data)

print(f"Best score: {result['best_score'].composite():.4f}")
print(f"Generations: {result['generations_run']}")
print(f"Best strategy:\n{result['best_strategy']}")
```

---

## Components

### EvolutionConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_generations` | int | 10 | Maximum evolution iterations |
| `frontier_size` | int | 3 | Number of top strategies to retain |
| `no_improvement_limit` | int | 5 | Early stop after N generations without improvement |

### Evaluator

Backtests strategies and returns a `FitnessScore` with metrics like return, Sharpe ratio, max drawdown, and win rate.

```python
from src.evolution.evaluator import Evaluator, FitnessScore

evaluator = Evaluator()
score: FitnessScore = evaluator.evaluate(strategy_yaml, data)
print(score.composite())  # Weighted fitness score
```

### Proposer

Analyzes strategy failures and proposes targeted mutations:

```python
from src.evolution.proposer import Proposer

proposer = Proposer()
analyses = proposer.analyze(strategy_yaml, feedback)
proposals = proposer.propose(strategy_yaml, analyses)
```

### Mutator

Applies proposed changes to strategy YAML:

```python
from src.evolution.mutator import Mutator

mutator = Mutator()
new_yaml = mutator.mutate(parent_yaml, proposal, feedback=feedback)
```

### Frontier

Maintains a sorted set of the best strategies discovered:

```python
from src.evolution.frontier import Frontier

frontier = Frontier(max_size=5)
entry = frontier.update(strategy_yaml, score, generation=1)
best = frontier.best
parent = frontier.select_parent(strategy="best")
```

---

## Callbacks

Track progress with the `on_generation` callback:

```python
def progress(gen: int, score, strategy_yaml: str):
    print(f"Gen {gen}: score={score.composite():.4f}")

result = engine.run(seed, data, on_generation=progress)
```

---

## Tips

- **Start simple** — Use a well-tested seed strategy; evolution refines, it doesn't create from scratch
- **Sufficient data** — Provide at least 1–2 years of daily data for meaningful evaluations
- **Frontier size** — Larger frontiers maintain diversity but slow convergence
- **Monitor overfitting** — Compare evolved strategy on out-of-sample data after evolution
