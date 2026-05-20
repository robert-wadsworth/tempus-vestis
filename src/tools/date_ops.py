from datetime import datetime, timedelta

import dateparser
from langchain_core.tools import tool

_WEEKDAY_NAMES: dict[str, int] = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2,
    'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
}


def _days_until_weekday(today_weekday: int, target_weekday: int) -> int:
    """Return the number of days from today until the next occurrence of target_weekday.

    Always returns 1–7: if today is already target_weekday, returns 7 (next week).
    """
    delta = (target_weekday - today_weekday) % 7
    return delta if delta != 0 else 7


def _resolve_to_date(expression: str) -> datetime:
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    weekday = today.weekday()  # Mon=0 … Sun=6
    expr = expression.lower().strip()

    if expr == 'today':
        return today

    if expr == 'tomorrow':
        return today + timedelta(days=1)

    # "next weekend" / "this weekend" / "weekend" → nearest upcoming Saturday;
    # if already on Saturday, "next weekend" advances a full week.
    if 'weekend' in expr:
        days = (5 - weekday) % 7          # days to next Saturday (0 if today is Sat)
        if days == 0 and 'next' in expr:   # "next weekend" on a Saturday → following Sat
            days = 7
        return today + timedelta(days=days)

    # "next [weekday]" / "this [weekday]" / bare weekday name
    words = set(expr.split())
    for name, idx in _WEEKDAY_NAMES.items():
        if name in words:
            return today + timedelta(days=_days_until_weekday(weekday, idx))

    # Numeric expressions: "in 7 days", "in 2 weeks", "next week" etc.
    result = dateparser.parse(
        expression,
        settings={'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': False},
    )
    if result is None:
        raise ValueError(f"Could not parse date expression: {expression!r}")
    return result.replace(hour=0, minute=0, second=0, microsecond=0)


@tool
def get_current_date() -> str:
    """Return today's date and day of the week (e.g. '2026-05-20 Wednesday')."""
    now = datetime.now()
    return now.strftime('%Y-%m-%d %A')


@tool
def resolve_travel_date(expression: str) -> str:
    """Resolve a natural language date expression to a calendar date (YYYY-MM-DD).

    Use for relative expressions such as 'next weekend', 'this Friday',
    'next Monday', 'tomorrow', 'in 7 days', 'in 2 weeks', 'next week'.
    Always call get_current_date first so you know today's weekday context.
    """
    return _resolve_to_date(expression).strftime('%Y-%m-%d')


@tool
def calculate_future_date(days: int = 0) -> str:
    """Return the date exactly N days from today (YYYY-MM-DD).

    Use when the user provides an explicit day count ('in 7 days', '14 days from now').
    For natural language expressions use resolve_travel_date instead.
    """
    return (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
