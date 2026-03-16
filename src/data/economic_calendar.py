"""
FinClaw - Economic Calendar
Track upcoming macro events and their potential market impact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class EconomicEvent:
    """A single economic calendar event."""
    name: str
    date: datetime
    country: str = 'US'
    impact: str = 'medium'   # low, medium, high
    previous: Optional[float] = None
    forecast: Optional[float] = None
    actual: Optional[float] = None
    category: str = 'other'  # employment, inflation, gdp, rates, housing, manufacturing, other

    @property
    def surprise(self) -> Optional[float]:
        """Actual - Forecast if both available."""
        if self.actual is not None and self.forecast is not None:
            return self.actual - self.forecast
        return None

    @property
    def is_high_impact(self) -> bool:
        return self.impact == 'high'


# Built-in recurring US economic events with typical schedules
_RECURRING_EVENTS = [
    {'name': 'Non-Farm Payrolls', 'category': 'employment', 'impact': 'high', 'day_of_month': 'first_friday'},
    {'name': 'CPI (YoY)', 'category': 'inflation', 'impact': 'high', 'day_of_month': 10},
    {'name': 'Core CPI (MoM)', 'category': 'inflation', 'impact': 'high', 'day_of_month': 10},
    {'name': 'FOMC Interest Rate Decision', 'category': 'rates', 'impact': 'high', 'day_of_month': None},
    {'name': 'GDP (QoQ)', 'category': 'gdp', 'impact': 'high', 'day_of_month': 25},
    {'name': 'Initial Jobless Claims', 'category': 'employment', 'impact': 'medium', 'day_of_month': 'weekly_thursday'},
    {'name': 'Retail Sales (MoM)', 'category': 'other', 'impact': 'medium', 'day_of_month': 15},
    {'name': 'ISM Manufacturing PMI', 'category': 'manufacturing', 'impact': 'high', 'day_of_month': 1},
    {'name': 'ISM Services PMI', 'category': 'manufacturing', 'impact': 'medium', 'day_of_month': 3},
    {'name': 'PCE Price Index (MoM)', 'category': 'inflation', 'impact': 'high', 'day_of_month': 28},
    {'name': 'Consumer Confidence', 'category': 'other', 'impact': 'medium', 'day_of_month': 25},
    {'name': 'Existing Home Sales', 'category': 'housing', 'impact': 'medium', 'day_of_month': 20},
    {'name': 'New Home Sales', 'category': 'housing', 'impact': 'medium', 'day_of_month': 23},
    {'name': 'Durable Goods Orders', 'category': 'manufacturing', 'impact': 'medium', 'day_of_month': 26},
    {'name': 'PPI (MoM)', 'category': 'inflation', 'impact': 'medium', 'day_of_month': 11},
]

# Historical average market impact (absolute S&P 500 move on release day, in %)
_HISTORICAL_IMPACT = {
    'Non-Farm Payrolls': {'avg_move': 0.8, 'max_move': 3.5, 'direction_bias': 'neutral'},
    'CPI (YoY)': {'avg_move': 1.0, 'max_move': 4.0, 'direction_bias': 'inverse'},
    'FOMC Interest Rate Decision': {'avg_move': 1.2, 'max_move': 5.0, 'direction_bias': 'inverse'},
    'GDP (QoQ)': {'avg_move': 0.6, 'max_move': 2.5, 'direction_bias': 'positive'},
    'ISM Manufacturing PMI': {'avg_move': 0.5, 'max_move': 2.0, 'direction_bias': 'positive'},
    'PCE Price Index (MoM)': {'avg_move': 0.7, 'max_move': 3.0, 'direction_bias': 'inverse'},
}


class EconomicCalendar:
    """
    Economic calendar for tracking macro events.

    Uses built-in recurring event templates for offline operation.
    Can also accept custom events.
    """

    def __init__(self):
        self._custom_events: list[EconomicEvent] = []

    def add_event(self, event: EconomicEvent) -> None:
        """Add a custom event to the calendar."""
        self._custom_events.append(event)

    def _generate_recurring(self, start: datetime, end: datetime) -> list[EconomicEvent]:
        """Generate recurring events in the date range."""
        events = []
        current = start.replace(hour=8, minute=30, second=0, microsecond=0)

        while current <= end:
            for tmpl in _RECURRING_EVENTS:
                dom = tmpl['day_of_month']
                event_date = None

                if dom == 'first_friday':
                    # First Friday of the month
                    first = current.replace(day=1)
                    offset = (4 - first.weekday()) % 7
                    event_date = first + timedelta(days=offset)
                elif dom == 'weekly_thursday':
                    # Every Thursday
                    if current.weekday() == 3:
                        event_date = current
                elif isinstance(dom, int):
                    try:
                        event_date = current.replace(day=dom)
                    except ValueError:
                        continue

                if event_date and start <= event_date <= end:
                    events.append(EconomicEvent(
                        name=tmpl['name'],
                        date=event_date,
                        country='US',
                        impact=tmpl['impact'],
                        category=tmpl['category'],
                    ))

            current += timedelta(days=1)

        # Deduplicate by (name, date)
        seen = set()
        unique = []
        for e in events:
            key = (e.name, e.date.date())
            if key not in seen:
                seen.add(key)
                unique.append(e)

        return sorted(unique, key=lambda e: e.date)

    def upcoming_events(self, days: int = 7) -> list[dict]:
        """
        Get upcoming economic events.

        Args:
            days: Number of days to look ahead

        Returns:
            List of event dicts sorted by date
        """
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)

        events = self._generate_recurring(now, end)
        # Add custom events in range
        for e in self._custom_events:
            if now <= e.date <= end:
                events.append(e)

        events.sort(key=lambda e: e.date)
        return [
            {
                'name': e.name,
                'date': e.date.isoformat(),
                'country': e.country,
                'impact': e.impact,
                'category': e.category,
                'forecast': e.forecast,
                'previous': e.previous,
            }
            for e in events
        ]

    def high_impact_events(self, days: int = 7) -> list[dict]:
        """Get only high-impact upcoming events."""
        return [e for e in self.upcoming_events(days) if e['impact'] == 'high']

    def historical_impact(self, event_type: str) -> dict:
        """
        Get historical market impact statistics for an event type.

        Args:
            event_type: Event name (e.g. 'Non-Farm Payrolls')

        Returns:
            Dict with avg_move, max_move, direction_bias
        """
        return _HISTORICAL_IMPACT.get(event_type, {
            'avg_move': 0.0,
            'max_move': 0.0,
            'direction_bias': 'unknown',
        })

    def events_by_category(self, category: str, days: int = 30) -> list[dict]:
        """Get upcoming events filtered by category."""
        return [e for e in self.upcoming_events(days) if e['category'] == category]
