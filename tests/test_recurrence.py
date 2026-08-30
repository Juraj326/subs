from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from subs.models.enums.billing_period import BillingPeriod
from subs.services.subscription import (
    get_billing_and_expiration_date,
    get_next_billing_date,
    get_renewals,
    local_today,
)


@pytest.mark.parametrize(
    ("period", "start_date", "as_of", "expected"),
    [
        (BillingPeriod.DAY, date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 3)),
        (
            BillingPeriod.WEEK,
            date(2026, 1, 5),
            date(2026, 1, 12),
            date(2026, 1, 12),
        ),
        (
            BillingPeriod.MONTH,
            date(2026, 1, 15),
            date(2026, 2, 16),
            date(2026, 3, 15),
        ),
        (
            BillingPeriod.YEAR,
            date(2024, 6, 1),
            date(2026, 6, 2),
            date(2027, 6, 1),
        ),
    ],
)
def test_next_billing_date_for_each_period(
    period: BillingPeriod,
    start_date: date,
    as_of: date,
    expected: date,
) -> None:
    assert (
        get_next_billing_date(
            start_date,
            period,
            1,
            as_of,
        )
        == expected
    )


def test_charge_due_today_is_the_next_charge() -> None:
    assert get_next_billing_date(
        date(2026, 1, 31),
        BillingPeriod.MONTH,
        1,
        date(2026, 2, 28),
    ) == date(2026, 2, 28)


@pytest.mark.parametrize("anchor_day", [29, 30, 31])
def test_month_end_anchors_clamp_without_drifting(anchor_day: int) -> None:
    renewals = get_renewals(
        date(2026, 1, anchor_day),
        BillingPeriod.MONTH,
        1,
        date(2026, 1, 1),
        date(2026, 4, 30),
    )

    assert renewals == [
        date(2026, 1, anchor_day),
        date(2026, 2, 28),
        date(2026, 3, anchor_day),
        date(2026, 4, min(anchor_day, 30)),
    ]


def test_leap_day_anchor_returns_to_leap_day() -> None:
    renewals = get_renewals(
        date(2024, 2, 29),
        BillingPeriod.YEAR,
        1,
        date(2024, 1, 1),
        date(2028, 12, 31),
    )

    assert renewals == [
        date(2024, 2, 29),
        date(2025, 2, 28),
        date(2026, 2, 28),
        date(2027, 2, 28),
        date(2028, 2, 29),
    ]


@pytest.mark.parametrize(
    ("period", "interval", "expected"),
    [
        (
            BillingPeriod.DAY,
            3,
            [date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 7)],
        ),
        (
            BillingPeriod.WEEK,
            2,
            [date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 29)],
        ),
        (
            BillingPeriod.MONTH,
            2,
            [date(2026, 1, 31), date(2026, 3, 31), date(2026, 5, 31)],
        ),
        (
            BillingPeriod.YEAR,
            2,
            [date(2024, 2, 29), date(2026, 2, 28), date(2028, 2, 29)],
        ),
    ],
)
def test_multi_interval_renewals(period: BillingPeriod, interval: int, expected: list[date]) -> None:
    start_date = expected[0]
    assert (
        get_renewals(
            start_date,
            period,
            interval,
            start_date,
            expected[-1],
        )
        == expected
    )


def test_range_and_as_of_boundaries_are_inclusive() -> None:
    renewals = get_renewals(
        date(2026, 1, 1),
        BillingPeriod.MONTH,
        1,
        date(2026, 1, 1),
        date(2026, 4, 1),
        date(2026, 2, 1),
    )

    assert renewals == [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (-5, (date(2026, 2, 23), date(2026, 2, 28))),
        (0, (date(2026, 2, 28), date(2026, 2, 28))),
        (5, (date(2026, 2, 28), date(2026, 3, 5))),
    ],
)
def test_signed_offset_positions_billing_and_expiration_dates(
    offset: int,
    expected: tuple[date, date],
) -> None:
    assert (
        get_billing_and_expiration_date(
            date(2026, 1, 31),
            BillingPeriod.MONTH,
            1,
            offset,
            date(2026, 2, 28),
        )
        == expected
    )


def test_local_today_respects_timezone_boundary() -> None:
    now = datetime(2026, 8, 25, 22, 30, tzinfo=UTC)

    assert local_today(ZoneInfo("Europe/Bratislava"), now) == date(2026, 8, 26)
    assert local_today(ZoneInfo("America/New_York"), now) == date(2026, 8, 25)
