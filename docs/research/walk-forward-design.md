# Walk-Forward Validation System — Technical Design

> **Status:** Design  
> **Author:** 螃蟹 (subagent)  
> **Date:** 2026-03-26  
> **Problem:** Massive overfitting — fitness 291,623; 25,000% annual return on in-sample data.  
> **Root cause:** DNA with ~480 parameters is evolved and evaluated on the *same* data window. The current 70/30 split in `auto_evolve.py` is a single static split — still highly overfit-prone because the GA sees the exact same validation set every generation and learns to game it.

---

## 1. Executive Summary

Replace the current single 70/30 train/val split with a **multi-window anchored walk-forward** validation system. The GA will:

1. **Train** on `[0, T]` (expanding window)
2. **Test** on `[T, T+W]` (fixed-size OOS window)
3. **Slide forward** and **repeat** across 3–6 non-overlapping OOS windows
4. **Final fitness** = weighted mean of all OOS window scores, with an overfit penalty based on IS vs. OOS divergence

This forces strategies to generalize across multiple unseen time regimes. A strategy that scores well on one lucky window but crashes on others will be crushed.

We also introduce a **purged embargo gap** between train and test to prevent indicator-lookback leakage.

---

## 2. Current Architecture Analysis

### 2.1 Two Evolution Systems

The codebase has **two** independent evolution engines:

| Component | File | Purpose |
|-----------|------|---------|
| **YAML-DSL Engine** | `src/evolution/engine.py` + `evaluator.py` | Evolves YAML strategy expressions (`sma(20) > sma(50)`) using LLM-driven mutation. Long-only, single-asset. |
| **AutoEvolver (GA)** | `src/evolution/auto_evolve.py` + `crypto_backtest.py` | Pure numerical GA over `StrategyDNA` (~480 params). Multi-asset, multi-market. **This is where the overfitting problem lives.** |

### 2.2 Current Walk-Forward in AutoEvolver (v3)

`auto_evolve.py` already has a rudimentary walk-forward (line ~1893):

```python
# Train on first 70%, validate on last 30%
warmup = 30
train_end = warmup + int((total_days - warmup) * 0.7)
val_start = train_end
val_end = total_days

# ... later ...
fitness = 0.4 * train_fitness + 0.6 * val_fitness

# Harsh overfit penalty: if validation fitness is < 30% of train fitness
if train_fitness > 0 and val_fitness < 0.3 * train_fitness:
    fitness *= 0.3
```

**Why this fails:**
- **Single static split** — the GA sees the same val window every generation and overfits to it within ~20 generations
- **No embargo gap** — indicators with 60-bar lookback leak train data into val
- **No sliding** — can't detect regime changes or verify robustness across time
- **Val period is always the most recent data** — if market regime happens to match the strategy, fitness is inflated

### 2.3 The Crypto Backtest Path

When `market="crypto"`, `AutoEvolver.evaluate_dna()` dispatches to `CryptoBacktestEngine.run_backtest()` instead of the inline `_run_backtest()`. Both accept `(day_start, day_end)` — this is the key interface we'll leverage.

### 2.4 Key Data Flow

```
AutoEvolver.evolve()
  └─ run_generation(parents, data, gen)
       └─ evaluate_dna(dna, data, indicators, codes)
            ├─ _run_backtest(day_start, day_end)          # A-share
            └─ CryptoBacktestEngine.run_backtest(...)     # Crypto
                 → returns (annual_return, max_drawdown, win_rate, sharpe,
                            calmar, total_trades, profit_factor, sortino,
                            max_consec_losses, monthly_returns, 
                            max_concurrent, avg_turnover)
            └─ compute_fitness(...) → float
```

---

## 3. Walk-Forward Validation Design

### 3.1 Anchored Walk-Forward

```
Data timeline:  [========================================]
                 0                                      N

Window 1:  [■■■■■ TRAIN ■■■■■][GAP][▓▓ TEST ▓▓]
Window 2:  [■■■■■■■■■ TRAIN ■■■■■■■■■][GAP][▓▓ TEST ▓▓]
Window 3:  [■■■■■■■■■■■■■■ TRAIN ■■■■■■■■■■■■■][GAP][▓▓ TEST ▓▓]
Window 4:  [■■■■■■■■■■■■■■■■■■■ TRAIN ■■■■■■■■■■■■■■■■■■][GAP][▓▓ FINAL ▓▓]

■ = In-sample (training)    ▓ = Out-of-sample (test)    GAP = Purge embargo
```

**Why anchored (expanding train)?** More training data → more stable parameter estimates. With 480 parameters, we need all the data we can get.

### 3.2 Parameters

```python
@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation."""
    
    n_windows: int = 4                    # Number of OOS test windows
    min_train_pct: float = 0.40           # Minimum train data as % of total
    test_window_pct: float = 0.10         # Each test window as % of total
    embargo_periods: int = 48             # Gap between train/test (hours for crypto, days for A-share)
    warmup_periods: int = 60              # Indicator warmup before first trade
    
    # Fitness combination
    oos_weight: float = 0.70              # Weight for OOS fitness
    is_weight: float = 0.30              # Weight for IS fitness (last train segment)
    overfit_penalty_threshold: float = 0.25  # Penalize if OOS < 25% of IS
    overfit_penalty_factor: float = 0.20     # Multiply fitness by this on overfit
    
    # Per-window requirements
    min_trades_per_window: int = 10       # Minimum trades in each OOS window
    
    # Consistency weighting
    use_consistency_weighting: bool = True  # Weight windows by OOS consistency
```

### 3.3 Window Calculation

For crypto hourly data with 8760 bars (1 year, 365×24):

```
Total bars: 8760
warmup: 60
usable: 8700

test_window_size = int(8700 * 0.10) = 870 bars (~36 days)
embargo = 48 bars (2 days)

Window layout (4 windows):
  Window 1: train=[60, 4290], embargo=[4290, 4338], test=[4338, 5208]
  Window 2: train=[60, 5208], embargo=[5208, 5256], test=[5256, 6126]
  Window 3: train=[60, 6126], embargo=[6126, 6174], test=[6174, 7044]
  Window 4: train=[60, 7044], embargo=[7044, 7092], test=[7092, 7962]
  
  Remaining bars: 8700 - 7962 + 60 = 798 (unused tail, acceptable)
```

For A-share daily data with 500 trading days (2 years):

```
Total bars: 500
warmup: 30
usable: 470

test_window_size = int(470 * 0.10) = 47 bars (~2.5 months)
embargo = 5 bars (1 week)

Window layout (4 windows):
  Window 1: train=[30, 214], embargo=[214, 219], test=[219, 266]
  Window 2: train=[30, 266], embargo=[266, 271], test=[271, 318]
  Window 3: train=[30, 318], embargo=[318, 323], test=[323, 370]
  Window 4: train=[30, 370], embargo=[370, 375], test=[375, 422]
```

### 3.4 Algorithm

```python
def compute_walk_forward_fitness(
    dna: StrategyDNA,
    data: Dict, indicators: Dict, codes: List[str],
    config: WalkForwardConfig,
    run_backtest_fn: Callable,  # (day_start, day_end) -> backtest_result_tuple
) -> Tuple[float, Dict[str, Any]]:
    """
    Returns (final_fitness, diagnostics_dict).
    """
    total_bars = len(data[codes[0]]["close"])
    usable = total_bars - config.warmup_periods
    test_size = int(usable * config.test_window_pct)
    
    # Calculate window boundaries (back-to-front to maximize test coverage)
    windows = []
    for i in range(config.n_windows):
        test_end = total_bars - i * test_size
        test_start = test_end - test_size
        embargo_start = test_start - config.embargo_periods
        train_start = config.warmup_periods
        train_end = embargo_start
        
        if train_end - train_start < config.warmup_periods * 2:
            break  # Not enough training data
        
        windows.append({
            "train": (train_start, train_end),
            "test": (test_start, test_end),
        })
    
    windows.reverse()  # Chronological order
    
    # Run backtests for each window
    is_fitnesses = []
    oos_fitnesses = []
    oos_details = []
    
    for i, w in enumerate(windows):
        # In-sample backtest (last 30% of training data for IS fitness)
        is_segment_start = w["train"][0] + int((w["train"][1] - w["train"][0]) * 0.7)
        is_result = run_backtest_fn(is_segment_start, w["train"][1])
        is_fitness = compute_fitness(*is_result[:7], sortino=is_result[7], ...)
        
        # Out-of-sample backtest
        oos_result = run_backtest_fn(w["test"][0], w["test"][1])
        oos_fitness = compute_fitness(*oos_result[:7], sortino=oos_result[7], ...)
        
        is_fitnesses.append(is_fitness)
        oos_fitnesses.append(oos_fitness)
        oos_details.append({
            "window": i,
            "is_fitness": is_fitness,
            "oos_fitness": oos_fitness,
            "oos_return": oos_result[0],
            "oos_trades": oos_result[5],
        })
    
    # Aggregate OOS fitness
    valid_oos = [f for f, d in zip(oos_fitnesses, oos_details) 
                 if d["oos_trades"] >= config.min_trades_per_window]
    
    if not valid_oos:
        return -1.0, {"reason": "no valid OOS windows"}
    
    if config.use_consistency_weighting:
        # Penalize high variance across windows
        mean_oos = sum(valid_oos) / len(valid_oos)
        if mean_oos > 0:
            std_oos = (sum((f - mean_oos)**2 for f in valid_oos) / len(valid_oos)) ** 0.5
            cv = std_oos / abs(mean_oos)
            consistency_bonus = max(0.5, 1.0 - cv * 0.3)
        else:
            consistency_bonus = 0.5
        aggregated_oos = mean_oos * consistency_bonus
    else:
        aggregated_oos = sum(valid_oos) / len(valid_oos)
    
    # IS fitness (average of all IS segments)
    aggregated_is = sum(is_fitnesses) / len(is_fitnesses) if is_fitnesses else 0
    
    # Combined fitness
    fitness = config.oos_weight * aggregated_oos + config.is_weight * aggregated_is
    
    # Overfit penalty
    if aggregated_is > 0 and aggregated_oos < config.overfit_penalty_threshold * aggregated_is:
        fitness *= config.overfit_penalty_factor
    
    return fitness, {"windows": oos_details, "consistency_bonus": consistency_bonus}
```

---

## 4. Integration Plan

### 4.1 New File: `src/evolution/walk_forward.py`

This is the core new module. Contains:

```python
# src/evolution/walk_forward.py

@dataclass
class WalkForwardConfig:
    """All walk-forward hyperparameters."""
    ...

@dataclass  
class WindowResult:
    """Results from one walk-forward window."""
    window_index: int
    train_range: Tuple[int, int]
    test_range: Tuple[int, int]
    is_fitness: float
    oos_fitness: float
    oos_annual_return: float
    oos_max_drawdown: float
    oos_sharpe: float
    oos_trades: int
    oos_win_rate: float

@dataclass
class WalkForwardResult:
    """Aggregated walk-forward validation result."""
    final_fitness: float
    is_mean_fitness: float
    oos_mean_fitness: float
    overfit_ratio: float           # oos_mean / is_mean — <1.0 = overfit
    consistency_score: float       # 1.0 = identical across windows
    window_results: List[WindowResult]
    
    def is_likely_overfit(self) -> bool:
        return self.overfit_ratio < 0.3

class WalkForwardValidator:
    """Runs anchored walk-forward validation on a strategy DNA."""
    
    def __init__(self, config: WalkForwardConfig | None = None):
        self.config = config or WalkForwardConfig()
    
    def compute_windows(self, total_bars: int) -> List[Dict]:
        """Calculate train/embargo/test boundaries."""
        ...
    
    def validate(
        self,
        dna: StrategyDNA,
        data: Dict, indicators: Dict, codes: List[str],
        run_backtest_fn: Callable,
    ) -> WalkForwardResult:
        """Run full walk-forward validation. Returns aggregated result."""
        ...
```

### 4.2 Changes to `auto_evolve.py`

#### 4.2.1 `AutoEvolver.__init__()` — Add walk-forward config

```python
# BEFORE (line ~1530)
class AutoEvolver:
    def __init__(self, data_dir="data/daily", market="a-share", ...):
        ...

# AFTER
class AutoEvolver:
    def __init__(
        self,
        data_dir="data/daily",
        market="a-share",
        walk_forward: bool = True,           # NEW
        wf_config: WalkForwardConfig = None, # NEW
        ...
    ):
        ...
        self.walk_forward = walk_forward
        self.wf_validator = WalkForwardValidator(wf_config) if walk_forward else None
```

#### 4.2.2 `AutoEvolver.evaluate_dna()` — Replace the split logic

This is the **main integration point**. The current method (line ~1830) does:
1. Compute `train_end = warmup + int((total_days - warmup) * 0.7)`
2. Run `_run_backtest(warmup, train_end)` and `_run_backtest(val_start, val_end)`
3. Combine: `fitness = 0.4 * train + 0.6 * val`

**New flow:**

```python
def evaluate_dna(self, dna, data, indicators, codes):
    # ... existing data prep, indicator computation ...
    
    total_days = len(data[codes[0]]["close"])
    
    # Build the backtest dispatch function (same as current)
    if self.market == "crypto" and self._crypto_engine is not None:
        def run_bt(day_start, day_end):
            return self._crypto_engine.run_backtest(
                dna, data, indicators, codes, day_start, day_end
            )
    else:
        def run_bt(day_start, day_end):
            return _run_backtest(day_start, day_end)  # existing inline
    
    if self.walk_forward and self.wf_validator is not None:
        # ──── NEW: Walk-Forward Validation ────
        wf_result = self.wf_validator.validate(
            dna, data, indicators, codes, run_bt
        )
        fitness = wf_result.final_fitness
        
        # Use the last OOS window's metrics for reporting
        last_window = wf_result.window_results[-1]
        annual_return = last_window.oos_annual_return
        max_drawdown = last_window.oos_max_drawdown
        sharpe = last_window.oos_sharpe
        win_rate = last_window.oos_win_rate
        total_trades = sum(w.oos_trades for w in wf_result.window_results)
        # ... etc
    else:
        # ──── LEGACY: Single 70/30 split (kept for backward compat) ────
        # ... existing code ...
    
    return EvolutionResult(dna=dna, ..., fitness=fitness)
```

#### 4.2.3 `evolve()` — Add walk-forward diagnostics to logging

```python
# In the per-generation print:
print(
    f"Gen {gen:4d} | "
    f"fitness={best.fitness:8.2f} | "
    f"OOS_ratio={best.overfit_ratio:.2f} | "  # NEW
    ...
)
```

### 4.3 Changes to `evaluator.py` (YAML-DSL Engine)

The YAML-DSL engine (`engine.py` + `evaluator.py`) currently passes the full `OHLCVData` to `evaluate()`. To add walk-forward:

```python
# evaluator.py — new method

def evaluate_walk_forward(
    self, strategy_yaml: str, data: OHLCVData,
    config: WalkForwardConfig | None = None,
) -> Tuple[FitnessScore, WalkForwardResult]:
    """Evaluate strategy with walk-forward validation.
    
    Slices OHLCVData into train/test windows and runs separate
    backtests on each.
    """
    cfg = config or WalkForwardConfig()
    n = len(data.close)
    windows = WalkForwardValidator(cfg).compute_windows(n)
    
    oos_scores = []
    for w in windows:
        # Slice OHLCVData
        test_data = OHLCVData(
            open=data.open[w["test"][0]:w["test"][1]],
            high=data.high[w["test"][0]:w["test"][1]],
            low=data.low[w["test"][0]:w["test"][1]],
            close=data.close[w["test"][0]:w["test"][1]],
            volume=data.volume[w["test"][0]:w["test"][1]],
        )
        score = self.evaluate(strategy_yaml, test_data)
        oos_scores.append(score)
    
    # Aggregate: mean composite of OOS windows
    mean_composite = sum(s.composite() for s in oos_scores) / len(oos_scores)
    ...
```

And update `engine.py` line ~97 to call `evaluate_walk_forward` instead of `evaluate`:

```python
# engine.py — in the main loop, change:
child_score = self.evaluator.evaluate(mutated_yaml, data)
# to:
child_score, wf_result = self.evaluator.evaluate_walk_forward(mutated_yaml, data)
```

---

## 5. Crypto-Specific Considerations

### 5.1 24/7 Market — No Calendar Gaps

Crypto trades 24/7/365. This affects:
- **`periods_per_day`**: 24 for hourly data, 1 for daily
- **`periods_per_year`**: 365 × `periods_per_day` (not 252)
- **Embargo calculation**: In hours, not days. 48 bars = 2 days of hourly data.
- **No weekends/holidays**: Sliding windows don't skip gaps — every bar is tradable.

This is actually **simpler** than A-share for walk-forward because there are no calendar irregularities.

### 5.2 Regime Diversity

Crypto exhibits distinct regimes (bull/bear/sideways/high-vol). The walk-forward windows naturally sample different regimes:
- Window 1 might be a bear market
- Window 2 might be a sideways accumulation
- Window 3 might be a bull run
- Window 4 might be a crash

A strategy that only works in bull markets will score 0 on windows 1, 2, 4 and get crushed in aggregation. This is exactly what we want.

### 5.3 Leverage & Liquidation

The `CryptoBacktestEngine` supports leverage (1–10×) with liquidation checks. Walk-forward doesn't change this — each window runs the same engine. However, a strategy optimized for 5× leverage on training data may get liquidated on OOS data with higher volatility. This provides a natural penalty against over-leveraged strategies.

### 5.4 Window Sizing for Crypto

For hourly crypto data:

| Data Duration | Recommended Windows | Test Window Size | Embargo |
|---|---|---|---|
| 3 months (2,160 bars) | 3 | ~216 bars (9 days) | 24 bars (1 day) |
| 6 months (4,380 bars) | 4 | ~438 bars (18 days) | 48 bars (2 days) |
| 1 year (8,760 bars) | 5 | ~876 bars (36 days) | 48 bars (2 days) |
| 2 years (17,520 bars) | 6 | ~1,752 bars (73 days) | 72 bars (3 days) |

---

## 6. New Fitness Calculation

### 6.1 Composite OOS Fitness Formula

```
final_fitness = (
    OOS_weight × mean(OOS_fitness_per_window) × consistency_bonus
    + IS_weight × mean(IS_fitness_of_last_train_segment)
) × overfit_penalty × trade_count_penalty
```

Where:
- **OOS_weight** = 0.70 (dominant — this is the whole point)
- **IS_weight** = 0.30 (prevents throwing away all IS signal)
- **consistency_bonus** = `max(0.5, 1.0 - CV(OOS_scores) × 0.3)` — rewards strategies that perform similarly across all windows
- **overfit_penalty** = `0.20 if (mean_OOS / mean_IS) < 0.25 else 1.0` — harsh kill for extreme overfitters
- **trade_count_penalty** = penalize if any OOS window has < 10 trades (could be luck)

### 6.2 Why 70/30 (OOS/IS) Instead of 100% OOS?

Pure OOS fitness (100%) discards IS signal entirely. This is too noisy early in evolution when you have few generations and need some gradient to guide mutation. The 30% IS component provides a smoother fitness landscape for the GA to navigate. As the population converges, OOS dominance ensures generalization.

### 6.3 Expected Impact on Fitness Values

Current fitness: **291,623** (absurdly overfit)

Expected post-implementation:
- OOS fitness per window: likely **5–50** range for strategies that generalize
- Overfit strategies: **<1.0** (crushed by OOS penalty)
- Good strategies: **10–100** range
- Target: fitness ~20–50 with Sharpe >1.0, return <100%/year

---

## 7. Purged K-Fold (Optional Enhancement)

In addition to anchored walk-forward, we can implement **purged K-fold cross-validation** for a second opinion:

```
Fold 1:  [▓▓ TEST ▓▓][GAP][■■■■■■■■■■ TRAIN ■■■■■■■■■■]
Fold 2:  [■■ TRAIN ■■][GAP][▓▓ TEST ▓▓][GAP][■■ TRAIN ■■]
Fold 3:  [■■■■■ TRAIN ■■■■■][GAP][▓▓ TEST ▓▓][GAP][■ TRAIN ■]
Fold 4:  [■■■■■■■■■■ TRAIN ■■■■■■■■■■][GAP][▓▓ TEST ▓▓]
```

**Key differences from anchored walk-forward:**
- Each fold uses a different test segment
- Training data is everything *except* the test window (with embargo gaps on both sides)
- More data-efficient — every bar appears in test exactly once
- Better for short datasets where anchored walk-forward runs out of data

**Implementation:** Add as a `ValidationMode` enum:

```python
class ValidationMode(Enum):
    SINGLE_SPLIT = "single_split"       # Current 70/30
    ANCHORED_WF = "anchored_wf"         # Recommended default
    PURGED_KFOLD = "purged_kfold"       # Data-efficient alternative
    COMBINATORIAL = "combinatorial"     # Future: CPCV
```

**Recommendation:** Start with `ANCHORED_WF` (simpler, well-understood). Add `PURGED_KFOLD` in v2 if anchored walk-forward is too slow or data is too short.

---

## 8. Performance Considerations

### 8.1 Backtest Count Multiplier

Current: 2 backtests per DNA (train + val)
Walk-forward with 4 windows: **8 backtests per DNA** (4 IS + 4 OOS)

With population_size=30 and 100 generations:
- Current: 30 × 100 × 2 = 6,000 backtests
- Walk-forward: 30 × 100 × 8 = 24,000 backtests
- **4× slowdown** per generation

### 8.2 Mitigation Strategies

1. **Cache IS results across windows** — Window N's IS includes Window N-1's IS + more data. Can reuse partial results.
2. **Parallel backtests** — Each window is independent. Use `concurrent.futures.ProcessPoolExecutor`.
3. **Early termination** — If the first 2 OOS windows score < 0, skip remaining windows.
4. **Reduce population** — Use 15–20 instead of 30 (GA converges faster with better fitness signal).
5. **Coarse-to-fine** — First 20 generations use 2 windows; switch to 4 windows after.

### 8.3 Implementation: Parallelism

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

class WalkForwardValidator:
    def __init__(self, config, max_workers=4):
        self.max_workers = max_workers
    
    def validate(self, dna, data, indicators, codes, run_backtest_fn):
        windows = self.compute_windows(len(data[codes[0]]["close"]))
        
        # Sequential for now (backtest uses shared state)
        # TODO: make backtest stateless for parallel execution
        results = []
        for w in windows:
            is_result = run_backtest_fn(w["train"][0], w["train"][1])
            oos_result = run_backtest_fn(w["test"][0], w["test"][1])
            results.append((is_result, oos_result))
        
        return self._aggregate(results)
```

**Note:** The current `CryptoBacktestEngine.run_backtest()` and inline `_run_backtest()` are both stateless (they don't modify the engine instance). This means they're safe to parallelize, but `score_stock()` reads from `indicators` dict which may have issues. For v1, keep sequential. Profile first, then parallelize.

---

## 9. Estimated Implementation Effort

| Task | Effort | Dependencies |
|------|--------|--------------|
| `walk_forward.py` — WalkForwardConfig, WindowResult, WalkForwardResult dataclasses | 1 hour | None |
| `walk_forward.py` — `compute_windows()` with embargo logic | 2 hours | None |
| `walk_forward.py` — `validate()` main loop | 3 hours | compute_windows |
| `auto_evolve.py` — integrate WalkForwardValidator into `evaluate_dna()` | 2 hours | walk_forward.py |
| `auto_evolve.py` — update `__init__` and `evolve()` logging | 1 hour | integration |
| `evaluator.py` — add `evaluate_walk_forward()` for YAML-DSL engine | 2 hours | walk_forward.py |
| `engine.py` — optional integration | 1 hour | evaluator changes |
| Tests: `test_walk_forward.py` | 3 hours | all above |
| Integration test: run evolution and compare old vs new fitness | 2 hours | all above |
| **Total** | **~17 hours** | **~2-3 days** |

### 9.1 Phased Rollout

**Phase 1 (Day 1):** `walk_forward.py` + integration into `auto_evolve.py` for crypto market.
**Phase 2 (Day 2):** Tests + Integration into A-share backtest path.
**Phase 3 (Day 3):** Integration into YAML-DSL engine (`engine.py`/`evaluator.py`). Performance profiling.

---

## 10. Test Plan

### 10.1 Unit Tests (`tests/test_walk_forward.py`)

```python
class TestWalkForwardConfig:
    def test_default_config(self):
        """Default config has sane values."""
        cfg = WalkForwardConfig()
        assert cfg.n_windows == 4
        assert cfg.oos_weight + cfg.is_weight == 1.0
    
    def test_weights_sum_to_one(self):
        """OOS + IS weights must sum to 1.0."""
        cfg = WalkForwardConfig(oos_weight=0.8, is_weight=0.2)
        assert cfg.oos_weight + cfg.is_weight == 1.0

class TestWindowComputation:
    def test_basic_4_windows(self):
        """4 windows on 1000 bars."""
        v = WalkForwardValidator(WalkForwardConfig(n_windows=4))
        windows = v.compute_windows(1000)
        assert len(windows) == 4
        # Windows should be chronological
        for i in range(1, len(windows)):
            assert windows[i]["test"][0] > windows[i-1]["test"][0]
    
    def test_no_overlap(self):
        """Test windows must not overlap."""
        v = WalkForwardValidator()
        windows = v.compute_windows(2000)
        for i in range(1, len(windows)):
            assert windows[i]["test"][0] >= windows[i-1]["test"][1]
    
    def test_embargo_gap(self):
        """Embargo gap between train end and test start."""
        cfg = WalkForwardConfig(embargo_periods=48)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(5000)
        for w in windows:
            assert w["test"][0] - w["train"][1] >= 48
    
    def test_train_always_before_test(self):
        """Train period must end before test starts."""
        v = WalkForwardValidator()
        windows = v.compute_windows(3000)
        for w in windows:
            assert w["train"][1] <= w["test"][0]
    
    def test_insufficient_data(self):
        """Too few bars should produce fewer windows."""
        cfg = WalkForwardConfig(n_windows=6)
        v = WalkForwardValidator(cfg)
        windows = v.compute_windows(300)
        assert len(windows) < 6  # Can't fit 6 windows in 300 bars
    
    def test_anchored_expansion(self):
        """Train always starts from warmup (anchored)."""
        v = WalkForwardValidator(WalkForwardConfig(warmup_periods=60))
        windows = v.compute_windows(5000)
        for w in windows:
            assert w["train"][0] == 60  # All anchored to warmup

class TestWalkForwardValidation:
    def test_perfect_strategy(self):
        """Strategy that works everywhere gets high fitness."""
        # Mock backtest that always returns good results
        def good_backtest(start, end):
            n = end - start
            return (50.0, 10.0, 65.0, 2.0, 5.0, max(n // 10, 15), 2.0, 2.5, 3, [5.0]*3, 2, 0.3)
        
        v = WalkForwardValidator()
        result = v.validate(mock_dna, mock_data, mock_ind, ["BTC"], good_backtest)
        assert result.final_fitness > 0
        assert result.overfit_ratio > 0.5  # Not overfit
    
    def test_overfit_strategy(self):
        """Strategy that only works IS gets crushed."""
        call_count = [0]
        def overfit_backtest(start, end):
            call_count[0] += 1
            if call_count[0] % 2 == 1:  # IS calls (odd)
                return (100.0, 5.0, 70.0, 3.0, 20.0, 50, 3.0, 3.5, 2, [10.0]*3, 2, 0.2)
            else:  # OOS calls (even)
                return (-5.0, 30.0, 35.0, -0.5, -0.2, 15, 0.5, -0.3, 8, [-3.0]*3, 1, 0.5)
        
        v = WalkForwardValidator()
        result = v.validate(mock_dna, mock_data, mock_ind, ["BTC"], overfit_backtest)
        # Overfit strategy should be penalized
        assert result.overfit_ratio < 0.3
        assert result.is_likely_overfit()
    
    def test_insufficient_trades_penalty(self):
        """OOS windows with too few trades get excluded."""
        def low_trade_backtest(start, end):
            return (10.0, 5.0, 60.0, 1.5, 2.0, 3, 1.5, 1.8, 1, [2.0], 1, 0.1)  # only 3 trades
        
        v = WalkForwardValidator(WalkForwardConfig(min_trades_per_window=10))
        result = v.validate(mock_dna, mock_data, mock_ind, ["BTC"], low_trade_backtest)
        assert result.final_fitness <= 0  # All windows excluded

class TestIntegration:
    def test_auto_evolver_with_walk_forward(self):
        """AutoEvolver with walk_forward=True runs without error."""
        evolver = AutoEvolver(
            data_dir="data/crypto",
            market="crypto",
            walk_forward=True,
            wf_config=WalkForwardConfig(n_windows=2),  # Fast
        )
        # ... run 1 generation on small data ...
    
    def test_backward_compat_without_walk_forward(self):
        """walk_forward=False preserves current behavior."""
        evolver = AutoEvolver(
            data_dir="data/crypto",
            market="crypto",
            walk_forward=False,
        )
        # Should use old 70/30 split
```

### 10.2 Regression Test

Run evolution for 10 generations with old vs new system on the same crypto data:

```bash
# Old system (baseline)
python -c "
from src.evolution.auto_evolve import AutoEvolver
e = AutoEvolver(data_dir='data/crypto', market='crypto', walk_forward=False)
results = e.evolve(generations=10)
print(f'Old fitness: {results[0].fitness}')
print(f'Old return: {results[0].annual_return}%')
"

# New system
python -c "
from src.evolution.auto_evolve import AutoEvolver
from src.evolution.walk_forward import WalkForwardConfig
e = AutoEvolver(data_dir='data/crypto', market='crypto', walk_forward=True,
    wf_config=WalkForwardConfig(n_windows=4))
results = e.evolve(generations=10)
print(f'New fitness: {results[0].fitness}')
print(f'New return: {results[0].annual_return}%')
"
```

**Expected:** New fitness should be orders of magnitude lower (realistic), with annual return < 200%.

### 10.3 Overfitting Detection Test

```python
def test_overfit_detection():
    """Known-overfit DNA should be flagged."""
    # Load the DNA that produced 25,000% return
    with open("evolution_results_crypto/latest.json") as f:
        overfit_dna = StrategyDNA.from_dict(json.load(f)["results"][0]["dna"])
    
    evolver = AutoEvolver(data_dir="data/crypto", market="crypto", walk_forward=True)
    data = evolver.load_data()
    result = evolver.evaluate_dna(overfit_dna, data, ...)
    
    # This DNA should have terrible OOS performance
    assert result.fitness < 10.0  # vs. current 291,623
```

---

## 11. Future Enhancements

### 11.1 Combinatorial Purged Cross-Validation (CPCV)

From López de Prado's *Advances in Financial Machine Learning*: instead of sequential windows, generate all C(N, K) combinations of K test blocks from N blocks. Provides a distribution of Sharpe ratios / returns, not just a point estimate. Very computationally expensive — save for v3.

### 11.2 Walk-Forward Optimization (WFO)

True WFO re-optimizes (re-evolves) on each expanding window, not just evaluates. This would mean running a mini-evolution on `[0, T]`, then testing on `[T, T+W]`, then re-evolving on `[0, T+W]`, etc. Much more expensive but the gold standard for production trading systems. Save for v4.

### 11.3 Multi-Asset Walk-Forward

Current walk-forward applies the same time windows to all assets. A more sophisticated version would also rotate *which assets* are in the training vs. test set (combinatorial asset splits). This prevents overfitting to specific asset characteristics.

### 11.4 Deflated Sharpe Ratio

Adjust the final Sharpe ratio for multiple testing bias (we test hundreds of strategy variants). The deflated Sharpe accounts for the number of trials and provides a p-value for whether the strategy's performance occurred by chance. Integrate with walk-forward fitness as an additional penalty term.

---

## 12. Summary of Changes

| File | Change | Lines Affected |
|------|--------|----------------|
| `src/evolution/walk_forward.py` | **NEW** — WalkForwardConfig, WalkForwardValidator, result dataclasses | ~200 lines |
| `src/evolution/auto_evolve.py` | Add `walk_forward` param to `__init__`, replace split logic in `evaluate_dna()`, update `evolve()` logging | ~50 lines changed, ~20 lines added |
| `src/evolution/evaluator.py` | Add `evaluate_walk_forward()` method | ~40 lines added |
| `src/evolution/engine.py` | Optional: use `evaluate_walk_forward` in main loop | ~5 lines changed |
| `tests/test_walk_forward.py` | **NEW** — comprehensive test suite | ~200 lines |
| **Total** | | ~515 lines |

### Key Design Decisions

1. **70% OOS / 30% IS weight** — OOS dominates but IS provides gradient signal
2. **4 windows default** — balance between robustness and compute cost
3. **48-period embargo** — sufficient for most indicator lookbacks (longest is 60-bar warmup)
4. **Anchored (expanding) train** — maximizes training data for high-dimensional DNA
5. **Backward compatible** — `walk_forward=False` preserves current behavior exactly
6. **Sequential execution for v1** — parallelize in v2 after profiling
