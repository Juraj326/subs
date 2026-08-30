from datetime import date, datetime, timedelta, tzinfo
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from flask import current_app
from sqlalchemy.exc import IntegrityError

from subs.extensions import db
from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.models.subscription import Subscription
from subs.repositories import subscription as subscription_repository

_UNIQUE_SERVICE_CONSTRAINT = "subscriptions_service_key"


class SubscriptionError(Exception):
    """Base class for expected subscription application errors."""


class SubscriptionValidationError(SubscriptionError, ValueError):
    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        message = "; ".join(f"{field}: {error}" for field, error in errors.items())
        super().__init__(message)


class DuplicateSubscriptionError(SubscriptionError):
    def __init__(self, service: str) -> None:
        self.service = service
        super().__init__(f"A subscription for {service!r} already exists")


class SubscriptionNotFoundError(SubscriptionError, LookupError):
    def __init__(self, subscription_id: int) -> None:
        self.subscription_id = subscription_id
        super().__init__(f"Subscription {subscription_id} was not found")


def create_subscription(
    *,
    service: str,
    start_date: date,
    category: Category,
    billing_period: BillingPeriod,
    billing_interval: int,
    billing_date_offset: int,
    payment_method: PaymentMethod,
    cost: Decimal,
    url: str | None,
) -> Subscription:
    _ensure_service_is_unique(service)

    subscription = Subscription(
        service=service,
        start_date=start_date,
        category=category,
        active=True,
        end_date=None,
        billing_period=billing_period,
        billing_interval=billing_interval,
        billing_date_offset=billing_date_offset,
        payment_method=payment_method,
        cost=cost,
        url=url,
    )
    subscription_repository.add_subscription(subscription)

    _commit()
    return subscription


def update_subscription(
    *,
    subscription_id: int,
    active: bool,
    service: str,
    start_date: date,
    category: Category,
    billing_period: BillingPeriod,
    billing_interval: int,
    billing_date_offset: int,
    payment_method: PaymentMethod,
    cost: Decimal,
    url: str | None,
    as_of: date | None = None,
) -> Subscription:
    subscription = _get_subscription(subscription_id)
    _ensure_service_is_unique(service, subscription_id)

    if subscription.active and not active:
        _, subscription.end_date = get_billing_and_expiration_date(
            start_date,
            billing_period,
            billing_interval,
            billing_date_offset,
            as_of,
        )

    subscription.active = active
    subscription.service = service
    subscription.start_date = start_date
    subscription.category = category
    subscription.billing_period = billing_period
    subscription.billing_interval = billing_interval
    subscription.billing_date_offset = billing_date_offset
    subscription.payment_method = payment_method
    subscription.cost = cost
    subscription.url = url

    _commit()
    return subscription


def delete_subscription(subscription_id: int) -> Subscription:
    subscription = _get_subscription(subscription_id)
    subscription_repository.delete_subscription(subscription)

    _commit()
    return subscription


def get_renewals(
    start_date: date,
    billing_period: BillingPeriod,
    billing_interval: int,
    range_start: date,
    range_end: date,
    as_of: date | None = None,
) -> list[date]:
    effective_start = max(range_start, as_of) if as_of is not None else range_start
    if effective_start > range_end:
        return []

    index = _first_renewal_index(start_date, billing_period, billing_interval, effective_start)
    renewals: list[date] = []
    while True:
        renewal = _renewal_at(start_date, billing_period, billing_interval, index)
        if renewal > range_end:
            break
        renewals.append(renewal)
        index += 1

    return renewals


def get_next_billing_date(
    start_date: date,
    billing_period: BillingPeriod,
    billing_interval: int,
    as_of: date,
) -> date:
    index = _first_renewal_index(start_date, billing_period, billing_interval, as_of)

    return _renewal_at(start_date, billing_period, billing_interval, index)


def get_billing_and_expiration_date(
    start_date: date,
    billing_period: BillingPeriod,
    billing_interval: int,
    offset: int,
    as_of: date | None = None,
) -> tuple[date, date]:
    if as_of is None:
        as_of = local_today(current_app.config["TIMEZONE"])

    billing_date = get_next_billing_date(
        start_date,
        billing_period,
        billing_interval,
        as_of,
    )

    if offset < 0:
        return billing_date + timedelta(offset), billing_date
    return billing_date, billing_date + timedelta(offset)


def local_today(timezone: tzinfo, now: datetime | None = None) -> date:
    if now is None:
        now = datetime.now(tz=timezone)
    elif now.tzinfo is None:
        raise ValueError("now must include timezone information")
    else:
        now = now.astimezone(timezone)

    return now.date()


def _first_renewal_index(
    start_date: date,
    billing_period: BillingPeriod,
    billing_interval: int,
    target_date: date,
) -> int:
    if target_date <= start_date:
        return 0

    if billing_period is BillingPeriod.DAY:
        index = (target_date - start_date).days // billing_interval
    elif billing_period is BillingPeriod.WEEK:
        index = (target_date - start_date).days // (7 * billing_interval)
    elif billing_period is BillingPeriod.MONTH:
        elapsed_months = (target_date.year - start_date.year) * 12
        elapsed_months += target_date.month - start_date.month
        index = elapsed_months // billing_interval
    else:
        index = (target_date.year - start_date.year) // billing_interval

    while _renewal_at(start_date, billing_period, billing_interval, index) < target_date:
        index += 1

    return index


def _renewal_at(
    start_date: date,
    billing_period: BillingPeriod,
    billing_interval: int,
    index: int,
) -> date:
    elapsed_intervals = billing_interval * index
    if billing_period is BillingPeriod.DAY:
        delta = relativedelta(days=elapsed_intervals)
    elif billing_period is BillingPeriod.WEEK:
        delta = relativedelta(weeks=elapsed_intervals)
    elif billing_period is BillingPeriod.MONTH:
        delta = relativedelta(months=elapsed_intervals)
    else:
        delta = relativedelta(years=elapsed_intervals)

    return start_date + delta


def _get_subscription(subscription_id: int) -> Subscription:
    subscription = subscription_repository.get_subscription_by_id(subscription_id)
    if subscription is None:
        raise SubscriptionNotFoundError(subscription_id)

    return subscription


def _ensure_service_is_unique(service: str, exclude_subscription_id: int | None = None) -> None:
    existing = subscription_repository.get_subscription_by_service(
        service,
        exclude_subscription_id,
    )
    if existing is not None:
        raise DuplicateSubscriptionError(service)


def _commit() -> None:
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint_name == _UNIQUE_SERVICE_CONSTRAINT or _UNIQUE_SERVICE_CONSTRAINT in str(error.orig):
            raise DuplicateSubscriptionError("the requested service") from error
        raise SubscriptionValidationError({"subscription": "violates a database constraint"}) from error
