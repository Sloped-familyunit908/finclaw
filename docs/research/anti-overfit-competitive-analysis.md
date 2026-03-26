# Anti-Overfitting Techniques: Competitive & Academic Analysis

> **Date:** 2026-03-26  
> **Author:** 螃蟹 (automated research)  
> **Purpose:** Inform finclaw's GA evolution framework with proven anti-overfitting techniques from competitors and academia.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Competitor Analysis](#2-competitor-analysis)
   - 2.1 [FreqTrade FreqAI](#21-freqtrade-freqai)
   - 2.2 [Jesse](#22-jesse)
   - 2.3 [QuantConnect / Lean](#23-quantconnect--lean)
   - 2.4 [Microsoft Qlib](#24-microsoft-qlib)
3. [Academic Techniques](#3-academic-techniques)
   - 3.1 [Walk-Forward Validation](#31-walk-forward-validation)
   - 3.2 [Combinatorial Purged Cross-Validation (CPCV)](#32-combinatorial-purged-cross-validation-cpcv)
   - 3.3 [Monte Carlo Permutation Tests](#33-monte-carlo-permutation-tests)
   - 3.4 [Deflated Sharpe Ratio (DSR)](#34-deflated-sharpe-ratio-dsr)
4. [Implementation Priority Matrix](#4-implementation-priority-matrix)
5. [Recommendations for Finclaw GA Framework](#5-recommendations-for-finclaw-ga-framework)

---

## 1. Executive Summary

All four competitors implement some form of **walk-forward / rolling-window validation** as their primary anti-overfitting mechanism. The key differentiators are:

| Competitor | Primary Technique | Sophistication Level |
|---|---|---|
| FreqAI | Sliding-window retrain + outlier detection | ★★★★ |
| Jesse | Simple in/out-of-sample split | ★★ |
| QuantConnect/Lean | Grid/Euler search optimization with constraints | ★★★ |
| Qlib | Rolling `RollingGen` task generation + train/valid/test segments | ★★★★★ |

The academic literature provides four techniques that **none of the competitors fully implement**, giving finclaw a potential edge:

1. **CPCV** — more statistically rigorous than simple walk-forward
2. **Monte Carlo permutation tests** — detects pure luck vs. real alpha
3. **Deflated Sharpe Ratio** — corrects for multiple-testing bias (trying many strategies)
4. **Purged embargo cross-validation** — handles autocorrelation in time-series

---

## 2. Competitor Analysis

### 2.1 FreqTrade FreqAI

**GitHub:** https://github.com/freqtrade/freqtrade/tree/develop/freqtrade/freqai

FreqAI is the most sophisticated anti-overfitting system among open-source trading bots. It implements:

#### 2.1.1 Sliding Window Walk-Forward

**Code:** [`freqai/data_kitchen.py` — `split_timerange()`](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/data_kitchen.py)

```python
def split_timerange(self, tr, train_split=28, bt_split=7):
    """
    Splits a single timerange into sub-timeranges:
    - train_split: training window (days)
    - bt_split: backtesting/validation window (days)
    The window slides forward by bt_split each iteration.
    """
```

**Configuration:**
```json
{
  "freqai": {
    "train_period_days": 30,
    "backtest_period_days": 7,
    "live_retrain_hours": 0.5,
    "expiration_hours": 0.5
  }
}
```

- Training window: configurable (`train_period_days`)
- Backtest window: configurable (`backtest_period_days`), can be fractional
- The system **slides forward** by `backtest_period_days` each iteration
- In live mode, models are retrained with frequency `live_retrain_hours`
- Models expire after `expiration_hours` — predictions on expired models are flagged via `do_predict == 2`

**Impact:** This is a **pure walk-forward** implementation. The sliding window ensures no look-ahead bias. Each model only sees data prior to its backtest window.

#### 2.1.2 Train/Test Split with Temporal Ordering

**Code:** [`freqai/data_kitchen.py` — `make_train_test_datasets()`](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/data_kitchen.py)

```python
# Default: shuffle=False to preserve temporal ordering
if "shuffle" not in self.freqai_config["data_split_parameters"]:
    self.freqai_config["data_split_parameters"].update({"shuffle": False})
```

Key features:
- **Default no-shuffle** — respects temporal autocorrelation
- `shuffle_after_split` option — shuffles within train/test sets *after* the split (useful for gradient-based models)
- `reverse_train_test_order` — allows testing on older data, training on newer (unusual but available)

#### 2.1.3 Outlier Detection Pipeline

**Code:** [`freqai/freqai_interface.py`](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/freqai_interface.py)

FreqAI implements a multi-layered outlier detection system to **flag unreliable predictions**:

| Method | Config Key | Effect on `do_predict` |
|---|---|---|
| **Dissimilarity Index (DI)** | `DI_threshold: 1` | Subtracts 1 if input is far from training data |
| **SVM Outlier Detector** | `use_SVM_to_remove_outliers: true` | Subtracts 1 for SVM-detected outliers |
| **DBSCAN Clustering** | `use_DBSCAN_to_remove_outliers: true` | Subtracts 1 for DBSCAN-detected outliers |

The `do_predict` score ranges from -2 to 2:
- `2` = model expired
- `1` = trustworthy prediction
- `0` = one detector flagged
- `-1` = two detectors flagged
- `-2` = all detectors flagged

**This is unique** — none of the other competitors have this "prediction confidence scoring" at the model level.

#### 2.1.4 Temporal Weighting

```python
# Exponential decay weight: recent data weighted more heavily
W_i = exp(-i / (alpha * n))
```

Config: `weight_factor` in `feature_parameters`. Higher values = more weight on recent data.

#### 2.1.5 Continual Learning (Experimental)

```json
{ "continual_learning": true }
```

New models start from the previous model's state rather than training from scratch. FreqAI itself warns this has "a high probability of overfitting/getting stuck in local minima."

#### 2.1.6 PCA Feature Reduction

Config: `principal_component_analysis: true` — reduces feature dimensionality to prevent overfitting on noisy features.

**Relevance to finclaw GA:**
- Walk-forward sliding window → **directly applicable** as GA evaluation pipeline
- Outlier/DI detection → can be used as **fitness penalty** for strategies with many outlier predictions
- Temporal weighting → could weight recent performance more in fitness scoring

---

### 2.2 Jesse

**GitHub:** https://github.com/jesse-ai/jesse

Jesse takes a **minimalist approach** to anti-overfitting compared to FreqAI.

#### 2.2.1 Simple Backtesting with Warmup

**Code:** [`jesse/modes/backtest_mode.py`](https://github.com/jesse-ai/jesse/blob/master/jesse/modes/backtest_mode.py)

```python
warmup_candles, candles = load_candles(
    jh.date_to_timestamp(start_date),
    jh.date_to_timestamp(finish_date)
)
_handle_warmup_candles(warmup_candles, start_date)
```

- Uses a **warmup period** (default 210 candles) before the backtest window to initialize indicators
- No built-in walk-forward — single in-sample backtest window
- No built-in cross-validation

#### 2.2.2 Hyperparameter Optimization

Jesse provides `optimize_mode` for genetic-algorithm-based hyperparameter optimization, but:
- Optimization runs over a **single window** — no walk-forward
- No out-of-sample validation built into the optimization loop
- Risk of overfitting to the optimization window is **high**

#### 2.2.3 What Jesse Lacks

- No walk-forward validation
- No cross-validation
- No outlier detection
- No model expiration / staleness detection
- No temporal weighting

**Relevance to finclaw GA:**
- Jesse is a cautionary example — **minimal anti-overfitting = strategies that fail in production**
- Finclaw should avoid Jesse's approach of single-window optimization

---

### 2.3 QuantConnect / Lean

**GitHub:** https://github.com/QuantConnect/Lean

QuantConnect focuses on **parameter optimization** rather than ML model validation, with a different but complementary approach.

#### 2.3.1 Optimization Framework

**Code:** [`Optimizer/LeanOptimizer.cs`](https://github.com/QuantConnect/Lean/blob/master/Optimizer/LeanOptimizer.cs)

The Lean optimizer runs multiple complete backtests with different parameter sets:

```csharp
// Core optimization loop
Strategy.NewParameterSet += (s, parameterSet) => {
    LaunchLeanForParameterSet(parameterSet);
};
```

#### 2.3.2 Grid Search

**Code:** [`Optimizer/Strategies/GridSearchOptimizationStrategy.cs`](https://github.com/QuantConnect/Lean/blob/master/Optimizer/Strategies/GridSearchOptimizationStrategy.cs)

Simple exhaustive search over cartesian product of parameter ranges. No anti-overfitting built in.

#### 2.3.3 Euler Search (Multi-Resolution)

**Code:** [`Optimizer/Strategies/EulerSearchOptimizationStrategy.cs`](https://github.com/QuantConnect/Lean/blob/master/Optimizer/Strategies/EulerSearchOptimizationStrategy.cs)

```csharp
// Progressively narrows search range around best solution
var newStep = Math.Max(minStep, step / _segmentsAmount);
var fractal = newStep * ((decimal)_segmentsAmount / 2);
// Zooms in: [best - fractal, best + fractal] with finer step
```

This is a **hierarchical search** that zooms into promising parameter regions. Each level uses a finer grid. While not explicitly anti-overfitting, the multi-resolution approach avoids over-precision.

#### 2.3.4 Optimization Constraints

QuantConnect supports **constraints** on optimization results (e.g., minimum number of trades, maximum drawdown). This acts as implicit overfitting protection by filtering out degenerate solutions.

#### 2.3.5 Out-of-Sample Framework

QuantConnect's platform (not fully in Lean OSS) provides:
- **In-sample / out-of-sample splits** via the Research environment
- **Walk-forward optimization** as a documented workflow (though implementation is user-side)
- **Paper trading** validation before live deployment

#### 2.3.6 What QuantConnect Lacks (in OSS Lean)

- No built-in walk-forward as part of the optimizer
- No cross-validation integration
- No automatic model staleness detection
- The optimizer treats each backtest as independent — no temporal awareness

**Relevance to finclaw GA:**
- **Euler search's hierarchical approach** could inspire multi-resolution GA evolution (coarse then fine)
- **Constraint-based filtering** is directly applicable as GA selection pressure
- QuantConnect demonstrates that optimization without walk-forward is insufficient

---

### 2.4 Microsoft Qlib

**GitHub:** https://github.com/microsoft/qlib

Qlib has the **most sophisticated** anti-overfitting framework of all competitors. It's designed for institutional-grade quantitative research.

#### 2.4.1 Rolling Task Generation (`RollingGen`)

**Code:** [`qlib/workflow/task/gen.py`](https://github.com/microsoft/qlib/blob/main/qlib/workflow/task/gen.py)

```python
class RollingGen(TaskGen):
    ROLL_EX = TimeAdjuster.SHIFT_EX  # expanding window (for train)
    ROLL_SD = TimeAdjuster.SHIFT_SD  # sliding window (for test/valid)

    def __init__(self, step=40, rtype=ROLL_EX, trunc_days=None):
        """
        step: number of trading days to roll forward
        rtype: ROLL_EX (expanding train) or ROLL_SD (sliding)
        trunc_days: days to truncate to prevent future leakage
        """
```

Key features:
- **Two rolling modes:**
  - `ROLL_EX` (Expanding): Training window grows over time, keeping all historical data
  - `ROLL_SD` (Sliding): Fixed-size training window slides forward
- **Configurable step size** (`step=40` = 40 trading days per roll)
- **Future information leakage prevention** via `trunc_days`
- **Automatic handler end-time adjustment** to prevent data leakage:

```python
def trunc_segments(ta, segments, days, test_key="test"):
    """Truncate segments to avoid leakage of future information"""
    test_start = min(t for t in segments[test_key] if t is not None)
    for k in list(segments.keys()):
        if k != test_key:
            segments[k] = ta.truncate(segments[k], test_start, days)
```

#### 2.4.2 Train / Valid / Test Segments

**Config:** [`examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml)

```yaml
segments:
  train: [2008-01-01, 2014-12-31]  # 7 years
  valid: [2015-01-01, 2016-12-31]  # 2 years
  test:  [2017-01-01, 2020-08-01]  # 3.5 years
```

Qlib enforces **three-way splits**: train for fitting, valid for hyperparameter tuning, test for final evaluation. When combined with `RollingGen`, this creates a rolling three-segment approach.

#### 2.4.3 Multi-Horizon Generation

**Code:** [`qlib/workflow/task/gen.py` — `MultiHorizonGenBase`](https://github.com/microsoft/qlib/blob/main/qlib/workflow/task/gen.py)

```python
class MultiHorizonGenBase(TaskGen):
    def __init__(self, horizon=[5], label_leak_n=2):
        """
        horizon: prediction horizons (e.g., 5-day, 10-day return)
        label_leak_n: days of future info needed for label construction
        """
```

- Tests strategy across **multiple prediction horizons** simultaneously
- Automatically adjusts segments to account for `label_leak_n` days of future data leakage
- If a strategy only works on one horizon, it's likely overfit

#### 2.4.4 Composable Task Generator Pipeline

```python
# Generate rolling + multi-horizon tasks from a single template
tasks = task_generator([base_task], [RollingGen(step=40), MultiHorizonGen(horizon=[5,10,20])])
# Result: N_rolls * 3 horizons = many independent tasks
```

This **composability** is Qlib's killer feature — generators multiply out independently, creating a comprehensive evaluation grid.

#### 2.4.5 Signal Analysis & Risk Analytics

**Code:** [`qlib/contrib/evaluate.py`](https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py)

```python
def risk_analysis(r, N=None, freq="day", mode="sum"):
    """Computes: mean, std, annualized_return, information_ratio, max_drawdown"""
```

Qlib's `SigAnaRecord` computes IC (Information Coefficient), ICIR, and rank IC across the rolling windows — detecting degrading signal quality automatically.

#### 2.4.6 Data Handler Fit/Transform Separation

```yaml
data_handler_config:
  fit_start_time: 2008-01-01
  fit_end_time: 2014-12-31  # Feature normalization only on train period
  start_time: 2008-01-01
  end_time: 2020-08-01
```

Feature engineering (normalization, PCA, etc.) is **fit** only on training data and then **applied** to valid/test — preventing look-ahead bias in feature construction.

**Relevance to finclaw GA:**
- `RollingGen` pattern → **must-have** for GA fitness evaluation
- Expanding vs. sliding window → should be configurable in finclaw
- Composable generators → fitness evaluation should compose walk-forward × multiple horizons × Monte Carlo
- `trunc_days` / embargo → critical for label leakage prevention
- Multi-horizon testing → strategies that generalize across horizons get higher fitness

---

## 3. Academic Techniques

### 3.1 Walk-Forward Validation

**Reference:** Pardo, R.E. (2008). *The Evaluation and Optimization of Trading Strategies*, 2nd ed. Wiley.

#### Description

Walk-forward validation (WFV) is the **gold standard** for trading strategy validation. The process:

1. **Optimize** on in-sample window (e.g., 12 months)
2. **Test** on out-of-sample window (e.g., 3 months)
3. **Roll forward** by the out-of-sample window size
4. **Repeat** until data is exhausted
5. **Aggregate** all out-of-sample results for evaluation

The Walk-Forward Efficiency (WFE) metric compares out-of-sample vs. in-sample performance:

$$WFE = \frac{\text{annualized return}_{OOS}}{\text{annualized return}_{IS}}$$

A WFE > 0.5 is generally considered acceptable; a WFE close to 1.0 indicates robust performance.

#### Variants

| Variant | Training Window | Test Window | Use Case |
|---|---|---|---|
| **Anchored** (Expanding) | Grows each roll | Fixed | Strategies that benefit from more data |
| **Rolling** (Sliding) | Fixed size | Fixed | Strategies that adapt to regime changes |
| **Optimized** | Varies (Pardo method) | Fixed | Performance-adaptive window sizing |

#### Implementation for Finclaw GA

**Difficulty: ★★☆☆☆ (Low)**

Walk-forward is the **minimum viable anti-overfitting technique**. It changes the **evaluation pipeline**, not the fitness function itself.

```python
# Pseudocode for GA fitness with walk-forward
def evaluate_strategy(strategy, data, train_days=252, test_days=63):
    oos_results = []
    for train_start, train_end, test_start, test_end in rolling_windows(data, train_days, test_days):
        strategy.optimize(data[train_start:train_end])
        result = strategy.backtest(data[test_start:test_end])
        oos_results.append(result)
    return aggregate_fitness(oos_results)  # mean Sharpe, etc.
```

**Expected Impact: ★★★★★ (Critical)**
- Eliminates the most common form of overfitting (fitting to the full dataset)
- All competitors implement this in some form

---

### 3.2 Combinatorial Purged Cross-Validation (CPCV)

**Reference:** de Prado, M.L. (2018). *Advances in Financial Machine Learning*. Wiley. Chapter 12. ([DOI: 10.1002/9781119482086](https://doi.org/10.1002/9781119482086))

#### Description

Standard k-fold CV is **invalid for time-series** because:
1. Training folds may contain future data relative to test folds
2. Autocorrelation causes information leakage across folds

CPCV solves this by:

1. **Dividing** the data into $N$ contiguous groups
2. **Choosing** $k$ groups as test sets (from $\binom{N}{k}$ combinations)
3. **Purging**: removing training samples whose labels overlap with test samples
4. **Embargoing**: adding a gap between train and test to prevent serial correlation leakage

$$\text{Number of paths} = \binom{N}{k} \cdot k!$$

Each "path" is a complete walk through time using only OOS predictions. The key insight is that CPCV generates **multiple independent backtest paths** from a single dataset, providing:
- A **distribution** of performance metrics (not just a point estimate)
- A **combinatorial** number of validation paths
- Proper **temporal ordering** despite being cross-validation

#### Purging & Embargo

```
|---train---|###purge###|---test---|###embargo###|---train---|
```

- **Purge width**: equal to the strategy's label horizon (e.g., if predicting 5-day returns, purge 5 days before test)
- **Embargo width**: typically 1-2% of total sample size

#### Implementation for Finclaw GA

**Difficulty: ★★★☆☆ (Medium)**

The key complexity is the combinatorial explosion: for $N=10, k=2$, there are $\binom{10}{2} = 45$ paths. Each path requires a full backtest.

```python
# Pseudocode for CPCV
def cpcv_evaluate(strategy, data, N=10, k=2, purge_days=5, embargo_pct=0.01):
    groups = split_into_groups(data, N)
    paths = []
    for test_groups in combinations(range(N), k):
        train_groups = [g for g in range(N) if g not in test_groups]
        train_data = purge_and_embargo(groups, train_groups, test_groups, purge_days, embargo_pct)
        test_data = concat([groups[g] for g in test_groups])
        strategy.train(train_data)
        result = strategy.backtest(test_data)
        paths.append(result)
    return distribution_stats(paths)  # mean, std, percentiles
```

For the GA, we can reduce cost by:
- Using smaller $N$ (e.g., $N=6, k=2$ → 15 paths)
- Running CPCV only for **elite candidates** (top 10% of population)
- Using a fast proxy metric for initial screening, then CPCV for final selection

**Expected Impact: ★★★★☆ (High)**
- Much more statistically rigorous than simple walk-forward
- Provides confidence intervals on strategy performance
- Catches overfitted strategies that can pass walk-forward (because walk-forward gives only one path)

**Changes required:**
- Evaluation pipeline: new `CPCVEvaluator` class
- Fitness function: can use mean Sharpe across paths, or worst-case Sharpe, or Sharpe's standard deviation as a penalty

---

### 3.3 Monte Carlo Permutation Tests

**Reference:** White, H. (2000). "A Reality Check for Data Snooping." *Econometrica*, 68(5), 1097-1126. Also: Romano, J.P. & Wolf, M. (2005). "Stepwise Multiple Testing as Formalized Data Snooping."

#### Description

The core question: **"Is this strategy's performance due to skill or luck?"**

Monte Carlo permutation tests answer this by:

1. Record the strategy's performance metric (e.g., Sharpe ratio = 1.5)
2. **Permute** the returns series (shuffle the order) many times (e.g., 10,000)
3. Re-evaluate the strategy on each permuted dataset
4. Compute a **p-value**: fraction of permuted runs that achieved equal or better performance

$$p = \frac{1 + \sum_{i=1}^{B} \mathbb{1}[\hat{\theta}_i \geq \hat{\theta}_{observed}]}{1 + B}$$

where $B$ is the number of permutations.

#### Variants for Trading

| Variant | How It Permutes | What It Tests |
|---|---|---|
| **Return shuffling** | Randomize daily return order | Tests temporal patterns |
| **Circular block bootstrap** | Shuffle blocks of returns | Preserves autocorrelation structure |
| **Signal shuffling** | Randomize trade signals | Tests signal timing |
| **Universe shuffling** | Randomly assign assets to portfolios | Tests cross-sectional selection |

**Circular block bootstrap** is preferred for financial data because it preserves volatility clustering and autocorrelation.

#### Implementation for Finclaw GA

**Difficulty: ★★☆☆☆ (Low)**

```python
def monte_carlo_test(strategy, data, n_permutations=1000, block_size=20):
    actual_sharpe = strategy.backtest(data).sharpe_ratio
    permuted_sharpes = []
    for _ in range(n_permutations):
        permuted_data = circular_block_bootstrap(data, block_size)
        permuted_sharpes.append(strategy.backtest(permuted_data).sharpe_ratio)
    p_value = (1 + sum(s >= actual_sharpe for s in permuted_sharpes)) / (1 + n_permutations)
    return p_value
```

The challenge is computational cost: 1,000 permutations × N strategies in GA population = 1,000N backtests.

**Mitigation:**
- Run MC tests only on **tournament winners** (top fitness candidates)
- Use a fast vectorized backtest for permuted runs (no order execution simulation)
- Apply as a **post-selection filter** rather than in the fitness function

**Expected Impact: ★★★☆☆ (Medium-High)**
- Excellent at detecting "accidentally good" strategies (pure luck)
- p-value can be used as a **fitness penalty**: `adjusted_fitness = fitness × (1 - p_value)`
- Less useful for strategies with genuine but weak alpha

**Changes required:**
- Post-evolution validation step
- Could integrate into fitness as: `fitness = sharpe × (1 - mc_p_value)` if computation budget allows

---

### 3.4 Deflated Sharpe Ratio (DSR)

**Reference:** Bailey, D.H. & de Prado, M.L. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." *Journal of Portfolio Management*.

#### Description

When you test $K$ strategies and pick the best one, the reported Sharpe ratio is **inflated** by selection bias. The more strategies you try (higher $K$), the more inflated.

The DSR corrects for this:

$$DSR = \Phi\left[\frac{(\hat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \cdot \hat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\hat{SR}^2}}\right]$$

where:
- $\hat{SR}$ = observed (best) Sharpe ratio
- $SR_0$ = expected maximum Sharpe from trying $K$ strategies under the null (no skill):

$$E[\max SR] \approx (1 - \gamma)\cdot Z^{-1}(1 - \frac{1}{K}) + \gamma \cdot Z^{-1}(1 - \frac{1}{K} \cdot e^{-1})$$

($\gamma$ ≈ 0.5772 is the Euler-Mascheroni constant)

- $T$ = number of return observations
- $\hat{\gamma}_3$ = skewness of returns
- $\hat{\gamma}_4$ = kurtosis of returns
- $\Phi$ = standard normal CDF

The DSR output is a **probability** (0 to 1) that the observed Sharpe is genuine, not a product of multiple testing.

#### Why This Matters for GA

In a GA with population $P$ and $G$ generations, the total number of strategies evaluated is $K = P \times G$. For a typical run:
- Population = 100, Generations = 50 → $K = 5,000$
- Expected max Sharpe from 5,000 random strategies ≈ 2.3 (assuming annual Sharpe)

This means a strategy needs Sharpe > 2.3 just to be **statistically distinguishable from luck** with $K = 5,000$ trials.

#### Implementation for Finclaw GA

**Difficulty: ★☆☆☆☆ (Very Low)**

DSR is a pure formula — no additional backtests needed.

```python
import numpy as np
from scipy.stats import norm

def deflated_sharpe_ratio(observed_sr, sr_benchmark, T, skew, kurtosis, K):
    """
    observed_sr: best strategy's Sharpe ratio
    sr_benchmark: expected max SR under null (0 skill)
    T: number of return observations  
    skew: returns skewness
    kurtosis: returns kurtosis (excess)
    K: number of strategies tested
    """
    # Expected max SR from K independent trials
    euler_mascheroni = 0.5772156649
    z_inv = norm.ppf(1 - 1/K)
    sr_0 = (1 - euler_mascheroni) * z_inv + euler_mascheroni * norm.ppf(1 - 1/(K * np.e))
    
    # DSR statistic
    numerator = (observed_sr - sr_0) * np.sqrt(T - 1)
    denominator = np.sqrt(1 - skew * observed_sr + ((kurtosis - 1) / 4) * observed_sr**2)
    
    return norm.cdf(numerator / denominator)
```

**Expected Impact: ★★★★☆ (High)**
- Directly addresses the multiple-testing problem inherent in GA evolution
- Forces the GA to find strategies with genuinely high Sharpe, not just best-of-many-random
- Can be used as a **final selection filter**: only export strategies with DSR > 0.95

**Changes required:**
- Track total number of unique strategies evaluated ($K$)
- Apply DSR correction to the final reported Sharpe of winning strategies
- Optionally use as fitness modifier: `adjusted_fitness = fitness × DSR`

---

## 4. Implementation Priority Matrix

| Technique | Difficulty | Impact | Changes To | Priority | Sprint |
|---|---|---|---|---|---|
| **Walk-Forward Validation** | ★★☆☆☆ | ★★★★★ | Evaluation pipeline | 🔴 P0 | 1 |
| **Deflated Sharpe Ratio** | ★☆☆☆☆ | ★★★★☆ | Post-selection filter | 🔴 P0 | 1 |
| **Expanding vs. Sliding Window** | ★★☆☆☆ | ★★★☆☆ | Evaluation pipeline | 🟡 P1 | 1-2 |
| **Purge & Embargo** | ★★☆☆☆ | ★★★★☆ | Evaluation pipeline | 🟡 P1 | 2 |
| **Monte Carlo Permutation** | ★★☆☆☆ | ★★★☆☆ | Post-selection validation | 🟡 P1 | 2 |
| **CPCV** | ★★★☆☆ | ★★★★☆ | Evaluation pipeline | 🟢 P2 | 3 |
| **Outlier Detection (FreqAI-style)** | ★★★☆☆ | ★★★☆☆ | Fitness penalty | 🟢 P2 | 3 |
| **Multi-Horizon Testing (Qlib-style)** | ★★★★☆ | ★★★☆☆ | Evaluation pipeline | 🟢 P2 | 4 |
| **Composable Generators (Qlib-style)** | ★★★★☆ | ★★★★☆ | Architecture | 🔵 P3 | 4-5 |

---

## 5. Recommendations for Finclaw GA Framework

### 5.1 Sprint 1: Foundation (Walk-Forward + DSR)

**Goal:** Every GA fitness evaluation uses walk-forward validation; final results are DSR-corrected.

```python
class WalkForwardEvaluator:
    def __init__(self, train_days=252, test_days=63, mode='sliding'):
        self.train_days = train_days
        self.test_days = test_days
        self.mode = mode  # 'sliding' or 'expanding'
    
    def evaluate(self, strategy, data):
        oos_metrics = []
        for window in self.generate_windows(data):
            strategy.fit(window.train)
            metrics = strategy.backtest(window.test)
            oos_metrics.append(metrics)
        
        # Aggregate OOS results
        mean_sharpe = np.mean([m.sharpe for m in oos_metrics])
        sharpe_std = np.std([m.sharpe for m in oos_metrics])
        
        # Walk-Forward Efficiency
        is_sharpe = np.mean([m.sharpe for m in is_metrics])
        wfe = mean_sharpe / is_sharpe if is_sharpe > 0 else 0
        
        return GaFitness(
            sharpe=mean_sharpe,
            sharpe_std=sharpe_std,
            wfe=wfe,
            n_windows=len(oos_metrics),
        )


class DSRFilter:
    def __init__(self):
        self.total_strategies_evaluated = 0
    
    def filter_elite(self, population):
        """Apply DSR to final elite selection"""
        for strategy in population:
            strategy.dsr = deflated_sharpe_ratio(
                observed_sr=strategy.fitness.sharpe,
                T=strategy.fitness.n_observations,
                skew=strategy.fitness.returns_skew,
                kurtosis=strategy.fitness.returns_kurtosis,
                K=self.total_strategies_evaluated,
            )
        return [s for s in population if s.dsr > 0.95]
```

### 5.2 Sprint 2: Robustness Layer (Purge + Embargo + Monte Carlo)

Add purge/embargo gaps between train/test windows:

```python
class PurgedWalkForwardEvaluator(WalkForwardEvaluator):
    def __init__(self, purge_days=5, embargo_pct=0.01, **kwargs):
        super().__init__(**kwargs)
        self.purge_days = purge_days
        self.embargo_pct = embargo_pct
    
    def generate_windows(self, data):
        for window in super().generate_windows(data):
            # Remove purge_days before test from training
            window.train = window.train[:-self.purge_days]
            # Add embargo after test before next train
            window.embargo = int(len(data) * self.embargo_pct)
            yield window
```

Add Monte Carlo as a post-selection filter:

```python
class MonteCarloValidator:
    def validate(self, strategy, data, n_permutations=500, block_size=20):
        actual = strategy.backtest(data).sharpe
        count_better = 0
        for _ in range(n_permutations):
            shuffled = circular_block_bootstrap(data.returns, block_size)
            if strategy.backtest(shuffled).sharpe >= actual:
                count_better += 1
        return (1 + count_better) / (1 + n_permutations)  # p-value
```

### 5.3 Sprint 3: Advanced (CPCV + Multi-Horizon)

CPCV for the elite candidates only (too expensive for full population):

```python
class CPCVEvaluator:
    """Run CPCV only on top 10% of population each generation"""
    def __init__(self, N=6, k=2, purge_days=5, embargo_pct=0.01):
        self.N = N
        self.k = k  # C(6,2) = 15 paths — manageable
    
    def evaluate_elite(self, strategy, data):
        """Returns distribution of Sharpe ratios across CPCV paths"""
        groups = np.array_split(data, self.N)
        path_sharpes = []
        for test_idx in combinations(range(self.N), self.k):
            train_groups = [groups[i] for i in range(self.N) if i not in test_idx]
            train = self.purge_and_embargo(pd.concat(train_groups), groups, test_idx)
            test = pd.concat([groups[i] for i in test_idx])
            strategy.fit(train)
            path_sharpes.append(strategy.backtest(test).sharpe)
        
        return {
            'mean_sharpe': np.mean(path_sharpes),
            'min_sharpe': np.min(path_sharpes),
            'std_sharpe': np.std(path_sharpes),
            'pct_profitable': np.mean([s > 0 for s in path_sharpes]),
        }
```

### 5.4 Proposed Composite Fitness Function

```python
def composite_fitness(strategy, walk_forward_result, dsr, mc_pvalue=None):
    """
    Multi-objective fitness combining:
    1. Mean OOS Sharpe (higher is better)
    2. Sharpe stability (lower std is better)  
    3. Walk-forward efficiency (closer to 1.0 is better)
    4. DSR confidence (higher is better)
    5. Monte Carlo p-value (lower is better, only if available)
    """
    fitness = walk_forward_result.mean_sharpe
    
    # Penalize instability across windows
    stability_penalty = walk_forward_result.sharpe_std * 0.5
    fitness -= stability_penalty
    
    # Penalize poor walk-forward efficiency
    if walk_forward_result.wfe < 0.3:
        fitness *= 0.5  # Harsh penalty for strategies that degrade OOS
    
    # DSR adjustment (probability that SR is genuine)
    fitness *= max(dsr, 0.1)  # Don't zero out completely
    
    # MC test penalty (if computed)
    if mc_pvalue is not None and mc_pvalue > 0.05:
        fitness *= (1 - mc_pvalue)  # Penalize strategies that look like luck
    
    return fitness
```

### 5.5 Key Architecture Decisions

1. **Walk-forward should be the default mode** — no single-window backtests allowed during GA evolution
2. **DSR tracking should be automatic** — the GA engine counts total evaluations and applies DSR to reported results
3. **CPCV should be opt-in** — expensive, use only for final validation or elite refinement
4. **Monte Carlo should be a post-evolution gate** — winning strategies must pass MC test before export/deployment
5. **Composable evaluators** (Qlib pattern) — allow mixing WF + CPCV + MC in pipeline fashion

---

## Appendix A: Key GitHub Links

| Component | URL |
|---|---|
| FreqAI interface | https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/freqai_interface.py |
| FreqAI data kitchen | https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/data_kitchen.py |
| FreqAI feature engineering | https://github.com/freqtrade/freqtrade/blob/develop/docs/freqai-feature-engineering.md |
| Jesse backtest mode | https://github.com/jesse-ai/jesse/blob/master/jesse/modes/backtest_mode.py |
| Lean Optimizer | https://github.com/QuantConnect/Lean/blob/master/Optimizer/LeanOptimizer.cs |
| Lean GridSearch | https://github.com/QuantConnect/Lean/blob/master/Optimizer/Strategies/GridSearchOptimizationStrategy.cs |
| Lean EulerSearch | https://github.com/QuantConnect/Lean/blob/master/Optimizer/Strategies/EulerSearchOptimizationStrategy.cs |
| Qlib RollingGen | https://github.com/microsoft/qlib/blob/main/qlib/workflow/task/gen.py |
| Qlib evaluate | https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py |
| Qlib trainer | https://github.com/microsoft/qlib/blob/main/qlib/model/trainer.py |
| Qlib LightGBM config | https://github.com/microsoft/qlib/blob/main/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml |

## Appendix B: Academic References

1. Pardo, R.E. (2008). *The Evaluation and Optimization of Trading Strategies*, 2nd ed. Wiley.
2. de Prado, M.L. (2018). *Advances in Financial Machine Learning*. Wiley. (CPCV: Chapter 12; Purged CV: Chapter 7)
3. Bailey, D.H. & de Prado, M.L. (2014). "The Deflated Sharpe Ratio." *Journal of Portfolio Management*, 40(5), 94-107.
4. White, H. (2000). "A Reality Check for Data Snooping." *Econometrica*, 68(5), 1097-1126.
5. Romano, J.P. & Wolf, M. (2005). "Stepwise Multiple Testing as Formalized Data Snooping." *Econometrica*, 73(4), 1237-1282.
6. Bailey, D.H. et al. (2017). "The Probability of Backtest Overfitting." *Journal of Computational Finance*, 20(4).
7. de Prado, M.L. (2018). "The 10 Reasons Most Machine Learning Funds Fail." *Journal of Portfolio Management*, 44(6).
