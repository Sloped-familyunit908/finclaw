"""
Automatic Strategy Evolution Engine
====================================
Runs 24/7. Each generation:
1. Take current best strategy parameters
2. Mutate parameters randomly (genetic algorithm)
3. Backtest all mutations on local CSV data
4. Keep top performers
5. Repeat

Uses local CSV data only — no API calls needed.
Separate from the YAML-DSL evolution engine (engine.py).
This is pure numerical parameter optimization via genetic algorithms.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class StrategyDNA:
    """All tunable parameters for a trading strategy."""

    # --- Selection thresholds ---
    min_score: int = 6
    rsi_buy_threshold: float = 35.0
    rsi_sell_threshold: float = 75.0
    r2_min: float = 0.5
    slope_min: float = 0.5  # daily %
    volume_ratio_min: float = 1.2

    # --- Execution ---
    hold_days: int = 3
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 20.0
    max_positions: int = 2

    # --- Golden dip specific ---
    dip_threshold_pct: float = 10.0  # pullback from high
    r2_trend_min: float = 0.6  # min R² for bull stock confirmation

    # --- Scoring weights (must sum ≈ 1.0) ---
    w_momentum: float = 0.25
    w_mean_reversion: float = 0.20
    w_volume: float = 0.15
    w_trend: float = 0.25
    w_pattern: float = 0.15

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyDNA":
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# Valid ranges for each parameter — (min, max, is_int)
_PARAM_RANGES: Dict[str, Tuple[float, float, bool]] = {
    "min_score": (1, 10, True),
    "rsi_buy_threshold": (10.0, 50.0, False),
    "rsi_sell_threshold": (55.0, 95.0, False),
    "r2_min": (0.1, 0.95, False),
    "slope_min": (0.1, 3.0, False),
    "volume_ratio_min": (0.5, 5.0, False),
    "hold_days": (1, 20, True),
    "stop_loss_pct": (0.5, 10.0, False),
    "take_profit_pct": (3.0, 50.0, False),
    "max_positions": (1, 10, True),
    "dip_threshold_pct": (3.0, 30.0, False),
    "r2_trend_min": (0.2, 0.95, False),
    "w_momentum": (0.0, 1.0, False),
    "w_mean_reversion": (0.0, 1.0, False),
    "w_volume": (0.0, 1.0, False),
    "w_trend": (0.0, 1.0, False),
    "w_pattern": (0.0, 1.0, False),
}


@dataclass
class EvolutionResult:
    """Result of one strategy evaluation."""

    dna: StrategyDNA
    annual_return: float
    max_drawdown: float
    win_rate: float
    sharpe: float
    calmar: float
    total_trades: int
    profit_factor: float
    fitness: float = 0.0

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "dna"}
        d["dna"] = self.dna.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "EvolutionResult":
        dna = StrategyDNA.from_dict(d.pop("dna"))
        return cls(dna=dna, **d)


def compute_rsi(closes: List[float], period: int = 14) -> List[float]:
    """Compute RSI indicator. Returns list same length as input (NaN-padded)."""
    rsi = [float("nan")] * len(closes)
    if len(closes) < period + 1:
        return rsi
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)

    return rsi


def compute_linear_regression(
    values: List[float], window: int = 20
) -> Tuple[List[float], List[float]]:
    """Compute rolling R² and slope over a window.

    Returns (r2_list, slope_list), same length as input, NaN-padded.
    Slope is expressed as daily % return.
    """
    n = len(values)
    r2_out = [float("nan")] * n
    slope_out = [float("nan")] * n

    if n < window:
        return r2_out, slope_out

    for i in range(window - 1, n):
        segment = values[i - window + 1 : i + 1]
        mean_y = sum(segment) / window
        mean_x = (window - 1) / 2.0

        ss_xy = 0.0
        ss_xx = 0.0
        ss_yy = 0.0
        for j, y in enumerate(segment):
            dx = j - mean_x
            dy = y - mean_y
            ss_xy += dx * dy
            ss_xx += dx * dx
            ss_yy += dy * dy

        if ss_xx == 0 or ss_yy == 0:
            r2_out[i] = 0.0
            slope_out[i] = 0.0
            continue

        slope = ss_xy / ss_xx
        r2 = (ss_xy * ss_xy) / (ss_xx * ss_yy)
        # daily % slope relative to mean price
        slope_pct = (slope / mean_y) * 100.0 if mean_y != 0 else 0.0

        r2_out[i] = max(0.0, min(1.0, r2))
        slope_out[i] = slope_pct

    return r2_out, slope_out


def compute_volume_ratio(volumes: List[float], period: int = 20) -> List[float]:
    """Compute rolling volume ratio (current / average of past N days)."""
    n = len(volumes)
    ratios = [float("nan")] * n
    if n < period + 1:
        return ratios
    for i in range(period, n):
        avg = sum(volumes[i - period : i]) / period
        ratios[i] = volumes[i] / avg if avg > 0 else 0.0
    return ratios


def score_stock(
    idx: int,
    rsi: List[float],
    r2: List[float],
    slope: List[float],
    volume_ratio: List[float],
    closes: List[float],
    dna: StrategyDNA,
) -> float:
    """Score a stock at a given index using DNA weights.

    Returns score in [0, 10] range.
    """
    if any(
        math.isnan(x)
        for x in [rsi[idx], r2[idx], slope[idx], volume_ratio[idx]]
    ):
        return 0.0

    # Momentum: higher slope = better
    momentum_raw = min(slope[idx] / max(dna.slope_min, 0.01), 2.0) / 2.0

    # Mean reversion: RSI near buy threshold is good
    rsi_val = rsi[idx]
    if rsi_val <= dna.rsi_buy_threshold:
        mr_raw = 1.0
    elif rsi_val >= dna.rsi_sell_threshold:
        mr_raw = 0.0
    else:
        rng = dna.rsi_sell_threshold - dna.rsi_buy_threshold
        mr_raw = 1.0 - (rsi_val - dna.rsi_buy_threshold) / rng if rng > 0 else 0.5

    # Volume: higher ratio = better
    vol_raw = min(volume_ratio[idx] / max(dna.volume_ratio_min, 0.01), 2.0) / 2.0

    # Trend: R² + positive slope
    trend_raw = r2[idx] if slope[idx] > 0 else r2[idx] * 0.3

    # Pattern: golden dip — pullback from recent high
    lookback = min(20, idx)
    if lookback > 0:
        recent_high = max(closes[idx - lookback : idx])
        pullback = (recent_high - closes[idx]) / recent_high * 100 if recent_high > 0 else 0
        if pullback >= dna.dip_threshold_pct * 0.5 and r2[idx] >= dna.r2_trend_min:
            pattern_raw = min(pullback / dna.dip_threshold_pct, 1.0)
        else:
            pattern_raw = 0.0
    else:
        pattern_raw = 0.0

    # Weighted sum
    raw = (
        dna.w_momentum * momentum_raw
        + dna.w_mean_reversion * mr_raw
        + dna.w_volume * vol_raw
        + dna.w_trend * trend_raw
        + dna.w_pattern * pattern_raw
    )

    total_weight = (
        dna.w_momentum + dna.w_mean_reversion + dna.w_volume + dna.w_trend + dna.w_pattern
    )
    if total_weight > 0:
        raw /= total_weight

    return raw * 10.0


def compute_fitness(
    annual_return: float,
    max_drawdown: float,
    win_rate: float,
    sharpe: float,
) -> float:
    """Compute composite fitness score.

    fitness = annual_return * sqrt(win_rate) / max(max_drawdown, 5.0) * sharpe_bonus

    Rewards: high return, high win rate, low drawdown, good Sharpe.
    """
    dd_denom = max(max_drawdown, 5.0)
    win_factor = math.sqrt(max(win_rate, 0.0))
    sharpe_bonus = 1.0 + max(sharpe, 0.0) * 0.2
    return annual_return * win_factor / dd_denom * sharpe_bonus


class AutoEvolver:
    """Automatic strategy parameter evolution engine.

    Pure genetic-algorithm approach: mutate numerical parameters,
    backtest on local CSV data, keep the fittest.
    """

    def __init__(
        self,
        data_dir: str,
        population_size: int = 30,
        elite_count: int = 5,
        mutation_rate: float = 0.3,
        results_dir: str = "evolution_results",
        seed: Optional[int] = None,
    ):
        self.data_dir = data_dir
        self.population_size = population_size
        self.elite_count = elite_count
        self.mutation_rate = mutation_rate
        self.results_dir = results_dir
        self.rng = random.Random(seed)
        os.makedirs(results_dir, exist_ok=True)

    def load_data(self) -> Dict[str, Dict[str, list]]:
        """Load stock CSV data into memory.

        Returns dict: code -> {date, open, high, low, close, volume}
        Only loads stocks with enough data (>= 60 trading days).
        """
        data: Dict[str, Dict[str, list]] = {}
        data_path = Path(self.data_dir)

        if not data_path.exists():
            return data

        csv_files = list(data_path.glob("*.csv"))
        for fp in csv_files:
            try:
                lines = fp.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) < 2:
                    continue

                header = lines[0].strip().split(",")
                col_map = {h.strip(): i for i, h in enumerate(header)}

                # Required columns
                required = {"date", "open", "high", "low", "close", "volume"}
                if not required.issubset(col_map.keys()):
                    continue

                dates = []
                opens = []
                highs = []
                lows = []
                closes = []
                volumes = []

                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if len(parts) > max(col_map.values()):
                        try:
                            dates.append(parts[col_map["date"]])
                            opens.append(float(parts[col_map["open"]]))
                            highs.append(float(parts[col_map["high"]]))
                            lows.append(float(parts[col_map["low"]]))
                            closes.append(float(parts[col_map["close"]]))
                            volumes.append(float(parts[col_map["volume"]]))
                        except (ValueError, IndexError):
                            continue

                if len(closes) >= 60:
                    code = fp.stem
                    data[code] = {
                        "date": dates,
                        "open": opens,
                        "high": highs,
                        "low": lows,
                        "close": closes,
                        "volume": volumes,
                    }
            except Exception:
                continue

        return data

    def mutate(self, dna: StrategyDNA) -> StrategyDNA:
        """Create a mutated copy of a strategy DNA.

        Each parameter has ``mutation_rate`` chance of being modified.
        Mutation amount: ±10-30% of current value, clamped to valid ranges.
        """
        d = dna.to_dict()
        for param, (lo, hi, is_int) in _PARAM_RANGES.items():
            if self.rng.random() < self.mutation_rate:
                val = d[param]
                # ±10-30%
                pct = self.rng.uniform(0.10, 0.30)
                direction = self.rng.choice([-1, 1])
                delta = val * pct * direction
                # Minimum absolute delta so small values still move
                if abs(delta) < 0.01:
                    delta = 0.01 * direction
                new_val = val + delta
                new_val = max(lo, min(hi, new_val))
                if is_int:
                    new_val = int(round(new_val))
                d[param] = new_val

        # Normalize scoring weights so they sum ≈ 1.0
        w_keys = ["w_momentum", "w_mean_reversion", "w_volume", "w_trend", "w_pattern"]
        w_sum = sum(d[k] for k in w_keys)
        if w_sum > 0:
            for k in w_keys:
                d[k] = round(d[k] / w_sum, 4)

        return StrategyDNA.from_dict(d)

    def crossover(self, dna1: StrategyDNA, dna2: StrategyDNA) -> StrategyDNA:
        """Combine two strategies by randomly picking parameters from each parent."""
        d1 = dna1.to_dict()
        d2 = dna2.to_dict()
        child = {}
        for key in d1:
            child[key] = d1[key] if self.rng.random() < 0.5 else d2[key]

        # Normalize weights
        w_keys = ["w_momentum", "w_mean_reversion", "w_volume", "w_trend", "w_pattern"]
        w_sum = sum(child[k] for k in w_keys)
        if w_sum > 0:
            for k in w_keys:
                child[k] = round(child[k] / w_sum, 4)

        return StrategyDNA.from_dict(child)

    def evaluate(
        self,
        dna: StrategyDNA,
        data: Dict[str, Dict[str, list]],
        sample_size: int = 200,
    ) -> EvolutionResult:
        """Backtest a strategy on loaded data.

        For speed, evaluates on a random sample of ``sample_size`` stocks.
        Simplified but correct backtesting:
        - Every hold_days: score all stocks → pick top max_positions
        - T+1 open price entry
        - Check stop-loss / take-profit during holding period
        - Exit at end of hold period
        - Compute annual return, drawdown, win rate, Sharpe, Calmar

        Args:
            dna: Strategy parameters
            data: Stock data dict from load_data()
            sample_size: Max stocks to evaluate (for speed)

        Returns:
            EvolutionResult with all metrics
        """
        if not data:
            return EvolutionResult(
                dna=dna,
                annual_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                sharpe=0.0,
                calmar=0.0,
                total_trades=0,
                profit_factor=0.0,
                fitness=0.0,
            )

        # Sample stocks for speed
        codes = list(data.keys())
        if len(codes) > sample_size:
            codes = self.rng.sample(codes, sample_size)

        # Pre-compute indicators per stock
        indicators: Dict[str, Dict[str, list]] = {}
        for code in codes:
            sd = data[code]
            closes = sd["close"]
            vols = sd["volume"]
            rsi = compute_rsi(closes)
            r2, slope = compute_linear_regression(closes)
            vol_ratio = compute_volume_ratio(vols)
            indicators[code] = {
                "rsi": rsi,
                "r2": r2,
                "slope": slope,
                "volume_ratio": vol_ratio,
            }

        # Find common date range — use the first stock to determine day count
        first_code = codes[0]
        total_days = len(data[first_code]["close"])

        # Portfolio simulation
        initial_capital = 1_000_000.0
        capital = initial_capital
        portfolio_values = [capital]

        trades: List[float] = []  # list of trade returns (%)
        gross_profit = 0.0
        gross_loss = 0.0

        hold_days = max(1, dna.hold_days)
        day = 30  # skip first 30 days for indicator warmup

        while day < total_days - hold_days - 1:
            # Score all stocks at this day
            scored: List[Tuple[str, float]] = []
            for code in codes:
                sd = data[code]
                if day >= len(sd["close"]):
                    continue
                ind = indicators[code]
                s = score_stock(
                    day,
                    ind["rsi"],
                    ind["r2"],
                    ind["slope"],
                    ind["volume_ratio"],
                    sd["close"],
                    dna,
                )
                if s >= dna.min_score:
                    scored.append((code, s))

            # Pick top max_positions
            scored.sort(key=lambda x: x[1], reverse=True)
            picks = scored[: dna.max_positions]

            if picks:
                # Allocate capital equally
                per_pos = capital / len(picks)

                for code, _score in picks:
                    sd = data[code]
                    entry_day = day + 1  # T+1

                    if entry_day >= len(sd["open"]):
                        continue

                    entry_price = sd["open"][entry_day]
                    if entry_price <= 0:
                        continue

                    shares = per_pos / entry_price
                    exit_price = entry_price  # default

                    # Hold period with SL/TP check
                    for d in range(entry_day, min(entry_day + hold_days, len(sd["close"]))):
                        low = sd["low"][d]
                        high = sd["high"][d]

                        # Stop loss
                        sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                        if low <= sl_price:
                            exit_price = sl_price
                            break

                        # Take profit
                        tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                        if high >= tp_price:
                            exit_price = tp_price
                            break

                        exit_price = sd["close"][d]

                    trade_return = (exit_price - entry_price) / entry_price * 100
                    trades.append(trade_return)

                    pnl = shares * (exit_price - entry_price)
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

                    capital += pnl

            portfolio_values.append(max(capital, 0.01))  # avoid zero

            day += hold_days

        # Compute metrics
        total_trades = len(trades)
        win_rate = 0.0
        if total_trades > 0:
            wins = sum(1 for t in trades if t > 0)
            win_rate = wins / total_trades * 100

        # Annual return
        if len(portfolio_values) > 1 and portfolio_values[0] > 0:
            total_return = portfolio_values[-1] / portfolio_values[0] - 1
            # Assume ~250 trading days per year
            trading_days_used = total_days - 30
            years = trading_days_used / 250 if trading_days_used > 0 else 1
            if total_return > -1:
                annual_return = ((1 + total_return) ** (1 / max(years, 0.01)) - 1) * 100
            else:
                annual_return = -100.0
        else:
            annual_return = 0.0

        # Max drawdown
        max_drawdown = 0.0
        peak = portfolio_values[0]
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, dd)

        # Sharpe ratio (daily returns → annualized)
        sharpe = 0.0
        if len(portfolio_values) > 2:
            daily_returns = [
                (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
                for i in range(1, len(portfolio_values))
                if portfolio_values[i - 1] > 0
            ]
            if daily_returns:
                mean_r = sum(daily_returns) / len(daily_returns)
                var_r = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
                std_r = math.sqrt(var_r) if var_r > 0 else 0.001
                # Annualize: each "period" is hold_days trading days
                periods_per_year = 250 / max(hold_days, 1)
                sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

        # Calmar ratio
        calmar = annual_return / max(max_drawdown, 1.0)

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

        fitness = compute_fitness(annual_return, max_drawdown, win_rate, sharpe)

        return EvolutionResult(
            dna=dna,
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(win_rate, 4),
            sharpe=round(sharpe, 4),
            calmar=round(calmar, 4),
            total_trades=total_trades,
            profit_factor=round(profit_factor, 4),
            fitness=round(fitness, 4),
        )

    def run_generation(
        self,
        parents: List[StrategyDNA],
        data: Dict[str, Dict[str, list]],
    ) -> List[EvolutionResult]:
        """Run one generation of evolution.

        1. Generate mutations + crossovers from parents
        2. Evaluate all candidates
        3. Sort by fitness
        4. Return top ``elite_count`` results
        """
        candidates: List[StrategyDNA] = list(parents)

        while len(candidates) < self.population_size:
            parent = self.rng.choice(parents)
            if self.rng.random() < 0.7:
                # Mutation
                child = self.mutate(parent)
            else:
                # Crossover
                other = self.rng.choice(parents)
                child = self.crossover(parent, other)
                child = self.mutate(child)  # mutate after crossover
            candidates.append(child)

        results = [self.evaluate(dna, data) for dna in candidates]
        results.sort(key=lambda r: r.fitness, reverse=True)
        return results[: self.elite_count]

    def evolve(self, generations: int = 100, save_interval: int = 10) -> List[EvolutionResult]:
        """Main evolution loop.

        - Loads data once
        - Optionally resumes from saved results
        - Runs ``generations`` generations
        - Saves best results every ``save_interval`` gens
        - Prints progress each generation

        Returns:
            Final top results
        """
        print("=" * 60)
        print("🦀 FinClaw Auto Evolution Engine")
        print("=" * 60)

        t0 = time.time()
        print("Loading market data...", flush=True)
        data = self.load_data()
        elapsed = time.time() - t0
        print(f"Loaded {len(data)} stocks in {elapsed:.1f}s")

        if not data:
            print("ERROR: No data loaded. Check data_dir path.")
            return []

        # Try to resume from saved results
        parents = self._load_parents()
        start_gen = self._load_start_gen()
        if parents:
            print(f"Resuming from generation {start_gen} with {len(parents)} elite strategies")
        else:
            parents = [StrategyDNA()]  # default seed
            start_gen = 0
            print("Starting fresh with default strategy DNA")

        print(f"Population: {self.population_size} | Elite: {self.elite_count} | "
              f"Mutation rate: {self.mutation_rate}")
        print("-" * 60)

        best_results: List[EvolutionResult] = []

        for gen in range(start_gen, start_gen + generations):
            gen_t0 = time.time()
            results = self.run_generation(parents, data)
            gen_time = time.time() - gen_t0

            best = results[0]
            best_results = results

            print(
                f"Gen {gen:4d} | "
                f"fitness={best.fitness:8.2f} | "
                f"return={best.annual_return:7.2f}% | "
                f"dd={best.max_drawdown:5.2f}% | "
                f"wr={best.win_rate:5.1f}% | "
                f"sharpe={best.sharpe:5.2f} | "
                f"trades={best.total_trades:4d} | "
                f"{gen_time:.1f}s"
            )

            # Update parents for next generation
            parents = [r.dna for r in results]

            # Periodic save
            if (gen + 1) % save_interval == 0 or gen == start_gen + generations - 1:
                self.save_results(gen, results)

        total_time = time.time() - t0
        print("-" * 60)
        print(f"Evolution complete! {generations} generations in {total_time:.1f}s")
        if best_results:
            print(f"Best fitness: {best_results[0].fitness:.4f}")
            print(f"Best DNA: {best_results[0].dna.to_dict()}")
        print("=" * 60)

        return best_results

    def save_results(self, gen: int, best: List[EvolutionResult]) -> None:
        """Save best strategies to JSON for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        payload = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "results": [r.to_dict() for r in best],
        }
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # Also save a versioned copy
        versioned = os.path.join(self.results_dir, f"gen_{gen:04d}.json")
        with open(versioned, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load_best(self) -> Optional[StrategyDNA]:
        """Load the best known strategy from saved results."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return None
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", [])
        if not results:
            return None
        return StrategyDNA.from_dict(results[0]["dna"])

    def _load_parents(self) -> List[StrategyDNA]:
        """Load elite parents from previous run for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return []
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [StrategyDNA.from_dict(r["dna"]) for r in data.get("results", [])]
        except Exception:
            return []

    def _load_start_gen(self) -> int:
        """Get last completed generation for resumption."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return 0
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("generation", 0) + 1
        except Exception:
            return 0
