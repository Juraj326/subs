from datetime import date
from typing import Any

from factories import make_subscription
from icalendar import Calendar

from subs.services.calendar import build_calendar
from subs.services.dashboard import build_dashboard_data


def _events(calendar: Calendar) -> list[Any]:
    return list(calendar.walk("VEVENT"))


def test_calendar_serializes_all_day_occurrences_with_stable_unique_ids() -> None:
    saved = make_subscription(start_date=date(2026, 1, 15), billing_date_offset=5)
    calendar = build_calendar([saved], date(2026, 2, 1), date(2026, 3, 31), date(2026, 2, 1))
    events = _events(Calendar.from_ical(calendar.to_ical()))

    assert [event.decoded("DTSTART") for event in events] == [date(2026, 2, 20), date(2026, 3, 20)]
    assert [event.decoded("DTEND") for event in events] == [date(2026, 2, 21), date(2026, 3, 21)]
    assert [str(event["UID"]) for event in events] == ["subscription-1-20260220@subs", "subscription-1-20260320@subs"]
    later = build_calendar([saved], date(2026, 3, 1), date(2026, 3, 31), date(2026, 3, 1))
    assert _events(later)[0]["UID"] == events[1]["UID"]


def test_cancelled_subscription_only_emits_expiration_in_feed_window() -> None:
    subscriptions = [
        make_subscription(id=1, active=False, end_date=date(2026, 6, 1)),
        make_subscription(id=2, active=False, end_date=date(2025, 12, 31)),
        make_subscription(id=3, active=False, end_date=date(2027, 2, 1)),
    ]

    events = _events(build_calendar(subscriptions, date(2026, 1, 1), date(2027, 1, 1), date(2026, 1, 1)))

    assert len(events) == 1
    assert str(events[0]["UID"]) == "subscription-1-20260601@subs"
    assert events[0].decoded("DTSTART") == date(2026, 6, 1)
    assert events[0].decoded("DTEND") == date(2026, 6, 2)


def test_dashboard_and_calendar_use_shifted_access_dates() -> None:
    offset = -5
    as_of = date(2026, 9, 10)
    expected = date(2026, 9, 10)
    saved = make_subscription(start_date=date(2026, 9, 15), billing_date_offset=offset)
    dashboard = build_dashboard_data([saved], as_of)
    calendar = build_calendar([saved], as_of, date(2026, 12, 31), as_of)

    assert dashboard.rows[0].next_access_date == expected
    assert _events(calendar)[0].decoded("DTSTART") == expected
