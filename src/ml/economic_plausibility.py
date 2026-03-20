"""
Economic Plausibility Checker
=============================

Detect suspiciously good backtest results that likely stem from overfitting,
look-ahead bias, or other methodological errors.

Inspired by the no-arbitrage constraints in the ARTEMIS framework
(arXiv:2603.18107).  Real-world trading faces friction, information delay,
and fat tails; any backtest that looks "too clean" probably is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass
class PlausibilityResult:
    """One check's verdict."""

    ok: bool
    message: str
    check_name: str = ""


class EconomicPlausibilityChecker:
    """Detect suspiciously good backtest results.

    Inspired by ARTEMIS's no-arbitrage constraints (arXiv:2603.18107).
    Each ``check_*`` method returns ``(ok: bool, message: str)`` where
    ``ok=False`` means the result looks implausible.
    """

    # ── Sharpe ───────────────────────────────────────────────────

    def check_sharpe(
        self,
        sharpe: float,
        period_days: int = 252,
    ) -> tuple[bool, str]:
        """Flag if Sharpe ratio looks unrealistically high.

        Rules
        -----
        * Raw Sharpe > 3.0  → suspicious (likely overfitting)
        * Annualised Sharpe > 4.0 → almost certainly wrong
        * Annualised Sharpe > 2.5 on long periods (>500d) → very rare
        """
        if period_days <= 0:
            return True, "Period too short to assess Sharpe."

        # Annualise if sub-annual
        ann_sharpe = sharpe * math.sqrt(252 / max(period_days, 1)) if period_days < 252 else sharpe

        if ann_sharpe > 4.0:
            return False, (
                f"Annualised Sharpe {ann_sharpe:.2f} is extremely high (>4.0). "
                "This almost certainly indicates overfitting or a simulation error."
            )
        if sharpe > 3.0:
            return False, (
                f"Sharpe {sharpe:.2f} > 3.0 is suspiciously high. "
                "Top hedge funds rarely sustain Sharpe > 2.5."
            )
        if period_days > 500 and ann_sharpe > 2.5:
            return False, (
                f"Annualised Sharpe {ann_sharpe:.2f} over {period_days} days is implausible. "
                "Very few strategies sustain Sharpe > 2.5 for multiple years."
            )
        return True, f"Sharpe {sharpe:.2f} is within plausible range."

    # ── Win rate ─────────────────────────────────────────────────

    def check_win_rate(
        self,
        win_rate: float,
        trades: int,
    ) -> tuple[bool, str]:
        """Flag implausibly high win rates.

        Rules
        -----
        * win_rate > 0.75 with > 50 trades  → suspicious
        * win_rate > 0.90 with > 20 trades  → almost certainly wrong
        * win_rate > 0.95 with > 10 trades  → unrealistic
        * ≤ 5 trades → too few to judge
        """
        if trades <= 5:
            return True, f"Only {trades} trades — too few to assess win rate."

        if win_rate > 0.95 and trades > 10:
            return False, (
                f"Win rate {win_rate:.1%} over {trades} trades is unrealistic. "
                "Even the best systematic strategies rarely exceed 65%."
            )
        if win_rate > 0.90 and trades > 20:
            return False, (
                f"Win rate {win_rate:.1%} over {trades} trades is highly suspicious. "
                "Check for look-ahead bias."
            )
        if win_rate > 0.75 and trades > 50:
            return False, (
                f"Win rate {win_rate:.1%} over {trades} trades is likely overfitting. "
                "Real strategies with this many trades rarely exceed 60-65%."
            )
        return True, f"Win rate {win_rate:.1%} over {trades} trades looks plausible."

    # ── Return consistency ───────────────────────────────────────

    def check_consistency(
        self,
        returns: Sequence[float],
    ) -> tuple[bool, str]:
        """Flag suspiciously smooth equity curves.

        Real P&L is lumpy.  If the day-over-day returns have an
        implausibly low coefficient of variation or near-zero skewness,
        something is wrong.

        Rules
        -----
        * Coefficient of variation of returns < 0.3 with > 50 returns → suspicious
        * Autocorrelation(1) > 0.5 → serial dependence (look-ahead?)
        * Fraction of positive days > 0.80 with > 30 days → suspicious
        """
        returns = list(returns)
        n = len(returns)
        if n < 10:
            return True, "Too few return observations to assess consistency."

        mean_r = sum(returns) / n
        if n < 2:
            return True, "Need at least 2 returns."

        var_r = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
        std_r = math.sqrt(var_r) if var_r > 0 else 0.0

        # Coefficient of variation
        if std_r > 0 and abs(mean_r) > 0 and n > 50:
            cv = std_r / abs(mean_r)
            if cv < 0.3:
                return False, (
                    f"Returns are suspiciously smooth (CV={cv:.2f} < 0.3). "
                    "Real markets are much bumpier."
                )

        # Lag-1 autocorrelation
        if n > 20:
            mean_centered = [r - mean_r for r in returns]
            autocov = sum(mean_centered[i] * mean_centered[i + 1] for i in range(n - 1)) / (n - 1)
            autocorr = autocov / var_r if var_r > 0 else 0.0
            if autocorr > 0.5:
                return False, (
                    f"Lag-1 autocorrelation = {autocorr:.2f} is very high. "
                    "This suggests serial dependence — possible look-ahead bias."
                )

        # Fraction of winning days
        positive_frac = sum(1 for r in returns if r > 0) / n
        if positive_frac > 0.80 and n > 30:
            return False, (
                f"{positive_frac:.0%} of days are positive over {n} observations. "
                "Real strategies rarely win more than 55-60% of days."
            )

        return True, "Return distribution looks plausible."

    # ── Max drawdown ─────────────────────────────────────────────

    def check_max_drawdown(
        self,
        max_drawdown: float,
        total_return: float,
        period_days: int = 252,
    ) -> tuple[bool, str]:
        """Flag if the return-to-drawdown ratio is implausibly good.

        The Calmar ratio (annualised return / max drawdown) above 5 is
        extremely rare in live trading.
        """
        if max_drawdown == 0:
            if total_return > 0.05:
                return False, (
                    f"Zero drawdown with {total_return:.1%} return is impossible in practice."
                )
            return True, "No drawdown detected (small move)."

        dd_abs = abs(max_drawdown)
        years = max(period_days / 252, 0.25)
        ann_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0
        calmar = abs(ann_return / dd_abs) if dd_abs > 0 else 0

        if calmar > 5.0 and period_days > 60:
            return False, (
                f"Calmar ratio {calmar:.1f} (ann. return {ann_return:.1%} / "
                f"max DD {max_drawdown:.1%}) is implausibly high. "
                "Even top-tier strategies rarely sustain Calmar > 3."
            )
        return True, f"Calmar ratio {calmar:.1f} looks plausible."

    # ── Convenience ──────────────────────────────────────────────

    def run_all(
        self,
        *,
        sharpe: float = 0.0,
        win_rate: float = 0.0,
        trades: int = 0,
        returns: Sequence[float] | None = None,
        max_drawdown: float = 0.0,
        total_return: float = 0.0,
        period_days: int = 252,
    ) -> list[PlausibilityResult]:
        """Run all plausibility checks and return a list of results.

        This is a convenience wrapper: callers can also invoke individual
        ``check_*`` methods directly.
        """
        results: list[PlausibilityResult] = []

        ok, msg = self.check_sharpe(sharpe, period_days)
        results.append(PlausibilityResult(ok=ok, message=msg, check_name="sharpe"))

        ok, msg = self.check_win_rate(win_rate, trades)
        results.append(PlausibilityResult(ok=ok, message=msg, check_name="win_rate"))

        if returns is not None:
            ok, msg = self.check_consistency(returns)
            results.append(PlausibilityResult(ok=ok, message=msg, check_name="consistency"))

        ok, msg = self.check_max_drawdown(max_drawdown, total_return, period_days)
        results.append(PlausibilityResult(ok=ok, message=msg, check_name="max_drawdown"))

        return results
