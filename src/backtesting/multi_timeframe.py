"""
Multi-Timeframe Backtester
Run the same strategy on daily, weekly, and monthly resampled data.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from agents.backtester import BacktestResult


@dataclass
class MultiTimeframeReport:
    daily: BacktestResult | None = None
    weekly: BacktestResult | None = None
    monthly: BacktestResult | None = None

    def summary(self) -> str:
        lines = ["=== Multi-Timeframe Report ==="]
        for label, r in [("Daily", self.daily), ("Weekly", self.weekly), ("Monthly", self.monthly)]:
            if r:
                lines.append(
                    f"  {label:8s}: Return={r.total_return:+.2%}  "
                    f"Sharpe={r.sharpe_ratio:.2f}  MaxDD={r.max_drawdown:.2%}  "
                    f"Trades={r.total_trades}"
                )
            else:
                lines.append(f"  {label:8s}: (insufficient data)")
        return "\n".join(lines)


def _resample_weekly(bars: list[dict]) -> list[dict]:
    """Resample daily bars to weekly (Friday close)."""
    if not bars:
        return []
    weekly = []
    week_bars = []
    for bar in bars:
        dt = bar.get("date", datetime.now())
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        week_bars.append(bar)
        if dt.weekday() == 4 or bar is bars[-1]:  # Friday or last bar
            if week_bars:
                weekly.append({
                    "date": dt,
                    "price": week_bars[-1]["price"],
                    "volume": sum(b.get("volume", 0) for b in week_bars),
                })
                week_bars = []
    return weekly


def _resample_monthly(bars: list[dict]) -> list[dict]:
    """Resample daily bars to monthly (last day of month)."""
    if not bars:
        return []
    monthly = []
    current_month = None
    month_bars = []
    for bar in bars:
        dt = bar.get("date", datetime.now())
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        m = (dt.year, dt.month)
        if current_month and m != current_month and month_bars:
            monthly.append({
                "date": month_bars[-1].get("date", datetime.now()),
                "price": month_bars[-1]["price"],
                "volume": sum(b.get("volume", 0) for b in month_bars),
            })
            month_bars = []
        current_month = m
        month_bars.append(bar)
    if month_bars:
        monthly.append({
            "date": month_bars[-1].get("date", datetime.now()),
            "price": month_bars[-1]["price"],
            "volume": sum(b.get("volume", 0) for b in month_bars),
        })
    return monthly


class MultiTimeframeBacktester:
    """Run backtests on daily, weekly, and monthly data."""

    async def run(
        self,
        asset: str,
        strategy_name: str,
        daily_history: list[dict],
        backtester_factory: Callable,
    ) -> MultiTimeframeReport:
        report = MultiTimeframeReport()

        # Daily
        if len(daily_history) >= 30:
            bt = backtester_factory()
            try:
                report.daily = await bt.run(asset, strategy_name, daily_history)
            except Exception:
                pass

        # Weekly
        weekly = _resample_weekly(daily_history)
        if len(weekly) >= 30:
            bt = backtester_factory()
            try:
                report.weekly = await bt.run(asset, f"{strategy_name}_weekly", weekly)
            except Exception:
                pass

        # Monthly
        monthly = _resample_monthly(daily_history)
        if len(monthly) >= 30:
            bt = backtester_factory()
            try:
                report.monthly = await bt.run(asset, f"{strategy_name}_monthly", monthly)
            except Exception:
                pass

        return report
