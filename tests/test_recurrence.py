from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from subs.models.enums.billing_period import BillingPeriod
from subs.services.subscription import (
    get_access_renewals,
    get_billing_and_expiration_date,
    get_next_access_date,
    local_today,
)


@pytest.mark.parametrize(
    ("period", "interval", "expected"),
    [
        (BillingPeriod.DAY, 3, [date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 7)]),
        (BillingPeriod.WEEK, 2, [date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 29)]),
        (BillingPeriod.MONTH, 2, [date(2026, 1, 31), date(2026, 3, 31), date(2026, 5, 31)]),
        (BillingPeriod.YEAR, 2, [date(2024, 2, 29), date(2026, 2, 28), date(2028, 2, 29)]),
    ],
)
def test_billing_periods_and_intervals(period: BillingPeriod, interval: int, expected: list[date]) -> None:
    assert get_access_renewals(expected[0], period, interval, 0, expected[0], expected[-1]) == expected


def test_month_end_anchor_clamps_without_drifting() -> None:
    anchor_day = 31
    renewals = get_access_renewals(
        date(2026, 1, anchor_day), BillingPeriod.MONTH, 1, 0, date(2026, 1, 1), date(2026, 4, 30)
    )

    assert renewals == [
        date(2026, 1, anchor_day),
        date(2026, 2, 28),
        date(2026, 3, anchor_day),
        date(2026, 4, min(anchor_day, 30)),
    ]


def test_leap_day_anchor_returns_to_leap_day() -> None:
    assert get_access_renewals(date(2024, 2, 29), BillingPeriod.YEAR, 1, 0, date(2024, 1, 1), date(2028, 12, 31)) == [
        date(2024, 2, 29),
        date(2025, 2, 28),
        date(2026, 2, 28),
        date(2027, 2, 28),
        date(2028, 2, 29),
    ]


@pytest.mark.parametrize(
    ("offset", "as_of", "expected"),
    [
        (0, date(2026, 9, 15), date(2026, 10, 15)),
        (5, date(2026, 9, 15), date(2026, 9, 20)),
        (-5, date(2026, 9, 10), date(2026, 9, 10)),
    ],
)
def test_initial_payment_and_shifted_access_selection(offset: int, as_of: date, expected: date) -> None:
    assert get_next_access_date(date(2026, 9, 15), BillingPeriod.MONTH, 1, offset, as_of) == expected


@pytest.mark.parametrize(
    ("offset", "expiration"),
    [(-5, date(2026, 3, 26)), (5, date(2026, 4, 5))],
)
def test_cancellation_skips_today_charge_and_applies_signed_access_offset(offset: int, expiration: date) -> None:
    assert get_billing_and_expiration_date(date(2026, 1, 31), BillingPeriod.MONTH, 1, offset, date(2026, 2, 28)) == (
        date(2026, 3, 31),
        expiration,
    )


def test_cancellation_before_start_keeps_first_future_charge() -> None:
    assert get_billing_and_expiration_date(date(2026, 9, 10), BillingPeriod.MONTH, 1, 0, date(2026, 9, 9)) == (
        date(2026, 9, 10),
        date(2026, 9, 10),
    )


def test_range_and_as_of_boundaries_are_inclusive() -> None:
    assert get_access_renewals(
        date(2026, 1, 1), BillingPeriod.MONTH, 1, 0, date(2026, 1, 1), date(2026, 4, 1), date(2026, 2, 1)
    ) == [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]


def test_window_only_filters_events_selected_at_evaluation_date() -> None:
    offset = 5
    as_of = date(2026, 9, 15)
    start = date(2026, 9, 15)
    end = date(2026, 12, 31)
    events = get_access_renewals(start, BillingPeriod.MONTH, 1, offset, date(2026, 9, 1), end, as_of)

    assert events[0] == get_next_access_date(start, BillingPeriod.MONTH, 1, offset, as_of)
    window_start = date(2026, 11, 1)
    assert get_access_renewals(start, BillingPeriod.MONTH, 1, offset, window_start, end, as_of) == [
        event for event in events if event >= window_start
    ]


def test_omitted_as_of_does_not_mark_initial_payment_as_paid() -> None:
    range_start = date(2026, 9, 15)
    assert get_access_renewals(date(2026, 9, 15), BillingPeriod.MONTH, 1, 0, range_start, date(2026, 10, 15)) == [
        date(2026, 9, 15),
        date(2026, 10, 15),
    ]


def test_access_window_without_events() -> None:
    range_start = date(2026, 9, 16)
    range_end = date(2026, 10, 14)
    as_of = None
    assert get_access_renewals(date(2026, 9, 15), BillingPeriod.MONTH, 1, 0, range_start, range_end, as_of) == []


def test_local_today_respects_timezone_boundary() -> None:
    now = datetime(2026, 8, 25, 22, 30, tzinfo=UTC)

    assert local_today(ZoneInfo("Europe/Bratislava"), now) == date(2026, 8, 26)
    assert local_today(ZoneInfo("America/New_York"), now) == date(2026, 8, 25)
