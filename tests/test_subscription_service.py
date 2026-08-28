from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.models.subscription import Subscription
from subs.services import subscription as subscription_service
from subs.services.subscription import (
    DuplicateSubscriptionError,
    SubscriptionNotFoundError,
    SubscriptionValidationError,
)


def _valid_fields() -> dict[str, object]:
    return {
        "service": "Netflix",
        "start_date": date(2026, 1, 31),
        "category": Category.ENTERTAINMENT,
        "billing_period": BillingPeriod.MONTH,
        "billing_interval": 1,
        "billing_date_offset": 2,
        "payment_method": PaymentMethod.MBANK_MASTERCARD,
        "cost": Decimal("12.90"),
        "url": "https://www.netflix.com/account",
    }


def _subscription(**overrides: object) -> Subscription:
    fields = _valid_fields()
    fields.update(overrides)
    subscription = Subscription(
        service=cast(str, fields["service"]),
        start_date=cast(date, fields["start_date"]),
        category=cast(Category, fields["category"]),
        active=cast(bool, fields.get("active", True)),
        end_date=cast(date | None, fields.get("end_date")),
        billing_period=cast(BillingPeriod, fields["billing_period"]),
        billing_interval=cast(int, fields["billing_interval"]),
        billing_date_offset=cast(int, fields["billing_date_offset"]),
        payment_method=cast(PaymentMethod, fields["payment_method"]),
        cost=cast(Decimal, fields["cost"]),
        url=cast(str | None, fields["url"]),
    )
    subscription.id = cast(int, fields.get("id", 1))
    return subscription


def _create(fields: dict[str, object]) -> Subscription:
    return subscription_service.create_subscription(
        service=cast(str, fields["service"]),
        start_date=cast(date, fields["start_date"]),
        category=cast(Category, fields["category"]),
        billing_period=cast(BillingPeriod, fields["billing_period"]),
        billing_interval=cast(int, fields["billing_interval"]),
        billing_date_offset=cast(int, fields["billing_date_offset"]),
        payment_method=cast(PaymentMethod, fields["payment_method"]),
        cost=cast(Decimal, fields["cost"]),
        url=cast(str | None, fields["url"]),
    )


def _update(
    subscription_id: int,
    fields: dict[str, object],
    active: bool = True,
    as_of: date | None = None,
) -> Subscription:
    return subscription_service.update_subscription(
        subscription_id=subscription_id,
        active=active,
        service=cast(str, fields["service"]),
        start_date=cast(date, fields["start_date"]),
        category=cast(Category, fields["category"]),
        billing_period=cast(BillingPeriod, fields["billing_period"]),
        billing_interval=cast(int, fields["billing_interval"]),
        billing_date_offset=cast(int, fields["billing_date_offset"]),
        payment_method=cast(PaymentMethod, fields["payment_method"]),
        cost=cast(Decimal, fields["cost"]),
        url=cast(str | None, fields["url"]),
        as_of=as_of,
    )


def test_create_subscription_stages_and_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    added: list[Subscription] = []
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "add_subscription",
        added.append,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)
    fields = _valid_fields()

    created = _create(fields)

    assert added == [created]
    assert created.service == "Netflix"
    assert created.start_date == date(2026, 1, 31)
    assert created.cost == Decimal("12.90")
    assert created.url == "https://www.netflix.com/account"
    assert created.active is True
    assert created.end_date is None
    commit.assert_called_once_with()


def test_create_rejects_existing_service_regardless_of_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _subscription(active=False, end_date=date(2026, 2, 2))
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: existing,
    )

    with pytest.raises(DuplicateSubscriptionError):
        _create(_valid_fields())


def test_update_changes_only_explicit_editable_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription()
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)
    fields = _valid_fields()
    fields.update(
        service="Nebula",
        start_date=date(2026, 2, 10),
        billing_interval=3,
        cost=Decimal("8.00"),
    )

    updated = _update(1, fields)

    assert updated is subscription
    assert updated.service == "Nebula"
    assert updated.start_date == date(2026, 2, 10)
    assert updated.billing_interval == 3
    assert updated.cost == Decimal("8.00")
    assert updated.active is True
    commit.assert_called_once_with()


def test_update_rejects_another_existing_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription(id=1)
    other_subscription = _subscription(id=2, service="Nebula")
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: other_subscription,
    )

    with pytest.raises(DuplicateSubscriptionError):
        _update(1, _valid_fields())


def test_active_subscription_ignores_an_existing_end_date_on_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription(active=True, end_date=date(2025, 1, 1))
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(subscription_service, "_commit", Mock())

    updated = _update(1, _valid_fields())

    assert updated.end_date == date(2025, 1, 1)


def test_update_to_cancelled_stores_expiration_from_submitted_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription()
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)

    fields = _valid_fields()
    fields.update(
        start_date=date(2026, 2, 10),
        billing_interval=3,
        billing_date_offset=5,
    )

    updated = _update(
        1,
        fields,
        active=False,
        as_of=date(2026, 2, 28),
    )

    assert updated is subscription
    assert subscription.active is False
    assert subscription.end_date == date(2026, 5, 15)
    commit.assert_called_once_with()


def test_update_while_cancelled_preserves_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription(active=False, end_date=date(2026, 3, 2))
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)

    updated = _update(
        1,
        _valid_fields(),
        active=False,
        as_of=date(2026, 4, 1),
    )

    assert updated.active is False
    assert updated.end_date == date(2026, 3, 2)
    commit.assert_called_once_with()


def test_update_to_active_keeps_ignored_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription(active=False, end_date=date(2026, 3, 2))
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_service",
        lambda service, exclude_subscription_id=None: None,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)

    updated = _update(1, _valid_fields(), active=True)

    assert updated.active is True
    assert updated.end_date == date(2026, 3, 2)
    commit.assert_called_once_with()


def test_delete_stages_deletion_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    subscription = _subscription()
    deleted: list[Subscription] = []
    commit = Mock()
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: subscription,
    )
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "delete_subscription",
        deleted.append,
    )
    monkeypatch.setattr(subscription_service, "_commit", commit)

    result = subscription_service.delete_subscription(1)

    assert result is subscription
    assert deleted == [subscription]
    commit.assert_called_once_with()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_missing_subscription_raises_typed_error(operation: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subscription_service.subscription_repository,
        "get_subscription_by_id",
        lambda subscription_id: None,
    )

    with pytest.raises(SubscriptionNotFoundError):
        if operation == "update":
            _update(404, _valid_fields())
        else:
            subscription_service.delete_subscription(404)


class _UniqueViolation(Exception):
    diag = SimpleNamespace(constraint_name="subscriptions_service_key")


def test_integrity_error_rolls_back_and_becomes_typed_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    session.commit.side_effect = IntegrityError("INSERT", {}, _UniqueViolation())
    monkeypatch.setattr(subscription_service, "db", SimpleNamespace(session=session))

    with pytest.raises(DuplicateSubscriptionError):
        subscription_service._commit()

    session.rollback.assert_called_once_with()


def test_other_integrity_error_rolls_back_and_becomes_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Mock()
    session.commit.side_effect = IntegrityError("INSERT", {}, Exception("check"))
    monkeypatch.setattr(subscription_service, "db", SimpleNamespace(session=session))

    with pytest.raises(SubscriptionValidationError):
        subscription_service._commit()

    session.rollback.assert_called_once_with()
