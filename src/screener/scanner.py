"""Market Scanner — real-time rule-based scanning with alerts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ScanRule:
    """A named scanning rule."""
    name: str
    condition: Callable[[dict], bool]
    action: str = "alert"  # alert, log, notify


@dataclass
class ScanResult:
    """Result of a single scan match."""
    rule_name: str
    symbol: str
    action: str
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class MarketScanner:
    """Scan symbols against configurable rules."""

    def __init__(self, exchange_registry=None):
        self._registry = exchange_registry
        self.rules: list[ScanRule] = []
        self._results_history: list[ScanResult] = []

    def add_rule(self, name: str, condition: Callable[[dict], bool], action: str = "alert") -> None:
        """Register a scanning rule."""
        self.rules.append(ScanRule(name=name, condition=condition, action=action))

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.name != name]
        return len(self.rules) < before

    def clear_rules(self) -> None:
        self.rules.clear()

    def scan_once(self, symbols: list[str]) -> list[ScanResult]:
        """Run all rules against all symbols once. Returns matches."""
        results = []
        for sym in symbols:
            data = self._fetch_data(sym)
            if data is None:
                continue
            data["symbol"] = sym
            for rule in self.rules:
                try:
                    if rule.condition(data):
                        result = ScanResult(
                            rule_name=rule.name,
                            symbol=sym,
                            action=rule.action,
                            data=dict(data),
                        )
                        results.append(result)
                except Exception as e:
                    logger.warning("Scanner rule '%s' failed for %s: %s", rule.name, sym, e)
        self._results_history.extend(results)
        return results

    def run_continuous(self, symbols: list[str], interval: int = 60, max_iterations: int | None = None,
                       callback: Callable[[list[ScanResult]], None] | None = None) -> list[ScanResult]:
        """Run scanning loop. If *max_iterations* is set, stop after that many rounds."""
        all_results: list[ScanResult] = []
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            results = self.scan_once(symbols)
            all_results.extend(results)
            if callback and results:
                callback(results)
            iteration += 1
            if max_iterations is not None and iteration >= max_iterations:
                break
            time.sleep(interval)
        return all_results

    @property
    def history(self) -> list[ScanResult]:
        return list(self._results_history)

    # ------------------------------------------------------------------
    # Rule builders (convenience)
    # ------------------------------------------------------------------

    @staticmethod
    def rsi_below(threshold: float) -> Callable[[dict], bool]:
        """Create a condition: RSI < threshold."""
        def condition(data: dict) -> bool:
            return data.get("rsi_14", 100) < threshold
        return condition

    @staticmethod
    def rsi_above(threshold: float) -> Callable[[dict], bool]:
        def condition(data: dict) -> bool:
            return data.get("rsi_14", 0) > threshold
        return condition

    @staticmethod
    def volume_above(threshold: float) -> Callable[[dict], bool]:
        """Create a condition: volume_ratio > threshold."""
        def condition(data: dict) -> bool:
            return data.get("volume_ratio", 0) > threshold
        return condition

    @staticmethod
    def price_change_above(threshold: float) -> Callable[[dict], bool]:
        def condition(data: dict) -> bool:
            return data.get("price_change_1d", 0) > threshold
        return condition

    @staticmethod
    def price_change_below(threshold: float) -> Callable[[dict], bool]:
        def condition(data: dict) -> bool:
            return data.get("price_change_1d", 0) < threshold
        return condition

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_data(self, symbol: str) -> dict | None:
        """Fetch enriched data for a symbol."""
        if self._registry is None:
            return None
        try:
            import numpy as np
            from src.ta import rsi as calc_rsi

            adapter = self._registry.get("yahoo")
            candles = adapter.get_ohlcv(symbol, timeframe="1d", limit=30)
            if not candles or len(candles) < 15:
                return None
            closes = np.array([c["close"] for c in candles], dtype=np.float64)
            volumes = np.array([c["volume"] for c in candles], dtype=np.float64)

            rsi_val = float(calc_rsi(closes, 14)[-1])
            avg_vol = float(np.mean(volumes[-21:-1])) if len(volumes) >= 21 else float(np.mean(volumes[:-1]))
            vol_ratio = float(volumes[-1] / avg_vol) if avg_vol > 0 else 0.0
            change_1d = (closes[-1] - closes[-2]) / closes[-2] if len(closes) >= 2 else 0.0

            return {
                "rsi_14": rsi_val,
                "volume_ratio": vol_ratio,
                "price_change_1d": float(change_1d),
                "price": float(closes[-1]),
                "volume": float(volumes[-1]),
            }
        except Exception:
            return None
