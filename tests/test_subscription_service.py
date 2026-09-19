from datetime import date
from decimal import Decimal

import pytest
from conftest import Repository
from factories import make_subscription, subscription_input

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.services.subscription import update_subscription


@pytest.mark.parametrize("expiration", [date(2026, 9, 10), date(2026, 9, 15), date(2026, 9, 14)])
def test_repeated_cancelled_edits_only_update_service_details(repository: Repository, expiration: date) -> None:
    saved = make_subscription(start_date=date(2026, 1, 15), billing_date_offset=-5, active=False, end_date=expiration)
    repository.rows.append(saved)
    protected = {
        name: getattr(saved, name)
        for name in (*subscription_input(), "active", "end_date")
        if name not in {"service", "url", "image_url"}
    }
    changes = subscription_input() | {
        "start_date": date(2026, 1, 20),
        "category": Category.PROFESSIONAL,
        "billing_period": BillingPeriod.YEAR,
        "billing_interval": 2,
        "billing_date_offset": 7,
        "payment_method": PaymentMethod.MBANK_VISA,
        "cost": Decimal("25.00"),
        "url": "https://changed.example.com",
        "image_url": None,
    }

    for as_of, service in [(date(2026, 9, 10), "Changed"), (date(2027, 3, 10), "Changed again")]:
        updated = update_subscription(subscription_id=1, **changes | {"service": service}, active=False, as_of=as_of)
        assert {name: getattr(updated, name) for name in protected} == protected
        assert (updated.service, updated.url, updated.image_url) == (service, changes["url"], None)
    assert repository.commit.call_count == 2


@pytest.mark.parametrize("active", [False, True], ids=["cancel", "reactivate"])
def test_status_change_saves_all_pending_details(repository: Repository, active: bool) -> None:
    saved = make_subscription(active=not active, end_date=date(2026, 3, 2) if active else None)
    repository.rows.append(saved)
    changes = subscription_input() | {
        "service": "Changed",
        "start_date": date(2026, 1, 20),
        "category": Category.PROFESSIONAL,
        "billing_period": BillingPeriod.YEAR,
        "billing_interval": 2,
        "billing_date_offset": -3,
        "payment_method": PaymentMethod.MBANK_VISA,
        "cost": Decimal("25.00"),
        "url": None,
        "image_url": None,
    }

    updated = update_subscription(subscription_id=1, **changes, active=active, as_of=date(2026, 9, 19))

    assert {name: getattr(updated, name) for name in changes} == changes
    assert updated.active is active
    assert updated.end_date == (None if active else date(2028, 1, 17))
    repository.commit.assert_called_once_with()
