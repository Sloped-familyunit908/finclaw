# Your Backtest Is Lying to You — Walk-Forward Validation Catches Overfitting

*This is Part 3 of my series on building [finclaw](https://github.com/NeuZhou/finclaw), an AI-native quant engine. Previously: [Why GA Beat DRL](https://dev.to/neuzhou) and [127 Generations Later](https://dev.to/neuzhou).*

---

## 25,000% Annual Return? Sure, Bro.

**Update (2026-03-29):** It turns out the problem was even worse than overfitting. The backtester had a **look-ahead bias** — the scoring function used the current period's indicators (including close/high/low) while entering at the current period's open price. This is equivalent to seeing the future. After fixing the bias, adding slippage, and capping position sizes, the old "champion" DNA produces **-99.56% annual return**. The 25,000% was entirely fake. Walk-forward validation alone wasn't enough — the backtester itself was broken. Lesson: verify your test harness before trusting any test results.

My genetic algorithm evolved a strategy with a fitness score of **291,623** and an annualized return of 25,000%.

On paper, I'd outperform Medallion Fund by a factor of 300. In reality, my GA had memorized the training data like a student who stole the answer key.

Here's the thing — I *knew* it was overfit. You know it's overfit. But how do you **prove** it, systematically, in code? And more importantly, how do you force your evolution engine to stop cheating?

That's what walk-forward validation does.

## The Problem: One Split, One Lie

The standard approach is one static train/test split:

```
|========= TRAIN (70%) =========|==== TEST (30%) ====|
```

Looks reasonable. But here's what actually happens after 50+ generations of genetic evolution:

1. Generation 1: GA explores broadly, test set acts as real validation
2. Generation 20: GA has implicitly learned the test set's characteristics
3. Generation 50: *Both* splits show amazing performance because the GA has found parameters that happen to work on this specific slice of history

A single static split gives you **one data point** about generalization. One. And the GA will find the one set of parameters that threads the needle on exactly that split.

## Walk-Forward Validation: Multiple Lies Are Harder to Tell

Walk-forward validation forces your strategy to prove itself across **multiple unseen time windows**. If it only works on one lucky period, it gets caught.

Here's the anchored walk-forward approach we use:

```
Window 1:
|===== TRAIN =====|~~embargo~~|-- TEST 1 --|
                                            
Window 2:
|========= TRAIN =========|~~embargo~~|-- TEST 2 --|

Window 3:
|============= TRAIN =============|~~embargo~~|-- TEST 3 --|

Window 4:
|================= TRAIN =================|~~embargo~~|-- TEST 4 --|
```

Key ideas:

- **Anchored**: Training always starts from the beginning. Each window gets *more* training data.
- **Non-overlapping test windows**: Each OOS period is unseen data the GA never trains on.
- **Embargo gap**: 48 bars of dead zone between train and test. This prevents indicator lookback leakage — a 60-bar SMA computed at the test boundary would otherwise "see" training data.

The final fitness is an aggregate across all OOS windows. A strategy has to work on multiple time regimes, not just one lucky slice.

## The Implementation

Here's the core config:

```python
@dataclass
class WalkForwardConfig:
    n_windows: int = 4
    min_train_pct: float = 0.40
    test_window_pct: float = 0.10
    embargo_periods: int = 48
    warmup_periods: int = 60
    oos_weight: float = 0.70
    is_weight: float = 0.30
    overfit_penalty_threshold: float = 0.25
    overfit_penalty_factor: float = 0.20
    min_trades_per_window: int = 10
    use_consistency_weighting: bool = True
```

A few things to note:

- **70/30 OOS/IS weighting** — We intentionally weight out-of-sample performance at 70%. The GA should optimize for generalization, not memorization.
- **Minimum trades per window** — A window with <10 trades is statistically meaningless. We discard it.
- **Consistency weighting** — If OOS fitness varies wildly across windows (high coefficient of variation), we penalize it. A consistent 5% return across 4 windows beats one window with 50% and three with -10%.

### Window Computation

Windows are computed back-to-front and then reversed. This ensures the most recent data is always used as a test window:

```python
def compute_windows(self, total_bars: int) -> List[Dict[str, Tuple[int, int]]]:
    cfg = self.config
    usable = total_bars - cfg.warmup_periods
    test_size = int(usable * cfg.test_window_pct)

    windows = []
    for i in range(cfg.n_windows):
        test_end = total_bars - i * test_size
        test_start = test_end - test_size
        train_end = test_start - cfg.embargo_periods
        train_start = cfg.warmup_periods

        # Sanity checks
        if train_end - train_start < cfg.warmup_periods * 2:
            break
        if (train_end - train_start) / usable < cfg.min_train_pct:
            break

        windows.append({
            "train": (train_start, train_end),
            "test": (test_start, test_end),
        })

    windows.reverse()  # chronological order
    return windows
```

### Aggregation with Overfit Detection

The aggregation isn't just "average the OOS scores." We compute an **overfit ratio** (OOS mean / IS mean) and apply a harsh penalty when it drops below 0.25:

```python
# Overfit ratio: how much does OOS underperform IS?
overfit_ratio = aggregated_oos / aggregated_is

if overfit_ratio < cfg.overfit_penalty_threshold:
    fitness *= cfg.overfit_penalty_factor  # 80% penalty
```

An overfit ratio of 0.25 means OOS performance is only 25% of IS performance. That's the GA telling you: "I memorized the training data." And we punish it accordingly.

## The Deflated Sharpe Ratio

Walk-forward validation handles overfitting to specific time periods. But there's another source of overfitting that most quant frameworks ignore: **multiple testing**.

If you test 10,000 strategy variants (which is exactly what a GA does — 200 population × 50 generations = 10,000 trials), some will have a high Sharpe ratio *by pure chance*.

Bailey & López de Prado (2014) formalized this as the **Deflated Sharpe Ratio (DSR)**. It adjusts the observed Sharpe for:

- The number of trials run
- Skewness and kurtosis of returns
- Sample size

```python
def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    # Expected max Sharpe under the null (all strategies have SR=0)
    euler_mascheroni = 0.5772156649
    ln_n = math.log(max(n_trials, 2))
    expected_max_sr = (
        (1.0 - euler_mascheroni / ln_n) * math.sqrt(2.0 * ln_n)
        - euler_mascheroni / math.sqrt(2.0 * ln_n)
    )

    # Standard error adjusted for non-normality
    se_sr = math.sqrt(
        (1.0
         - skew * observed_sharpe
         + ((kurtosis - 1.0) / 4.0) * observed_sharpe ** 2)
        / max(n_observations - 1, 1)
    )

    t_stat = (observed_sharpe - expected_max_sr) / se_sr
    prob = 1.0 / (1.0 + math.exp(-1.7 * t_stat))
    return prob
```

The DSR returns a probability. Below ~0.95 means your observed Sharpe is likely a statistical artifact — a result of how many strategies you tested, not how good your strategy actually is.

We built this directly into finclaw's evolution pipeline. After the GA finishes, the winning strategy's Sharpe is deflated by the total number of individuals evaluated. No more celebrating a Sharpe of 3.0 that came from testing 10,000 variants.

## Before vs. After

Here's what happened when we turned on walk-forward validation:

| Metric | Before (single split) | After (walk-forward) |
|--------|----------------------|---------------------|
| Fitness | 291,623 | Realistic range |
| Annual Return | 25,000% | Actually believable |
| Overfit Ratio | N/A | Computed per run |
| Confidence | "Trust the backtest" | Statistically validated |

**The fitness dropped by orders of magnitude.** And that's exactly what should happen.

A lower fitness score that reflects reality is infinitely more valuable than a sky-high number that reflects memorization. The strategies that survive walk-forward validation are the ones you might actually trust with capital.

## The Overfitting Pipeline

To summarize the full anti-overfitting pipeline in finclaw:

```
Strategy DNA (480 params)
    │
    ├─ Walk-Forward Validation (4 OOS windows)
    │       ├─ 48-period embargo gap
    │       ├─ Consistency weighting across windows
    │       └─ Overfit ratio penalty (OOS/IS < 0.25 → 80% penalty)
    │
    ├─ Deflated Sharpe Ratio
    │       └─ Corrects for population_size × generations trials
    │
    └─ Final fitness = 0.7 × OOS_mean × consistency + 0.3 × IS_mean
```

Every single one of these components is designed to crush strategies that only work on data they've already seen.

## Try It Yourself

The full implementation is at [github.com/NeuZhou/finclaw](https://github.com/NeuZhou/finclaw).

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw
pip install -e .
```

The walk-forward validator is at `src/evolution/walk_forward.py`. You can use it standalone:

```python
from src.evolution.walk_forward import WalkForwardValidator, WalkForwardConfig

cfg = WalkForwardConfig(n_windows=4, embargo_periods=48)
validator = WalkForwardValidator(cfg)

result = validator.validate(run_backtest_fn, total_bars=8760, warmup=60)
print(f"Fitness: {result.final_fitness}")
print(f"Overfit ratio: {result.overfit_ratio:.2f}")
print(f"Likely overfit? {result.is_likely_overfit()}")
```

---

If you're building evolved trading strategies and not using walk-forward validation, your backtest is lying to you. The numbers are too good. They will not hold in live trading.

Start by admitting the problem. Then fix it.

⭐ [Star the repo](https://github.com/NeuZhou/finclaw) if this was useful. Issues and PRs welcome.

*Next in this series: taking walk-forward validated strategies into paper trading and measuring regime adaptation.*
