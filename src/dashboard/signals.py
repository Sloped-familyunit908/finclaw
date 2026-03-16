"""
Signal Dashboard
Generate signal reports combining strategy output with risk metrics.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SignalReport:
    """Comprehensive signal report for a single ticker."""
    ticker: str
    current_signal: float        # -1 to 1
    signal_history: list[float]  # recent signal values
    confidence: float            # 0 to 1
    regime: str                  # bull, bear, neutral
    suggested_position: str      # long, short, flat
    risk_metrics: dict[str, float]
    strategy_name: str = ""
    timestamp: str = ""


def generate_signal_report(
    strategy: Any,
    data: list[float],
    ticker: str,
    history_window: int = 20,
) -> SignalReport:
    """
    Generate a signal report from a strategy and price data.
    
    Strategy must have one of:
    - .signal(prices) -> float
    - .generate_signal(prices) -> object with .signal and .confidence
    - .detailed_signal(prices) -> CombinedSignal
    """
    if len(data) < 5:
        return SignalReport(
            ticker=ticker, current_signal=0.0, signal_history=[],
            confidence=0.0, regime="neutral", suggested_position="flat",
            risk_metrics={},
        )

    # Generate signal history
    signal_history = []
    start = max(0, len(data) - history_window)
    for i in range(start, len(data)):
        slice_data = data[:i + 1]
        sig_val = _extract_signal(strategy, slice_data)
        signal_history.append(sig_val)

    current_signal = signal_history[-1] if signal_history else 0.0
    confidence = _estimate_confidence(signal_history)
    regime = _detect_regime(data)
    position = _suggest_position(current_signal, confidence, regime)
    risk = _compute_risk_metrics(data)

    return SignalReport(
        ticker=ticker,
        current_signal=round(current_signal, 4),
        signal_history=[round(s, 4) for s in signal_history],
        confidence=round(confidence, 4),
        regime=regime,
        suggested_position=position,
        risk_metrics=risk,
        strategy_name=type(strategy).__name__,
    )


def _extract_signal(strategy: Any, prices: list[float]) -> float:
    """Extract a float signal from various strategy types."""
    if hasattr(strategy, "detailed_signal"):
        return strategy.detailed_signal(prices).value
    if hasattr(strategy, "signal"):
        val = strategy.signal(prices)
        if isinstance(val, (int, float)):
            return max(-1.0, min(1.0, float(val)))
    if hasattr(strategy, "generate_signal"):
        result = strategy.generate_signal(prices)
        sig_str = getattr(result, "signal", "hold")
        conf = getattr(result, "confidence", 0.5)
        if sig_str == "buy":
            return conf
        elif sig_str == "sell":
            return -conf
    return 0.0


def _estimate_confidence(signal_history: list[float]) -> float:
    """Confidence based on signal consistency."""
    if len(signal_history) < 2:
        return abs(signal_history[0]) if signal_history else 0.0

    # Consistency: are recent signals pointing the same way?
    recent = signal_history[-5:] if len(signal_history) >= 5 else signal_history
    signs = [1 if s > 0.05 else (-1 if s < -0.05 else 0) for s in recent]
    if not signs:
        return 0.0
    
    dominant = max(set(signs), key=signs.count)
    agreement = signs.count(dominant) / len(signs)
    avg_strength = sum(abs(s) for s in recent) / len(recent)
    
    return min(1.0, agreement * avg_strength * 1.5)


def _detect_regime(data: list[float], window: int = 50) -> str:
    """Simple regime detection based on trend and volatility."""
    if len(data) < 10:
        return "neutral"
    
    w = min(window, len(data))
    recent = data[-w:]
    
    # Trend: compare first half vs second half
    mid = len(recent) // 2
    first_avg = sum(recent[:mid]) / mid
    second_avg = sum(recent[mid:]) / (len(recent) - mid)
    
    pct_change = (second_avg / first_avg - 1) if first_avg > 0 else 0
    
    if pct_change > 0.05:
        return "bull"
    elif pct_change < -0.05:
        return "bear"
    return "neutral"


def _suggest_position(signal: float, confidence: float, regime: str) -> str:
    """Suggest position considering signal, confidence, and regime."""
    if confidence < 0.2:
        return "flat"
    if signal > 0.2:
        return "long"
    elif signal < -0.2:
        return "short"
    return "flat"


def _compute_risk_metrics(data: list[float]) -> dict[str, float]:
    """Compute basic risk metrics from price data."""
    if len(data) < 2:
        return {}
    
    returns = [(data[i] / data[i-1]) - 1 for i in range(1, len(data))]
    
    mean_r = sum(returns) / len(returns)
    var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std_r = math.sqrt(var_r) if var_r > 0 else 0.0
    
    # Annualized volatility
    annual_vol = std_r * math.sqrt(252)
    
    # Max drawdown
    peak = data[0]
    max_dd = 0.0
    for p in data:
        if p > peak:
            peak = p
        dd = (peak - p) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    # Sortino-style downside deviation
    down_returns = [r for r in returns if r < 0]
    downside_dev = 0.0
    if down_returns:
        downside_dev = math.sqrt(sum(r ** 2 for r in down_returns) / len(down_returns))
    
    return {
        "daily_volatility": round(std_r, 6),
        "annual_volatility": round(annual_vol, 4),
        "max_drawdown": round(max_dd, 4),
        "downside_deviation": round(downside_dev, 6),
        "daily_return_mean": round(mean_r, 6),
        "positive_days_pct": round(sum(1 for r in returns if r > 0) / len(returns), 4),
    }
