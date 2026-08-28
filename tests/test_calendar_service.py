from datetime import date
from decimal import Decimal
from typing import Any, cast

from icalendar import Calendar

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.models.subscription import Subscription
from subs.services.calendar import build_calendar


def _subscription(**overrides: object) -> Subscription:
    values: dict[str, object] = {
        "id": 1,
        "service": "Netflix",
        "start_date": date(2026, 1, 31),
        "category": Category.ENTERTAINMENT,
        "active": True,
        "end_date": None,
        "billing_period": BillingPeriod.MONTH,
        "billing_interval": 1,
        "billing_date_offset": 0,
        "payment_method": PaymentMethod.MBANK_MASTERCARD,
        "cost": Decimal("12.90"),
        "url": "https://www.netflix.com/account",
    }
    values.update(overrides)
    subscription = Subscription(
        service=cast(str, values["service"]),
        start_date=values["start_date"],
        category=cast(Category, values["category"]),
        active=cast(bool, values["active"]),
        end_date=cast(date | None, values["end_date"]),
        billing_period=cast(BillingPeriod, values["billing_period"]),
        billing_interval=cast(int, values["billing_interval"]),
        billing_date_offset=cast(int, values["billing_date_offset"]),
        payment_method=cast(PaymentMethod, values["payment_method"]),
        cost=values["cost"],
        url=cast(str | None, values["url"]),
    )
    subscription.id = cast(int, values["id"])
    return subscription


def _events(calendar: Calendar) -> list[Any]:
    return list(calendar.walk("VEVENT"))


def test_calendar_has_name_stable_uids_and_all_day_occurrences() -> None:
    calendar = build_calendar(
        [_subscription()],
        date(2026, 2, 1),
        date(2026, 4, 30),
        date(2026, 2, 1),
    )
    parsed = Calendar.from_ical(calendar.to_ical())
    events = _events(parsed)

    assert str(parsed["NAME"]) == "Subscriptions"
    assert str(parsed["X-WR-CALNAME"]) == "Subscriptions"
    assert [str(event["UID"]) for event in events] == [
        "subscription-1-20260228@subs",
        "subscription-1-20260331@subs",
        "subscription-1-20260430@subs",
    ]
    assert [event.decoded("DTSTART") for event in events] == [
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]
    assert [event.decoded("DTEND") for event in events] == [
        date(2026, 3, 1),
        date(2026, 4, 1),
        date(2026, 5, 1),
    ]


def test_calendar_window_includes_today_and_exact_twelve_month_boundary() -> None:
    calendar = build_calendar(
        [_subscription(start_date=date(2026, 1, 31))],
        date(2026, 1, 31),
        date(2027, 1, 31),
        date(2026, 1, 31),
    )
    event_dates = [event.decoded("DTSTART") for event in _events(calendar)]

    assert len(event_dates) == 13
    assert event_dates[0] == date(2026, 1, 31)
    assert event_dates[-1] == date(2027, 1, 31)
    assert all(event_date >= date(2026, 1, 31) for event_date in event_dates)


def test_cancelled_subscription_only_emits_future_expiration_in_window() -> None:
    subscriptions = [
        _subscription(id=1, active=False, end_date=date(2026, 6, 1)),
        _subscription(id=2, active=False, end_date=date(2025, 12, 31)),
        _subscription(id=3, active=False, end_date=date(2027, 2, 1)),
    ]

    calendar = build_calendar(
        subscriptions,
        date(2026, 1, 1),
        date(2027, 1, 1),
        date(2026, 1, 1),
    )
    events = _events(calendar)

    assert len(events) == 1
    assert str(events[0]["UID"]) == "subscription-1-20260601@subs"
    assert events[0].decoded("DTSTART") == date(2026, 6, 1)
    assert events[0].decoded("DTEND") == date(2026, 6, 2)


def test_active_subscription_ignores_end_date() -> None:
    calendar = build_calendar(
        [_subscription(active=True, end_date=date(2025, 1, 1))],
        date(2026, 2, 1),
        date(2026, 2, 28),
        date(2026, 2, 1),
    )
    events = _events(calendar)

    assert len(events) == 1
    assert str(events[0]["UID"]) == "subscription-1-20260228@subs"
