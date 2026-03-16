"""US Market Calendar — trading days, holidays, next-trading-day logic."""

from __future__ import annotations

import datetime
from typing import List, Tuple


# US market holidays (fixed + observed rules)
_FIXED_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (7, 4): "Independence Day",
    (12, 25): "Christmas Day",
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> datetime.date:
    """Return the *n*-th occurrence of *weekday* (0=Mon) in *month*."""
    first = datetime.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + datetime.timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> datetime.date:
    last = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1) if month < 12 else datetime.date(year, 12, 31)
    offset = (last.weekday() - weekday) % 7
    return last - datetime.timedelta(days=offset)


def _us_holidays(year: int) -> List[Tuple[datetime.date, str]]:
    holidays = []
    # Fixed
    for (m, d), name in _FIXED_HOLIDAYS.items():
        dt = datetime.date(year, m, d)
        # Observed rule: Sat→Fri, Sun→Mon
        if dt.weekday() == 5:
            dt = dt - datetime.timedelta(days=1)
        elif dt.weekday() == 6:
            dt = dt + datetime.timedelta(days=1)
        holidays.append((dt, name))
    # MLK: 3rd Mon Jan
    holidays.append((_nth_weekday(year, 1, 0, 3), "MLK Day"))
    # Presidents: 3rd Mon Feb
    holidays.append((_nth_weekday(year, 2, 0, 3), "Presidents' Day"))
    # Good Friday: approximate (Easter - 2)
    holidays.append((_easter(year) - datetime.timedelta(days=2), "Good Friday"))
    # Memorial: last Mon May
    holidays.append((_last_weekday(year, 5, 0), "Memorial Day"))
    # Juneteenth
    jt = datetime.date(year, 6, 19)
    if jt.weekday() == 5:
        jt -= datetime.timedelta(days=1)
    elif jt.weekday() == 6:
        jt += datetime.timedelta(days=1)
    holidays.append((jt, "Juneteenth"))
    # Labor: 1st Mon Sep
    holidays.append((_nth_weekday(year, 9, 0, 1), "Labor Day"))
    # Thanksgiving: 4th Thu Nov
    holidays.append((_nth_weekday(year, 11, 3, 4), "Thanksgiving"))
    return holidays


def _easter(year: int) -> datetime.date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(year, month, day)


class MarketCalendar:
    """US stock-market calendar."""

    def __init__(self):
        self._cache: dict[int, set[datetime.date]] = {}

    def _holiday_set(self, year: int) -> set[datetime.date]:
        if year not in self._cache:
            self._cache[year] = {d for d, _ in _us_holidays(year)}
        return self._cache[year]

    def _holiday_list(self, year: int) -> List[Tuple[datetime.date, str]]:
        return sorted(_us_holidays(year), key=lambda x: x[0])

    def is_trading_day(self, date: datetime.date) -> bool:
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        if date.weekday() >= 5:
            return False
        return date not in self._holiday_set(date.year)

    def next_trading_day(self, date: datetime.date) -> datetime.date:
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        d = date + datetime.timedelta(days=1)
        while not self.is_trading_day(d):
            d += datetime.timedelta(days=1)
        return d

    def trading_days_between(self, start: datetime.date, end: datetime.date) -> List[datetime.date]:
        if isinstance(start, str):
            start = datetime.date.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.date.fromisoformat(end)
        days = []
        d = start
        while d <= end:
            if self.is_trading_day(d):
                days.append(d)
            d += datetime.timedelta(days=1)
        return days

    def upcoming_holidays(self, days: int = 30, from_date: datetime.date = None) -> List[Tuple[datetime.date, str]]:
        if from_date is None:
            from_date = datetime.date.today()
        elif isinstance(from_date, str):
            from_date = datetime.date.fromisoformat(from_date)
        end = from_date + datetime.timedelta(days=days)
        result = []
        for year in range(from_date.year, end.year + 1):
            for dt, name in self._holiday_list(year):
                if from_date <= dt <= end:
                    result.append((dt, name))
        return sorted(result, key=lambda x: x[0])
