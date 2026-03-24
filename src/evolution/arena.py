"""
Multi-DNA Arena Competition Module
====================================
Inspired by FinEvo: multiple DNA strategies compete in the same simulated
market simultaneously. When many DNAs buy/sell the same stock at the same
time, price impact is applied — rewarding strategies that work even under
crowded conditions and penalizing overfitted ones.

Key concepts:
  - TradingArena: simulates N DNAs trading on the same OHLCV data
  - Price impact: if >50% of DNAs buy simultaneously, price goes up 0.5%;
    if >50% sell simultaneously, price goes down 0.5%
  - ArenaResult: per-DNA performance summary with ranking
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ════════════════════════════════════════════════════════════════════
# ArenaResult — per-DNA performance summary
# ════════════════════════════════════════════════════════════════════

@dataclass
class ArenaResult:
    """Performance result for a single DNA in the arena."""

    dna_index: int
    final_value: float
    sharpe: float
    max_drawdown: float
    rank: int  # 1-based, 1 = best
    total_trades: int = 0
    win_rate: float = 0.0


# ════════════════════════════════════════════════════════════════════
# TradingArena — multi-DNA competition simulator
# ════════════════════════════════════════════════════════════════════

# Default signal weight keys (subset used in arena scoring)
_SIGNAL_WEIGHT_KEYS: List[str] = [
    "w_volume_breakout",
    "w_bottom_reversal",
    "w_macd_divergence",
    "w_ma_alignment",
    "w_low_volume_pullback",
    "w_nday_breakout",
    "w_momentum_confirmation",
    "w_three_soldiers",
    "w_long_lower_shadow",
    "w_doji_at_bottom",
    "w_volume_climax_reversal",
    "w_accumulation",
    "w_rsi_divergence",
    "w_squeeze_release",
    "w_adx_trend",
]


def _compute_simple_score(
    closes: np.ndarray,
    volumes: np.ndarray,
    idx: int,
    dna: Dict[str, Any],
) -> float:
    """Compute a simplified trading signal score using DNA weights.

    Uses a lightweight signal calculation based on price momentum,
    volume ratio, and MA alignment — weighted by the DNA's signal weights.
    This is intentionally simpler than the full cn_scanner to keep
    arena simulation fast.

    Returns a score roughly in [0, 10].
    """
    if idx < 25 or idx >= len(closes):
        return 0.0

    score = 0.0

    # Extract weights, defaulting to equal if missing
    weights = {}
    total_w = 0.0
    for key in _SIGNAL_WEIGHT_KEYS:
        w = float(dna.get(key, 1.0 / len(_SIGNAL_WEIGHT_KEYS)))
        weights[key] = w
        total_w += w
    if total_w > 0:
        for key in weights:
            weights[key] /= total_w

    # --- Signal 1: Momentum (5-day return) ---
    ret_5d = (closes[idx] / closes[idx - 5] - 1) * 100 if closes[idx - 5] > 0 else 0.0
    momentum_signal = max(0.0, min(10.0, 5.0 + ret_5d * 0.5))
    score += (weights.get("w_momentum_confirmation", 0.0) +
              weights.get("w_nday_breakout", 0.0)) * momentum_signal

    # --- Signal 2: Volume ratio ---
    avg_vol = np.mean(volumes[max(0, idx - 20):idx]) if idx >= 20 else np.mean(volumes[:idx])
    if avg_vol > 0:
        vol_ratio = volumes[idx] / avg_vol
        vol_signal = max(0.0, min(10.0, vol_ratio * 3.0))
    else:
        vol_signal = 0.0
    score += (weights.get("w_volume_breakout", 0.0) +
              weights.get("w_volume_climax_reversal", 0.0) +
              weights.get("w_accumulation", 0.0)) * vol_signal

    # --- Signal 3: MA alignment (close > MA5 > MA10 > MA20) ---
    ma5 = np.mean(closes[idx - 4:idx + 1])
    ma10 = np.mean(closes[idx - 9:idx + 1])
    ma20 = np.mean(closes[idx - 19:idx + 1])
    if closes[idx] > ma5 > ma10 > ma20:
        ma_signal = 7.0
    elif closes[idx] > ma10:
        ma_signal = 4.0
    else:
        ma_signal = 1.0
    score += weights.get("w_ma_alignment", 0.0) * ma_signal

    # --- Signal 4: RSI-like oversold ---
    if idx >= 14:
        diffs = np.diff(closes[idx - 14:idx + 1])
        gains = np.sum(diffs[diffs > 0])
        losses = -np.sum(diffs[diffs < 0])
        if losses > 0:
            rs = gains / losses
            rsi = 100 - 100 / (1 + rs)
        else:
            rsi = 100.0
        if rsi < 30:
            rsi_signal = 8.0
        elif rsi < 50:
            rsi_signal = 5.0
        else:
            rsi_signal = 2.0
    else:
        rsi_signal = 5.0
    score += (weights.get("w_bottom_reversal", 0.0) +
              weights.get("w_rsi_divergence", 0.0) +
              weights.get("w_doji_at_bottom", 0.0) +
              weights.get("w_long_lower_shadow", 0.0)) * rsi_signal

    # --- Signal 5: MACD-like trend ---
    if idx >= 26:
        ema12 = np.mean(closes[idx - 11:idx + 1])  # simplified
        ema26 = np.mean(closes[idx - 25:idx + 1])
        macd_val = ema12 - ema26
        if closes[idx] > 0:
            macd_signal = max(0.0, min(10.0, 5.0 + (macd_val / closes[idx]) * 500))
        else:
            macd_signal = 5.0
    else:
        macd_signal = 5.0
    score += (weights.get("w_macd_divergence", 0.0) +
              weights.get("w_adx_trend", 0.0) +
              weights.get("w_squeeze_release", 0.0)) * macd_signal

    # --- Remaining weights get a neutral score ---
    remaining_keys = {"w_low_volume_pullback", "w_three_soldiers"}
    for key in remaining_keys:
        score += weights.get(key, 0.0) * 5.0

    return max(0.0, min(10.0, score))


class TradingArena:
    """Simulates N DNAs competing on the same market data.

    Each DNA gets the same initial capital and trades the same stocks.
    When many DNAs act in the same direction simultaneously, price
    impact is applied — simulating market crowding effects.

    Parameters
    ----------
    dna_list : list of dict
        List of DNA parameter dictionaries (UnifiedDNA.to_dict() format).
    initial_capital : float
        Starting capital for each DNA (default: 1,000,000).
    impact_threshold : float
        Fraction of DNAs that must act in same direction to trigger
        price impact (default: 0.5 = 50%).
    impact_pct : float
        Price impact percentage when threshold is exceeded
        (default: 0.005 = 0.5%).
    """

    def __init__(
        self,
        dna_list: List[Dict[str, Any]],
        initial_capital: float = 1_000_000.0,
        impact_threshold: float = 0.5,
        impact_pct: float = 0.005,
    ):
        if not dna_list:
            raise ValueError("dna_list must contain at least one DNA")
        self.dna_list = dna_list
        self.n_dnas = len(dna_list)
        self.initial_capital = initial_capital
        self.impact_threshold = impact_threshold
        self.impact_pct = impact_pct

    def run(
        self,
        stock_data: Dict[str, Dict[str, Any]],
        step_size: int = 5,
    ) -> List[ArenaResult]:
        """Run the arena competition.

        Parameters
        ----------
        stock_data : dict
            Mapping of stock code -> {'close': list, 'volume': list, ...}.
            At minimum needs 'close' and 'volume' arrays.
        step_size : int
            Trading interval in days (default: 5 = weekly rebalance).

        Returns
        -------
        List of ArenaResult, one per DNA, sorted by rank (best first).
        """
        if not stock_data:
            return self._empty_results()

        # Initialize per-DNA state
        capitals = np.full(self.n_dnas, self.initial_capital)
        # Track positions: positions[dna_idx][stock_code] = num_shares
        positions: List[Dict[str, float]] = [{} for _ in range(self.n_dnas)]
        # Track portfolio value history for Sharpe/drawdown
        value_history: List[List[float]] = [[self.initial_capital] for _ in range(self.n_dnas)]
        # Trade counts and wins
        trade_counts = np.zeros(self.n_dnas, dtype=int)
        win_counts = np.zeros(self.n_dnas, dtype=int)

        # Determine data length from first stock
        codes = list(stock_data.keys())
        if not codes:
            return self._empty_results()

        # Prepare numpy arrays for each stock
        stock_arrays: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        data_length = 0
        for code in codes:
            sd = stock_data[code]
            closes_raw = sd.get("close", sd.get("closes", []))
            volumes_raw = sd.get("volume", sd.get("volumes", []))
            if not closes_raw or not volumes_raw:
                continue
            c = np.array(closes_raw, dtype=np.float64)
            v = np.array(volumes_raw, dtype=np.float64)
            if len(c) != len(v):
                min_len = min(len(c), len(v))
                c = c[:min_len]
                v = v[:min_len]
            stock_arrays[code] = (c, v)
            data_length = max(data_length, len(c))

        if not stock_arrays or data_length < 30:
            return self._empty_results()

        # Simulation loop
        warmup = 26  # Need enough history for signals
        for day in range(warmup, data_length - 1, step_size):
            # Phase 1: Collect each DNA's desired actions per stock
            # actions[code] = list of (dna_idx, action) where action is 'buy' or 'sell'
            actions_per_stock: Dict[str, List[Tuple[int, str]]] = {}

            for dna_idx in range(self.n_dnas):
                dna = self.dna_list[dna_idx]
                threshold = float(dna.get("min_score", 3.0))
                max_pos = int(dna.get("max_positions", 2))

                for code, (closes, volumes) in stock_arrays.items():
                    if day >= len(closes):
                        continue

                    score = _compute_simple_score(closes, volumes, day, dna)

                    has_position = code in positions[dna_idx] and positions[dna_idx][code] > 0

                    if score > threshold and not has_position:
                        # Want to buy
                        current_positions = sum(1 for s in positions[dna_idx].values() if s > 0)
                        if current_positions < max_pos:
                            if code not in actions_per_stock:
                                actions_per_stock[code] = []
                            actions_per_stock[code].append((dna_idx, "buy"))
                    elif has_position and score < threshold - 2:
                        # Want to sell
                        if code not in actions_per_stock:
                            actions_per_stock[code] = []
                        actions_per_stock[code].append((dna_idx, "sell"))

            # Phase 2: Apply price impact and execute trades
            for code, actions in actions_per_stock.items():
                closes, volumes = stock_arrays[code]
                if day + 1 >= len(closes):
                    continue

                base_price = closes[day]
                if base_price <= 0:
                    continue

                buy_count = sum(1 for _, a in actions if a == "buy")
                sell_count = sum(1 for _, a in actions if a == "sell")

                # Price impact
                effective_price = base_price
                if self.n_dnas > 1:
                    buy_frac = buy_count / self.n_dnas
                    sell_frac = sell_count / self.n_dnas
                    if buy_frac > self.impact_threshold:
                        effective_price *= (1 + self.impact_pct)
                    if sell_frac > self.impact_threshold:
                        effective_price *= (1 - self.impact_pct)

                # Execute trades
                for dna_idx, action in actions:
                    if action == "buy":
                        available = capitals[dna_idx]
                        max_pos = int(self.dna_list[dna_idx].get("max_positions", 2))
                        invest_amount = available / max(max_pos, 1)
                        if invest_amount > 100 and effective_price > 0:
                            shares = invest_amount / effective_price
                            cost = shares * effective_price
                            capitals[dna_idx] -= cost
                            positions[dna_idx][code] = positions[dna_idx].get(code, 0) + shares

                    elif action == "sell":
                        shares = positions[dna_idx].get(code, 0)
                        if shares > 0:
                            # Use next-day close as exit
                            exit_price = closes[min(day + 1, len(closes) - 1)]
                            # Apply sell-side impact
                            if self.n_dnas > 1:
                                sell_frac_total = sell_count / self.n_dnas
                                if sell_frac_total > self.impact_threshold:
                                    exit_price *= (1 - self.impact_pct)

                            proceeds = shares * exit_price
                            entry_value = shares * effective_price
                            capitals[dna_idx] += proceeds
                            trade_counts[dna_idx] += 1
                            if proceeds > entry_value:
                                win_counts[dna_idx] += 1
                            positions[dna_idx][code] = 0

            # Phase 3: Record portfolio values
            for dna_idx in range(self.n_dnas):
                portfolio_value = capitals[dna_idx]
                for code, shares in positions[dna_idx].items():
                    if shares > 0 and code in stock_arrays:
                        closes, _ = stock_arrays[code]
                        price_idx = min(day, len(closes) - 1)
                        portfolio_value += shares * closes[price_idx]
                value_history[dna_idx].append(portfolio_value)

        # Phase 4: Close all remaining positions at last available price
        for dna_idx in range(self.n_dnas):
            for code, shares in positions[dna_idx].items():
                if shares > 0 and code in stock_arrays:
                    closes, _ = stock_arrays[code]
                    final_price = closes[-1]
                    capitals[dna_idx] += shares * final_price
                    positions[dna_idx][code] = 0

        # Phase 5: Compute metrics
        results: List[ArenaResult] = []
        for dna_idx in range(self.n_dnas):
            final_value = capitals[dna_idx]
            # Add any remaining positions value
            for code, shares in positions[dna_idx].items():
                if shares > 0 and code in stock_arrays:
                    closes, _ = stock_arrays[code]
                    final_value += shares * closes[-1]

            values = value_history[dna_idx]
            if not values:
                values = [self.initial_capital]

            # Sharpe ratio
            if len(values) > 1:
                returns = np.diff(values) / np.array(values[:-1], dtype=np.float64)
                returns = returns[np.isfinite(returns)]
                if len(returns) > 1 and np.std(returns) > 1e-10:
                    sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252 / max(step_size, 1)))
                else:
                    sharpe = 0.0
            else:
                sharpe = 0.0

            # Max drawdown
            peak = values[0]
            max_dd = 0.0
            for v in values:
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (peak - v) / peak
                    max_dd = max(max_dd, dd)

            # Win rate
            total_trades = int(trade_counts[dna_idx])
            wins = int(win_counts[dna_idx])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

            results.append(ArenaResult(
                dna_index=dna_idx,
                final_value=round(final_value, 2),
                sharpe=round(sharpe, 4),
                max_drawdown=round(max_dd * 100, 4),  # as percentage
                rank=0,  # will be set below
                total_trades=total_trades,
                win_rate=round(win_rate, 2),
            ))

        # Phase 6: Assign ranks (1 = best final value)
        results.sort(key=lambda r: r.final_value, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    def _empty_results(self) -> List[ArenaResult]:
        """Return neutral results when no data is available."""
        return [
            ArenaResult(
                dna_index=i,
                final_value=self.initial_capital,
                sharpe=0.0,
                max_drawdown=0.0,
                rank=i + 1,
            )
            for i in range(self.n_dnas)
        ]


# ════════════════════════════════════════════════════════════════════
# Convenience function
# ════════════════════════════════════════════════════════════════════

def arena_evaluate(
    dna_list: List[Dict[str, Any]],
    stock_data: Dict[str, Dict[str, Any]],
    initial_capital: float = 1_000_000.0,
    impact_threshold: float = 0.5,
    impact_pct: float = 0.005,
    step_size: int = 5,
) -> List[ArenaResult]:
    """Evaluate multiple DNAs in arena competition mode.

    Parameters
    ----------
    dna_list : list of dict
        DNA parameter dictionaries.
    stock_data : dict
        Stock code -> {'close': [...], 'volume': [...]}.
    initial_capital : float
        Starting capital per DNA.
    impact_threshold : float
        Fraction triggering price impact.
    impact_pct : float
        Price impact percentage.
    step_size : int
        Trading interval in days.

    Returns
    -------
    List of ArenaResult sorted by rank (best first).
    """
    arena = TradingArena(
        dna_list=dna_list,
        initial_capital=initial_capital,
        impact_threshold=impact_threshold,
        impact_pct=impact_pct,
    )
    return arena.run(stock_data, step_size=step_size)
