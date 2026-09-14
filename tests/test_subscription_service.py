from datetime import date

import pytest
from conftest import Repository
from factories import ScheduleChanges, make_subscription, subscription_input

from subs.models.enums.billing_period import BillingPeriod
from subs.services.subscription import correct_cancelled_expiration, update_subscription


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"billing_period": BillingPeriod.YEAR}, date(2027, 1, 20)),
        ({"billing_date_offset": -5}, date(2026, 9, 10)),
        ({"start_date": date(2026, 1, 16), "billing_interval": 3}, date(2026, 10, 21)),
    ],
)
def test_cancelled_corrections_keep_recorded_cycle_across_later_edits(
    repository: Repository, changes: ScheduleChanges, expected: date
) -> None:
    original = subscription_input() | {"start_date": date(2026, 1, 15), "billing_date_offset": 5}
    saved = make_subscription(**original, active=False, end_date=date(2026, 9, 20))
    repository.rows.append(saved)

    for as_of in (date(2026, 9, 10), date(2027, 3, 10)):
        updated = update_subscription(subscription_id=1, **original | changes, active=False, as_of=as_of)
        assert updated.end_date == expected
    assert repository.commit.call_count == 2


@pytest.mark.parametrize(
    ("period", "interval", "offset", "expiration"),
    [
        (BillingPeriod.MONTH, 1, -5, date(2026, 1, 10)),
    ],
)
def test_valid_current_expiration_is_preserved(
    period: BillingPeriod, interval: int, offset: int, expiration: date
) -> None:
    anchor = date(2026, 1, 15)
    saved = make_subscription(
        start_date=anchor,
        billing_period=period,
        billing_interval=interval,
        billing_date_offset=offset,
        active=False,
        end_date=expiration,
    )

    assert correct_cancelled_expiration(saved, anchor, period, interval, offset) == expiration


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {
                "start_date": date(2026, 1, 20),
                "billing_period": BillingPeriod.YEAR,
                "billing_interval": 2,
                "billing_date_offset": -3,
            },
            date(2028, 1, 17),
        ),
    ],
)
def test_legacy_correction_uses_old_schedule_before_applying_changes(
    repository: Repository, changes: ScheduleChanges, expected: date
) -> None:
    original = subscription_input() | {"start_date": date(2026, 1, 15), "billing_date_offset": -5}
    saved = make_subscription(**original, active=False, end_date=date(2026, 9, 15))
    repository.rows.append(saved)

    updated = update_subscription(subscription_id=1, **original | changes, active=False, as_of=date(2027, 3, 10))

    assert updated.end_date == expected
    repository.commit.assert_called_once_with()


@pytest.mark.parametrize(
    ("anchor", "period", "offset", "expiration", "corrected", "expected"),
    [
        (date(2026, 1, 31), BillingPeriod.MONTH, -5, date(2026, 2, 28), date(2026, 1, 30), date(2026, 2, 23)),
        (date(2024, 2, 29), BillingPeriod.YEAR, -5, date(2025, 2, 28), date(2024, 2, 28), date(2025, 2, 23)),
    ],
)
def test_cancelled_correction_preserves_clamped_occurrence_index(
    anchor: date, period: BillingPeriod, offset: int, expiration: date, corrected: date, expected: date
) -> None:
    saved = make_subscription(
        start_date=anchor, billing_period=period, billing_date_offset=offset, active=False, end_date=expiration
    )

    assert correct_cancelled_expiration(saved, corrected, period, 1, offset) == expected
