"""Stock Screener - filter stocks by technical and fundamental criteria."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from src.ta import rsi as calc_rsi, macd as calc_macd, sma


@dataclass
class StockData:
    """Minimal stock data for screening."""
    ticker: str
    close: np.ndarray
    high: np.ndarray | None = None
    low: np.ndarray | None = None
    volume: np.ndarray | None = None
    pe_ratio: float | None = None
    market_cap: float | None = None
    sector: str | None = None


@dataclass
class ScreenResult:
    """One screener match."""
    ticker: str
    price: float
    change_pct: float
    volume: int
    rsi: float | None = None
    market_cap: float | None = None


class StockScreener:
    """Filter a universe of stocks by technical and fundamental criteria."""

    def __init__(self) -> None:
        self._evaluators: dict[str, Callable] = {
            "rsi_14": self._eval_rsi,
            "macd_signal": self._eval_macd_signal,
            "volume_ratio": self._eval_volume_ratio,
            "pe_ratio": self._eval_pe,
            "market_cap": self._eval_market_cap,
            "sma_cross": self._eval_sma_cross,
            "sector": self._eval_sector,
            "price": self._eval_price,
            "change_pct": self._eval_change_pct,
            "volume": self._eval_volume,
        }

    def screen(
        self,
        universe: list[StockData],
        filters: dict[str, Any],
        sort_by: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Screen *universe* with *filters*, return sorted results."""
        results: list[dict[str, Any]] = []
        for stock in universe:
            values: dict[str, Any] = {"ticker": stock.ticker}
            passed = True
            for key, condition in filters.items():
                evaluator = self._evaluators.get(key)
                if evaluator is None:
                    continue
                val = evaluator(stock)
                if val is None:
                    passed = False
                    break
                values[key] = val
                if not self._check(val, condition):
                    passed = False
                    break
            if passed:
                results.append(values)
        if sort_by and results:
            reverse = sort_by.startswith("-")
            key = sort_by.lstrip("-")
            results.sort(key=lambda r: r.get(key, float("inf")), reverse=reverse)
        return results[:limit]

    def screen_gainers(self, universe: list[StockData], limit: int = 20) -> list[dict[str, Any]]:
        """Return top gainers by daily change %."""
        results = []
        for stock in universe:
            pct = self._eval_change_pct(stock)
            if pct is not None and pct > 0:
                results.append({
                    "ticker": stock.ticker,
                    "change_pct": pct,
                    "price": float(stock.close[-1]),
                    "volume": int(stock.volume[-1]) if stock.volume is not None and len(stock.volume) > 0 else 0,
                })
        results.sort(key=lambda r: r["change_pct"], reverse=True)
        return results[:limit]

    def screen_losers(self, universe: list[StockData], limit: int = 20) -> list[dict[str, Any]]:
        """Return top losers by daily change %."""
        results = []
        for stock in universe:
            pct = self._eval_change_pct(stock)
            if pct is not None and pct < 0:
                results.append({
                    "ticker": stock.ticker,
                    "change_pct": pct,
                    "price": float(stock.close[-1]),
                    "volume": int(stock.volume[-1]) if stock.volume is not None and len(stock.volume) > 0 else 0,
                })
        results.sort(key=lambda r: r["change_pct"])
        return results[:limit]

    # -- Condition checker -----------------------------------------------
    @staticmethod
    def _check(value: Any, condition: Any) -> bool:
        if isinstance(condition, dict):
            for op, thr in condition.items():
                if op == "gt" and not (value > thr):
                    return False
                if op == "lt" and not (value < thr):
                    return False
                if op == "gte" and not (value >= thr):
                    return False
                if op == "lte" and not (value <= thr):
                    return False
            return True
        if isinstance(condition, str):
            return value == condition
        return value == condition

    # -- Evaluators ------------------------------------------------------
    @staticmethod
    def _eval_rsi(stock: StockData) -> float | None:
        if len(stock.close) < 15:
            return None
        return float(calc_rsi(stock.close, 14)[-1])

    @staticmethod
    def _eval_macd_signal(stock: StockData) -> str | None:
        if len(stock.close) < 35:
            return None
        _, _, hist = calc_macd(stock.close)
        if len(hist) < 2:
            return None
        if hist[-2] < 0 and hist[-1] >= 0:
            return "bullish"
        if hist[-2] > 0 and hist[-1] <= 0:
            return "bearish"
        return "neutral"

    @staticmethod
    def _eval_volume_ratio(stock: StockData) -> float | None:
        if stock.volume is None or len(stock.volume) < 21:
            return None
        avg = np.mean(stock.volume[-21:-1])
        return float(stock.volume[-1] / avg) if avg > 0 else None

    @staticmethod
    def _eval_pe(stock: StockData) -> float | None:
        return stock.pe_ratio

    @staticmethod
    def _eval_market_cap(stock: StockData) -> float | None:
        return stock.market_cap

    @staticmethod
    def _eval_sma_cross(stock: StockData) -> str | None:
        if len(stock.close) < 50:
            return None
        s20 = sma(stock.close, 20)
        s50 = sma(stock.close, 50)
        if np.isnan(s20[-1]) or np.isnan(s50[-1]):
            return None
        return "bullish" if s20[-1] > s50[-1] else "bearish"

    @staticmethod
    def _eval_sector(stock: StockData) -> str | None:
        return stock.sector

    @staticmethod
    def _eval_price(stock: StockData) -> float | None:
        if len(stock.close) == 0:
            return None
        return float(stock.close[-1])

    @staticmethod
    def _eval_change_pct(stock: StockData) -> float | None:
        if len(stock.close) < 2:
            return None
        prev = stock.close[-2]
        if prev == 0:
            return None
        return float((stock.close[-1] / prev - 1) * 100)

    @staticmethod
    def _eval_volume(stock: StockData) -> float | None:
        if stock.volume is None or len(stock.volume) == 0:
            return None
        return float(stock.volume[-1])
