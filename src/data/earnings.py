"""
Earnings Calendar Integration
==============================
Fetch upcoming and historical earnings data using yfinance.
No API keys required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


@dataclass
class EarningsEvent:
    """A single earnings event."""
    ticker: str
    date: str
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    surprise_pct: Optional[float] = None


class EarningsCalendar:
    """
    Earnings calendar integration using yfinance.

    Usage:
        cal = EarningsCalendar()
        upcoming = cal.upcoming(days=7)
        history = cal.historical("AAPL", quarters=4)
        surprises = cal.surprise_history("AAPL")
    """

    # Popular tickers to check for upcoming earnings
    DEFAULT_WATCHLIST = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
        "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD",
        "DIS", "NFLX", "PYPL", "INTC", "AMD", "CRM", "ADBE",
        "PEP", "KO", "MRK", "ABBV", "PFE", "TMO", "COST", "AVGO",
    ]

    def __init__(self, watchlist: Optional[list[str]] = None):
        self.watchlist = watchlist or self.DEFAULT_WATCHLIST

    def upcoming(self, days: int = 7, tickers: Optional[list[str]] = None) -> list[dict]:
        """
        Get upcoming earnings within the next N days.
        Returns list of dicts with ticker, date, eps_estimate.
        """
        if yf is None:
            return []

        check_tickers = tickers or self.watchlist
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        results: list[dict] = []

        for ticker in check_tickers:
            try:
                stock = yf.Ticker(ticker)
                cal = stock.calendar
                if cal is None or (hasattr(cal, 'empty') and cal.empty):
                    continue

                # yfinance calendar can be a dict or DataFrame
                if isinstance(cal, dict):
                    earn_date = cal.get("Earnings Date")
                    if earn_date:
                        if isinstance(earn_date, list):
                            earn_date = earn_date[0]
                        if hasattr(earn_date, 'to_pydatetime'):
                            earn_date = earn_date.to_pydatetime()
                        elif isinstance(earn_date, str):
                            try:
                                earn_date = datetime.fromisoformat(earn_date)
                            except ValueError:
                                continue
                        if isinstance(earn_date, datetime) and now <= earn_date <= cutoff:
                            results.append({
                                "ticker": ticker,
                                "date": earn_date.strftime("%Y-%m-%d"),
                                "eps_estimate": cal.get("EPS Estimate"),
                                "revenue_estimate": cal.get("Revenue Estimate"),
                            })
                else:
                    # DataFrame format
                    if "Earnings Date" in cal.index:
                        dates = cal.loc["Earnings Date"]
                        if hasattr(dates, 'iloc'):
                            earn_date = dates.iloc[0]
                        else:
                            earn_date = dates
                        if hasattr(earn_date, 'to_pydatetime'):
                            earn_date = earn_date.to_pydatetime()
                        if isinstance(earn_date, datetime) and now <= earn_date <= cutoff:
                            results.append({
                                "ticker": ticker,
                                "date": earn_date.strftime("%Y-%m-%d"),
                                "eps_estimate": None,
                                "revenue_estimate": None,
                            })
            except Exception:
                continue

        results.sort(key=lambda x: x["date"])
        return results

    def historical(self, ticker: str, quarters: int = 4) -> list[dict]:
        """
        Get historical earnings data for a ticker.
        Returns list of dicts with date, eps_actual, eps_estimate, surprise_pct.
        """
        if yf is None:
            return []

        try:
            stock = yf.Ticker(ticker)
            earnings = stock.earnings_history
            if earnings is None or (hasattr(earnings, 'empty') and earnings.empty):
                # Fallback to quarterly earnings
                qe = stock.quarterly_earnings
                if qe is not None and not qe.empty:
                    results = []
                    for idx, row in qe.iterrows():
                        results.append({
                            "ticker": ticker,
                            "date": str(idx),
                            "eps_actual": float(row.get("Earnings", 0)) if "Earnings" in row else None,
                            "revenue_actual": float(row.get("Revenue", 0)) if "Revenue" in row else None,
                            "eps_estimate": None,
                            "surprise_pct": None,
                        })
                    return results[-quarters:]
                return []

            results = []
            if hasattr(earnings, 'iterrows'):
                for idx, row in earnings.iterrows():
                    actual = row.get("epsActual", row.get("Reported EPS"))
                    estimate = row.get("epsEstimate", row.get("EPS Estimate"))
                    surprise = None
                    if actual is not None and estimate is not None and estimate != 0:
                        try:
                            surprise = round((float(actual) - float(estimate)) / abs(float(estimate)) * 100, 2)
                        except (ValueError, ZeroDivisionError):
                            pass
                    results.append({
                        "ticker": ticker,
                        "date": str(idx) if not hasattr(idx, 'strftime') else idx.strftime("%Y-%m-%d"),
                        "eps_actual": float(actual) if actual is not None else None,
                        "eps_estimate": float(estimate) if estimate is not None else None,
                        "surprise_pct": surprise,
                    })
            return results[-quarters:]
        except Exception:
            return []

    def surprise_history(self, ticker: str) -> list[dict]:
        """
        Get earnings surprise history (beat/miss).
        Returns list of dicts with date, surprise_pct, beat (bool).
        """
        history = self.historical(ticker, quarters=8)
        results = []
        for h in history:
            surprise = h.get("surprise_pct")
            if surprise is not None:
                results.append({
                    "ticker": ticker,
                    "date": h["date"],
                    "surprise_pct": surprise,
                    "beat": surprise > 0,
                    "eps_actual": h.get("eps_actual"),
                    "eps_estimate": h.get("eps_estimate"),
                })
        return results
