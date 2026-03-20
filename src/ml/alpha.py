"""
Alpha model — combine multiple signals into a unified alpha score.

Community Edition: Standard alpha model implementation.
See finclaw-pro for production parameters and optimized signal weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np


@dataclass
class Signal:
    """A named signal generator.

    Parameters
    ----------
    name : str
        Human-readable name.
    func : callable
        Function(ticker: str) -> float or np.nan.
    weight : float
        Default weight in alpha combination.
    """

    name: str
    func: Callable[[str], float]
    weight: float = 1.0


class AlphaModel:
    """Combine multiple signals into a single alpha score per ticker.

    Parameters
    ----------
    signals : list of Signal
        Signal generators.
    weights : list of float, optional
        Weights for each signal. Overrides Signal.weight if provided.
    normalize : bool
        If True, z-score normalize the final alphas across the universe.
    """

    def __init__(
        self,
        signals: List[Signal],
        weights: Optional[List[float]] = None,
        normalize: bool = True,
    ):
        self.signals = signals
        self.weights = weights or [s.weight for s in signals]
        self.normalize = normalize
        if len(self.weights) != len(self.signals):
            raise ValueError("Number of weights must match number of signals")

    def generate_alphas(self, universe: List[str]) -> Dict[str, float]:
        """Generate alpha scores for a universe of tickers.

        Returns
        -------
        dict
            {ticker: alpha_score}. Higher = more attractive.
        """
        if not universe or not self.signals:
            return {}

        raw_scores: Dict[str, float] = {}
        w_total = sum(abs(w) for w in self.weights)
        if w_total == 0:
            w_total = 1.0

        for ticker in universe:
            score = 0.0
            weight_used = 0.0
            for signal, w in zip(self.signals, self.weights):
                try:
                    val = signal.func(ticker)
                    if val is not None and not np.isnan(val):
                        score += w * val
                        weight_used += abs(w)
                except Exception:
                    continue
            if weight_used > 0:
                raw_scores[ticker] = score / weight_used
            else:
                raw_scores[ticker] = 0.0

        if self.normalize and len(raw_scores) >= 2:
            values = np.array(list(raw_scores.values()))
            mean = np.mean(values)
            std = np.std(values, ddof=1)
            if std > 0:
                raw_scores = {t: (v - mean) / std for t, v in raw_scores.items()}

        return raw_scores

    def rank(self, universe: List[str], ascending: bool = False) -> List[str]:
        """Rank tickers by alpha score.

        Parameters
        ----------
        ascending : bool
            If False (default), highest alpha first.
        """
        alphas = self.generate_alphas(universe)
        return sorted(alphas.keys(), key=lambda t: alphas.get(t, 0), reverse=not ascending)

    def top_n(self, universe: List[str], n: int = 10) -> List[str]:
        """Return top N tickers by alpha score."""
        return self.rank(universe)[:n]
