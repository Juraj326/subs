from sqlalchemy import func

from subs.extensions import db
from subs.models.subscription import Subscription


def get_all_subscriptions() -> list[Subscription]:
    result = db.session.scalars(db.select(Subscription).order_by(Subscription.service))
    return list(result)


def get_active_subscriptions() -> list[Subscription]:
    result = db.session.scalars(
        db.select(Subscription).where(Subscription.active == True).order_by(Subscription.service)
    )
    return list(result)


def get_cancelled_subscriptions() -> list[Subscription]:
    result = db.session.scalars(
        db.select(Subscription)
        .where(Subscription.active == False)
        .order_by(Subscription.service, Subscription.end_date)
    )
    return list(result)


def get_subscription_by_id(subscription_id: int) -> Subscription | None:
    return db.session.get(Subscription, subscription_id)


def get_subscription_by_service(service: str, exclude_subscription_id: int | None = None) -> Subscription | None:
    statement = db.select(Subscription).where(
        func.lower(func.btrim(Subscription.service)) == service.strip().lower(),
    )
    if exclude_subscription_id is not None:
        statement = statement.where(Subscription.id != exclude_subscription_id)

    return db.session.scalar(statement)


def add_subscription(subscription: Subscription) -> None:
    db.session.add(subscription)


def delete_subscription(subscription: Subscription) -> None:
    db.session.delete(subscription)
