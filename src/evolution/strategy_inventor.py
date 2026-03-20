"""
Strategy Inventor - Automatically discover new trading rules
==============================================================
Instead of just tuning parameters on a fixed strategy,
this system combines modular "rule blocks" to create entirely new strategies.

Rule blocks are simple conditions like:
- "RSI < 30" (buy signal)
- "volume > 2x avg" (confirmation)
- "price > MA20" (trend filter)
- "BB width < 10th percentile" (squeeze)
- "3 consecutive red candles" (pattern)

The system:
1. Starts with a library of ~30 rule blocks
2. Randomly combines 3-5 blocks into a strategy
3. Backtests the combination
4. Keeps the best, mutates (swap/add/remove blocks)
5. Discovers which combinations work best
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RuleBlock:
    """A single trading rule/condition."""

    name: str
    category: str  # "entry", "exit", "filter", "confirmation"
    evaluate: Callable  # (closes, highs, lows, opens, volumes, idx) -> bool
    description: str


@dataclass
class CompositeStrategy:
    """A strategy assembled from multiple rule blocks."""

    name: str
    entry_rules: List[str]  # ALL must be true to buy
    filter_rules: List[str]  # ALL must be true (pre-filter)
    exit_rules: List[str]  # ANY triggers sell
    hold_days: int = 3
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 15.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CompositeStrategy":
        return cls(**d)


@dataclass
class InventionResult:
    """Result of backtesting a composite strategy."""

    strategy: CompositeStrategy
    annual_return: float
    max_drawdown: float
    win_rate: float
    sharpe: float
    total_trades: int
    fitness: float

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "strategy"}
        d["strategy"] = self.strategy.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "InventionResult":
        strat = CompositeStrategy.from_dict(d.pop("strategy"))
        return cls(strategy=strat, **d)


# ---------------------------------------------------------------------------
# Helper indicators (standalone, used by rule lambdas via StrategyInventor)
# ---------------------------------------------------------------------------


def _rsi(c: np.ndarray, i: int, period: int = 14) -> float:
    """Calculate RSI at index *i*."""
    if i < period:
        return 50.0
    deltas = np.diff(c[max(0, i - period) : i + 1])
    gains = float(np.mean(np.where(deltas > 0, deltas, 0)))
    losses = float(np.mean(np.where(deltas < 0, -deltas, 0)))
    rs = gains / (losses + 1e-10)
    return 100.0 - 100.0 / (1.0 + rs)


def _ma_cross(c: np.ndarray, i: int, short: int, long: int) -> bool:
    if i < long + 1:
        return False
    ma_s_now = float(np.mean(c[i - short + 1 : i + 1]))
    ma_l_now = float(np.mean(c[i - long + 1 : i + 1]))
    ma_s_prev = float(np.mean(c[i - short : i]))
    ma_l_prev = float(np.mean(c[i - long : i]))
    return ma_s_now > ma_l_now and ma_s_prev <= ma_l_prev


def _is_hammer(o: float, h: float, l: float, c: float) -> bool:
    body = abs(c - o)
    lower_wick = min(o, c) - l
    return lower_wick > body * 2 and body > 0


def _bb_squeeze(c: np.ndarray, i: int, window: int = 20) -> bool:
    if i < window + 20:
        return False
    std_now = float(np.std(c[i - window + 1 : i + 1]))
    stds = [float(np.std(c[i - window - j : i - j])) for j in range(1, min(20, i - window))]
    if not stds:
        return False
    return std_now < float(np.percentile(stds, 20))


def _at_lower_bb(c: np.ndarray, i: int, window: int = 20) -> bool:
    if i < window:
        return False
    ma = float(np.mean(c[i - window + 1 : i + 1]))
    std = float(np.std(c[i - window + 1 : i + 1]))
    return c[i] < ma - 1.5 * std


def _pullback(c: np.ndarray, h: np.ndarray, i: int, pct: float) -> bool:
    if i < 20:
        return False
    recent_high = float(np.max(h[max(0, i - 20) : i + 1]))
    if recent_high == 0:
        return False
    return (recent_high - c[i]) / recent_high >= pct


# ---------------------------------------------------------------------------
# Rule library builder  (free function so tests can call it independently)
# ---------------------------------------------------------------------------


def build_rule_library() -> Dict[str, RuleBlock]:
    """Build a library of ~30 composable rule blocks."""
    rules: Dict[str, RuleBlock] = {}

    # === ENTRY SIGNALS ===
    # RSI variants
    rules["rsi_below_30"] = RuleBlock(
        "RSI<30", "entry",
        lambda c, h, l, o, v, i: _rsi(c, i) < 30,
        "RSI oversold",
    )
    rules["rsi_below_40"] = RuleBlock(
        "RSI<40", "entry",
        lambda c, h, l, o, v, i: _rsi(c, i) < 40,
        "RSI approaching oversold",
    )
    rules["rsi_cross_30_up"] = RuleBlock(
        "RSI crosses above 30", "entry",
        lambda c, h, l, o, v, i: _rsi(c, i) > 30 and _rsi(c, i - 1) <= 30,
        "RSI bounce from oversold",
    )

    # Moving average signals
    rules["price_above_ma5"] = RuleBlock(
        "Price>MA5", "entry",
        lambda c, h, l, o, v, i: c[i] > float(np.mean(c[max(0, i - 4) : i + 1])),
        "Short-term bullish",
    )
    rules["price_above_ma20"] = RuleBlock(
        "Price>MA20", "filter",
        lambda c, h, l, o, v, i: (
            c[i] > float(np.mean(c[max(0, i - 19) : i + 1])) if i >= 19 else False
        ),
        "Medium-term bullish",
    )
    rules["ma5_above_ma20"] = RuleBlock(
        "MA5>MA20", "filter",
        lambda c, h, l, o, v, i: (
            float(np.mean(c[max(0, i - 4) : i + 1]))
            > float(np.mean(c[max(0, i - 19) : i + 1]))
            if i >= 19
            else False
        ),
        "Trend alignment",
    )
    rules["golden_cross"] = RuleBlock(
        "MA5 crosses MA20", "entry",
        lambda c, h, l, o, v, i: _ma_cross(c, i, 5, 20),
        "Golden cross",
    )

    # Volume signals
    rules["volume_spike_2x"] = RuleBlock(
        "Vol>2x avg", "confirmation",
        lambda c, h, l, o, v, i: (
            v[i] > float(np.mean(v[max(0, i - 19) : i + 1])) * 2 if i >= 19 else False
        ),
        "Volume breakout",
    )
    rules["volume_spike_1_5x"] = RuleBlock(
        "Vol>1.5x avg", "confirmation",
        lambda c, h, l, o, v, i: (
            v[i] > float(np.mean(v[max(0, i - 19) : i + 1])) * 1.5 if i >= 19 else False
        ),
        "Volume increase",
    )
    rules["volume_shrink"] = RuleBlock(
        "Vol<0.5x avg", "entry",
        lambda c, h, l, o, v, i: (
            v[i] < float(np.mean(v[max(0, i - 19) : i + 1])) * 0.5 if i >= 19 else False
        ),
        "Volume dryup",
    )
    rules["volume_increasing_3d"] = RuleBlock(
        "3d vol increasing", "confirmation",
        lambda c, h, l, o, v, i: i >= 2 and v[i] > v[i - 1] > v[i - 2],
        "Accumulating",
    )

    # Pattern signals
    rules["3_red_candles"] = RuleBlock(
        "3 red candles", "entry",
        lambda c, h, l, o, v, i: (
            i >= 2 and c[i] < o[i] and c[i - 1] < o[i - 1] and c[i - 2] < o[i - 2]
        ),
        "Selloff exhaustion",
    )
    rules["hammer"] = RuleBlock(
        "Hammer", "entry",
        lambda c, h, l, o, v, i: _is_hammer(o[i], h[i], l[i], c[i]),
        "Bullish reversal",
    )
    rules["doji"] = RuleBlock(
        "Doji", "entry",
        lambda c, h, l, o, v, i: (
            abs(c[i] - o[i]) < (h[i] - l[i]) * 0.1 if h[i] != l[i] else False
        ),
        "Indecision",
    )
    rules["bullish_engulfing"] = RuleBlock(
        "Bullish engulfing", "entry",
        lambda c, h, l, o, v, i: (
            i >= 1
            and c[i] > o[i]
            and c[i - 1] < o[i - 1]
            and c[i] > o[i - 1]
            and o[i] < c[i - 1]
        ),
        "Reversal",
    )

    # Bollinger / squeeze
    rules["bb_squeeze"] = RuleBlock(
        "BB squeeze", "entry",
        lambda c, h, l, o, v, i: _bb_squeeze(c, i),
        "Volatility compression",
    )
    rules["price_at_lower_bb"] = RuleBlock(
        "Price at lower BB", "entry",
        lambda c, h, l, o, v, i: _at_lower_bb(c, i),
        "Mean reversion opportunity",
    )

    # Trend signals
    rules["new_20d_high"] = RuleBlock(
        "20d high", "entry",
        lambda c, h, l, o, v, i: (
            c[i] >= float(np.max(c[max(0, i - 19) : i + 1])) if i >= 19 else False
        ),
        "Breakout",
    )
    rules["pullback_from_high"] = RuleBlock(
        "10% pullback", "entry",
        lambda c, h, l, o, v, i: _pullback(c, h, i, 0.10),
        "Buy the dip",
    )
    rules["uptrend_20d"] = RuleBlock(
        "20d uptrend", "filter",
        lambda c, h, l, o, v, i: (
            c[i] > c[max(0, i - 20)] * 1.05 if i >= 20 else False
        ),
        "Trending up",
    )

    # Gap signals
    rules["gap_up"] = RuleBlock(
        "Gap up", "entry",
        lambda c, h, l, o, v, i: i >= 1 and o[i] > c[i - 1] * 1.02,
        "Strong open",
    )
    rules["gap_down_recovery"] = RuleBlock(
        "Gap down then recover", "entry",
        lambda c, h, l, o, v, i: (
            i >= 1 and o[i] < c[i - 1] * 0.98 and c[i] > o[i]
        ),
        "Resilience",
    )

    # === EXIT SIGNALS ===
    rules["rsi_above_80"] = RuleBlock(
        "RSI>80", "exit",
        lambda c, h, l, o, v, i: _rsi(c, i) > 80,
        "Overbought",
    )
    rules["rsi_above_70"] = RuleBlock(
        "RSI>70", "exit",
        lambda c, h, l, o, v, i: _rsi(c, i) > 70,
        "Getting hot",
    )
    rules["price_below_ma5"] = RuleBlock(
        "Price<MA5", "exit",
        lambda c, h, l, o, v, i: c[i] < float(np.mean(c[max(0, i - 4) : i + 1])),
        "Short-term weakness",
    )
    rules["volume_climax"] = RuleBlock(
        "Volume climax", "exit",
        lambda c, h, l, o, v, i: (
            v[i] > float(np.mean(v[max(0, i - 19) : i + 1])) * 3 if i >= 19 else False
        ),
        "Blow off top",
    )
    rules["3_green_candles"] = RuleBlock(
        "3 green candles", "exit",
        lambda c, h, l, o, v, i: (
            i >= 2 and c[i] > o[i] and c[i - 1] > o[i - 1] and c[i - 2] > o[i - 2]
        ),
        "Take profit after run",
    )

    return rules


# ---------------------------------------------------------------------------
# StrategyInventor
# ---------------------------------------------------------------------------


class StrategyInventor:
    """Discover new trading strategies by combining modular rule blocks.

    Instead of tuning parameters of a fixed strategy (like AutoEvolver),
    this system assembles *new* strategies from a library of ~30 atomic
    rule blocks and evolves the *combinations* themselves.
    """

    def __init__(
        self,
        data_dir: str,
        results_dir: str = "invention_results",
        seed: Optional[int] = None,
    ):
        self.data_dir = data_dir
        self.results_dir = results_dir
        self.rng = random.Random(seed)
        self.rule_library = build_rule_library()
        os.makedirs(results_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Strategy generation & mutation
    # ------------------------------------------------------------------

    def random_strategy(self) -> CompositeStrategy:
        """Create a random strategy by combining rule blocks."""
        entry_pool = [k for k, v in self.rule_library.items() if v.category == "entry"]
        filter_pool = [
            k
            for k, v in self.rule_library.items()
            if v.category in ("filter", "confirmation")
        ]
        exit_pool = [k for k, v in self.rule_library.items() if v.category == "exit"]

        n_entry = self.rng.randint(1, min(3, len(entry_pool)))
        n_filter = self.rng.randint(0, min(2, len(filter_pool)))
        n_exit = self.rng.randint(1, min(2, len(exit_pool)))

        entry_rules = self.rng.sample(entry_pool, n_entry)
        filter_rules = self.rng.sample(filter_pool, n_filter)
        exit_rules = self.rng.sample(exit_pool, n_exit)

        return CompositeStrategy(
            name="+".join(entry_rules[:2]),
            entry_rules=entry_rules,
            filter_rules=filter_rules,
            exit_rules=exit_rules,
            hold_days=self.rng.choice([2, 3, 5, 10]),
            stop_loss_pct=self.rng.choice([2, 3, 5, 7, 10]),
            take_profit_pct=self.rng.choice([5, 10, 15, 20, 30]),
        )

    def mutate_strategy(self, strategy: CompositeStrategy) -> CompositeStrategy:
        """Mutate: swap one rule, add/remove a rule, or adjust parameters."""
        s = copy.deepcopy(strategy)
        mutation = self.rng.choice(
            ["swap_entry", "swap_filter", "swap_exit", "add_rule", "remove_rule", "adjust_params"]
        )

        if mutation == "swap_entry" and s.entry_rules:
            idx = self.rng.randint(0, len(s.entry_rules) - 1)
            candidates = [
                k
                for k, v in self.rule_library.items()
                if v.category == "entry" and k not in s.entry_rules
            ]
            if candidates:
                s.entry_rules[idx] = self.rng.choice(candidates)

        elif mutation == "swap_filter":
            candidates = [
                k
                for k, v in self.rule_library.items()
                if v.category in ("filter", "confirmation") and k not in s.filter_rules
            ]
            if candidates:
                if s.filter_rules:
                    idx = self.rng.randint(0, len(s.filter_rules) - 1)
                    s.filter_rules[idx] = self.rng.choice(candidates)
                else:
                    s.filter_rules.append(self.rng.choice(candidates))

        elif mutation == "swap_exit" and s.exit_rules:
            idx = self.rng.randint(0, len(s.exit_rules) - 1)
            candidates = [
                k
                for k, v in self.rule_library.items()
                if v.category == "exit" and k not in s.exit_rules
            ]
            if candidates:
                s.exit_rules[idx] = self.rng.choice(candidates)

        elif mutation == "add_rule":
            # Add a rule to whichever category has room
            cat = self.rng.choice(["entry", "filter", "exit"])
            if cat == "entry" and len(s.entry_rules) < 4:
                pool = [
                    k
                    for k, v in self.rule_library.items()
                    if v.category == "entry" and k not in s.entry_rules
                ]
                if pool:
                    s.entry_rules.append(self.rng.choice(pool))
            elif cat == "filter" and len(s.filter_rules) < 3:
                pool = [
                    k
                    for k, v in self.rule_library.items()
                    if v.category in ("filter", "confirmation")
                    and k not in s.filter_rules
                ]
                if pool:
                    s.filter_rules.append(self.rng.choice(pool))
            elif cat == "exit" and len(s.exit_rules) < 3:
                pool = [
                    k
                    for k, v in self.rule_library.items()
                    if v.category == "exit" and k not in s.exit_rules
                ]
                if pool:
                    s.exit_rules.append(self.rng.choice(pool))

        elif mutation == "remove_rule":
            # Remove a random rule (keep at least 1 entry, 1 exit)
            options = []
            if len(s.entry_rules) > 1:
                options.append("entry")
            if s.filter_rules:
                options.append("filter")
            if len(s.exit_rules) > 1:
                options.append("exit")
            if options:
                cat = self.rng.choice(options)
                if cat == "entry":
                    s.entry_rules.pop(self.rng.randint(0, len(s.entry_rules) - 1))
                elif cat == "filter":
                    s.filter_rules.pop(self.rng.randint(0, len(s.filter_rules) - 1))
                else:
                    s.exit_rules.pop(self.rng.randint(0, len(s.exit_rules) - 1))

        else:  # adjust_params
            s.hold_days = max(2, s.hold_days + self.rng.choice([-1, 0, 1]))
            s.stop_loss_pct = max(1, min(15, s.stop_loss_pct + self.rng.uniform(-2, 2)))
            s.take_profit_pct = max(3, min(50, s.take_profit_pct + self.rng.uniform(-5, 5)))

        s.name = "+".join(s.entry_rules[:2])
        return s

    def crossover(
        self, a: CompositeStrategy, b: CompositeStrategy
    ) -> CompositeStrategy:
        """Combine rules from two parent strategies."""
        # Merge entry rules: take some from each parent, deduplicate
        all_entry = list(set(a.entry_rules + b.entry_rules))
        n_entry = self.rng.randint(1, min(3, len(all_entry)))
        entry_rules = self.rng.sample(all_entry, n_entry)

        all_filter = list(set(a.filter_rules + b.filter_rules))
        n_filter = self.rng.randint(0, min(2, len(all_filter))) if all_filter else 0
        filter_rules = self.rng.sample(all_filter, n_filter) if all_filter else []

        all_exit = list(set(a.exit_rules + b.exit_rules))
        n_exit = self.rng.randint(1, min(2, len(all_exit)))
        exit_rules = self.rng.sample(all_exit, n_exit)

        return CompositeStrategy(
            name="+".join(entry_rules[:2]),
            entry_rules=entry_rules,
            filter_rules=filter_rules,
            exit_rules=exit_rules,
            hold_days=self.rng.choice([a.hold_days, b.hold_days]),
            stop_loss_pct=self.rng.choice([a.stop_loss_pct, b.stop_loss_pct]),
            take_profit_pct=self.rng.choice([a.take_profit_pct, b.take_profit_pct]),
        )

    # ------------------------------------------------------------------
    # Data loading (reuses CSV format from auto_evolve)
    # ------------------------------------------------------------------

    def load_data(self) -> Dict[str, Dict[str, np.ndarray]]:
        """Load stock CSV data into numpy arrays.

        Returns dict: code -> {date, open, high, low, close, volume}
        Only loads stocks with >= 60 trading days.
        """
        data: Dict[str, Dict[str, np.ndarray]] = {}
        data_path = Path(self.data_dir)

        if not data_path.exists():
            return data

        for fp in data_path.glob("*.csv"):
            try:
                lines = fp.read_text(encoding="utf-8").strip().split("\n")
                if len(lines) < 2:
                    continue

                header = lines[0].strip().split(",")
                col_map = {h.strip(): idx for idx, h in enumerate(header)}
                required = {"date", "open", "high", "low", "close", "volume"}
                if not required.issubset(col_map.keys()):
                    continue

                dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
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
                    data[fp.stem] = {
                        "date": dates,
                        "open": np.array(opens),
                        "high": np.array(highs),
                        "low": np.array(lows),
                        "close": np.array(closes),
                        "volume": np.array(volumes),
                    }
            except Exception:
                continue
        return data

    # ------------------------------------------------------------------
    # Backtesting
    # ------------------------------------------------------------------

    def _evaluate_rules(
        self,
        rule_keys: List[str],
        c: np.ndarray,
        h: np.ndarray,
        l: np.ndarray,
        o: np.ndarray,
        v: np.ndarray,
        idx: int,
        mode: str = "all",
    ) -> bool:
        """Evaluate a list of rule blocks.

        mode='all': all must be True (AND logic — entry/filter).
        mode='any': any must be True (OR logic — exit).
        """
        results = []
        for key in rule_keys:
            rule = self.rule_library.get(key)
            if rule is None:
                results.append(False)
                continue
            try:
                results.append(bool(rule.evaluate(c, h, l, o, v, idx)))
            except Exception:
                results.append(False)

        if not results:
            return mode == "all"  # no rules = pass for filters, fail for exits

        if mode == "all":
            return all(results)
        return any(results)

    def backtest_strategy(
        self,
        strategy: CompositeStrategy,
        data: Dict[str, Dict[str, np.ndarray]],
        sample_size: int = 200,
    ) -> InventionResult:
        """Backtest a composite strategy on local data with A-share rules.

        A-share constraints:
        - T+1: cannot sell on the same day you bought
        - 涨停 (limit-up): cannot buy if stock opens at limit-up
        - 跌停 (limit-down): cannot sell if stock is at limit-down
        - Commission: 0.1% round-trip
        """
        if not data:
            return InventionResult(
                strategy=strategy,
                annual_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                sharpe=0.0,
                total_trades=0,
                fitness=0.0,
            )

        codes = list(data.keys())
        if len(codes) > sample_size:
            codes = self.rng.sample(codes, sample_size)

        initial_capital = 1_000_000.0
        capital = initial_capital
        portfolio_values = [capital]
        trades: List[float] = []  # per-trade return %

        hold_days = max(2, strategy.hold_days)  # A-share T+1 minimum
        commission_rate = 0.001  # 0.1%

        # Use first stock to determine total days (approximate)
        first_code = codes[0]
        total_days = len(data[first_code]["close"])

        day = 30  # skip warmup

        while day < total_days - hold_days - 1:
            # Score: check entry+filter rules on each stock
            picks: List[str] = []
            for code in codes:
                sd = data[code]
                if day >= len(sd["close"]):
                    continue
                c, h_arr, l_arr, o_arr, v = (
                    sd["close"],
                    sd["high"],
                    sd["low"],
                    sd["open"],
                    sd["volume"],
                )

                # All entry rules must fire
                entry_ok = self._evaluate_rules(
                    strategy.entry_rules, c, h_arr, l_arr, o_arr, v, day, mode="all"
                )
                if not entry_ok:
                    continue

                # All filters must pass
                filter_ok = self._evaluate_rules(
                    strategy.filter_rules, c, h_arr, l_arr, o_arr, v, day, mode="all"
                )
                if not filter_ok:
                    continue

                picks.append(code)

            # Limit positions
            max_positions = 5
            if len(picks) > max_positions:
                picks = self.rng.sample(picks, max_positions)

            if picks:
                per_pos = capital / len(picks)

                for code in picks:
                    sd = data[code]
                    entry_day = day + 1  # T+1

                    if entry_day >= len(sd["open"]):
                        continue

                    entry_price = sd["open"][entry_day]
                    if entry_price <= 0:
                        continue

                    # Limit-up check: can't buy if open at limit-up
                    if entry_day >= 1:
                        prev_close = sd["close"][entry_day - 1]
                        if prev_close > 0:
                            code_str = code.replace("_", ".")
                            limit_pct = (
                                0.20
                                if code_str.startswith("sh.688")
                                or code_str.startswith("sz.3")
                                else 0.10
                            )
                            if entry_price >= prev_close * (1 + limit_pct - 0.005):
                                continue

                    shares = per_pos / entry_price
                    exit_price = entry_price

                    # Hold period with SL/TP + exit rules
                    for d in range(entry_day + 1, min(entry_day + hold_days, len(sd["close"]))):
                        c_arr = sd["close"]
                        h_arr = sd["high"]
                        l_arr = sd["low"]
                        o_arr = sd["open"]
                        v_arr = sd["volume"]

                        # Limit-down check
                        if d >= 1:
                            pc = c_arr[d - 1]
                            if pc > 0:
                                code_str = code.replace("_", ".")
                                lim = (
                                    0.20
                                    if code_str.startswith("sh.688")
                                    or code_str.startswith("sz.3")
                                    else 0.10
                                )
                                limit_down_price = pc * (1 - lim + 0.005)
                                if c_arr[d] <= limit_down_price and d < entry_day + hold_days - 1:
                                    continue  # can't sell, try next day

                        # Stop loss
                        sl_price = entry_price * (1 - strategy.stop_loss_pct / 100)
                        if l_arr[d] <= sl_price:
                            exit_price = sl_price
                            break

                        # Take profit
                        tp_price = entry_price * (1 + strategy.take_profit_pct / 100)
                        if h_arr[d] >= tp_price:
                            exit_price = tp_price
                            break

                        # Exit rules (ANY triggers sell)
                        if d < len(c_arr):
                            exit_signal = self._evaluate_rules(
                                strategy.exit_rules,
                                c_arr,
                                h_arr,
                                l_arr,
                                o_arr,
                                v_arr,
                                d,
                                mode="any",
                            )
                            if exit_signal:
                                exit_price = c_arr[d]
                                break

                        exit_price = c_arr[d]

                    # Commission
                    trade_return = (
                        (exit_price - entry_price) / entry_price * 100 - commission_rate * 100
                    )
                    trades.append(trade_return)

                    pnl = shares * (exit_price - entry_price) - shares * entry_price * commission_rate
                    capital += pnl

            portfolio_values.append(max(capital, 0.01))
            day += hold_days

        # --- Metrics ---
        total_trades = len(trades)
        win_rate = 0.0
        if total_trades > 0:
            wins = sum(1 for t in trades if t > 0)
            win_rate = wins / total_trades * 100

        # Annual return
        annual_return = 0.0
        if len(portfolio_values) > 1 and portfolio_values[0] > 0:
            total_return = portfolio_values[-1] / portfolio_values[0] - 1
            trading_days_used = total_days - 30
            years = trading_days_used / 250 if trading_days_used > 0 else 1
            if total_return > -1:
                annual_return = ((1 + total_return) ** (1 / max(years, 0.01)) - 1) * 100
            else:
                annual_return = -100.0

        # Max drawdown
        max_drawdown = 0.0
        peak = portfolio_values[0]
        for v_val in portfolio_values:
            if v_val > peak:
                peak = v_val
            dd = (peak - v_val) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, dd)

        # Sharpe
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
                periods_per_year = 250 / max(hold_days, 1)
                sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

        # Fitness
        fitness = _compute_invention_fitness(
            annual_return, max_drawdown, win_rate, sharpe, total_trades
        )

        return InventionResult(
            strategy=strategy,
            annual_return=round(annual_return, 4),
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(win_rate, 4),
            sharpe=round(sharpe, 4),
            total_trades=total_trades,
            fitness=round(fitness, 4),
        )

    # ------------------------------------------------------------------
    # Evolution loop
    # ------------------------------------------------------------------

    def invent(
        self,
        generations: int = 50,
        population: int = 20,
        elite_count: int = 5,
        save_interval: int = 10,
    ) -> List[InventionResult]:
        """Run the full invention loop.

        1. Generate random population of composite strategies
        2. Backtest all
        3. Keep elite, mutate/crossover to fill next generation
        4. Repeat for *generations*

        Returns the final elite results sorted by fitness.
        """
        print("=" * 60)
        print("🦀 FinClaw Strategy Inventor")
        print("=" * 60)

        t0 = time.time()
        print("Loading market data...", flush=True)
        data = self.load_data()
        elapsed = time.time() - t0
        print(f"Loaded {len(data)} stocks in {elapsed:.1f}s")

        if not data:
            print("ERROR: No data loaded. Check data_dir path.")
            return []

        # Initial random population
        pop: List[CompositeStrategy] = [self.random_strategy() for _ in range(population)]

        best_results: List[InventionResult] = []

        print(
            f"Population: {population} | Elite: {elite_count} | Generations: {generations}"
        )
        print("-" * 60)

        for gen in range(generations):
            gen_t0 = time.time()

            # Evaluate population
            results = [self.backtest_strategy(s, data) for s in pop]
            results.sort(key=lambda r: r.fitness, reverse=True)

            elite = results[:elite_count]
            best = elite[0]
            best_results = elite

            rule_desc = (
                f"E={best.strategy.entry_rules[:2]} "
                f"F={best.strategy.filter_rules[:1]} "
                f"X={best.strategy.exit_rules[:1]}"
            )
            print(
                f"Gen {gen:4d} | "
                f"fitness={best.fitness:8.2f} | "
                f"return={best.annual_return:7.2f}% | "
                f"dd={best.max_drawdown:5.2f}% | "
                f"wr={best.win_rate:5.1f}% | "
                f"sharpe={best.sharpe:5.2f} | "
                f"trades={best.total_trades:4d} | "
                f"{rule_desc} | "
                f"{time.time() - gen_t0:.1f}s"
            )

            # Save periodically
            if (gen + 1) % save_interval == 0 or gen == generations - 1:
                self._save_results(gen, elite)

            # Build next generation
            elite_strats = [r.strategy for r in elite]
            next_pop: List[CompositeStrategy] = list(elite_strats)

            while len(next_pop) < population:
                parent = self.rng.choice(elite_strats)
                if self.rng.random() < 0.6:
                    child = self.mutate_strategy(parent)
                elif self.rng.random() < 0.8:
                    other = self.rng.choice(elite_strats)
                    child = self.crossover(parent, other)
                    child = self.mutate_strategy(child)
                else:
                    # Inject fresh random blood to avoid local optima
                    child = self.random_strategy()
                next_pop.append(child)

            pop = next_pop

        total_time = time.time() - t0
        print("-" * 60)
        print(f"Invention complete! {generations} generations in {total_time:.1f}s")
        if best_results:
            best = best_results[0]
            print(f"Best fitness: {best.fitness:.4f}")
            print(f"Best strategy: {best.strategy.name}")
            print(f"  Entry:  {best.strategy.entry_rules}")
            print(f"  Filter: {best.strategy.filter_rules}")
            print(f"  Exit:   {best.strategy.exit_rules}")
            print(
                f"  Hold={best.strategy.hold_days}d "
                f"SL={best.strategy.stop_loss_pct}% "
                f"TP={best.strategy.take_profit_pct}%"
            )
        print("=" * 60)

        return best_results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_results(self, gen: int, results: List[InventionResult]) -> None:
        """Save elite strategies to JSON."""
        payload = {
            "generation": gen,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "results": [r.to_dict() for r in results],
        }
        latest = os.path.join(self.results_dir, "latest.json")
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        versioned = os.path.join(self.results_dir, f"gen_{gen:04d}.json")
        with open(versioned, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load_best(self) -> Optional[InventionResult]:
        """Load the best invention result from saved results."""
        result_file = os.path.join(self.results_dir, "latest.json")
        if not os.path.exists(result_file):
            return None
        try:
            with open(result_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            results = payload.get("results", [])
            if not results:
                return None
            return InventionResult.from_dict(results[0])
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Fitness function
# ---------------------------------------------------------------------------


def _compute_invention_fitness(
    annual_return: float,
    max_drawdown: float,
    win_rate: float,
    sharpe: float,
    total_trades: int,
) -> float:
    """Compute fitness for an invented strategy.

    Same philosophy as auto_evolve.compute_fitness but slightly different weights:
    - Heavier trade-count penalty (new strategies often produce few trades)
    - Sharpe bonus to reward consistency
    """
    dd_denom = max(max_drawdown, 5.0)
    win_factor = math.sqrt(max(win_rate, 0.0))
    sharpe_bonus = 1.0 + max(sharpe, 0.0) * 0.25

    if total_trades < 10:
        trade_penalty = 0.1
    elif total_trades < 30:
        trade_penalty = total_trades / 30.0
    elif total_trades < 50:
        trade_penalty = 0.8 + 0.2 * (total_trades - 30) / 20.0
    else:
        trade_penalty = 1.0

    return annual_return * win_factor / dd_denom * sharpe_bonus * trade_penalty
