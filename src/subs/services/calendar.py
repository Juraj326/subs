from collections.abc import Iterable
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from flask import current_app
from icalendar import Calendar, Event

from subs.models.subscription import Subscription
from subs.repositories.subscription import get_all_subscriptions
from subs.services.subscription import get_renewals, local_today


def get_calendar_ics(as_of: date | None = None) -> bytes:
    if as_of is None:
        as_of = local_today(current_app.config["TIMEZONE"])

    range_end = as_of + relativedelta(months=12)
    calendar = build_calendar(
        get_all_subscriptions(),
        as_of,
        range_end,
        as_of,
    )

    return calendar.to_ical()


def build_calendar(
    subscriptions: Iterable[Subscription],
    range_start: date,
    range_end: date,
    as_of: date | None = None,
) -> Calendar:
    calendar = Calendar.new(
        name="Subscriptions",
        uid="subscriptions-calendar@subs",
        color="green",
    )

    for subscription in subscriptions:
        if subscription.active:
            renewals = get_renewals(
                subscription.start_date,
                subscription.billing_period,
                subscription.billing_interval,
                range_start,
                range_end,
                as_of,
            )
            for renewal in renewals:
                calendar.add_component(_build_event(subscription, day=renewal))
        else:
            if subscription.end_date is None:
                continue
            if range_start <= subscription.end_date <= range_end:
                calendar.add_component(
                    _build_event(
                        subscription,
                        subscription.end_date,
                    )
                )

    return calendar


def _build_event(subscription: Subscription, day: date) -> Event:
    return Event.new(
        uid=(f"subscription-{subscription.id}-{day.strftime('%Y%m%d')}@subs"),
        summary=f"{subscription.service}",
        start=day,
        end=day + timedelta(days=1),
        url=subscription.url,
        description=_event_description(subscription),
    )


def _event_description(subscription: Subscription) -> str:
    if subscription.billing_interval == 1:
        billing_description = f"Every {subscription.billing_period.value}"
    else:
        billing_description = f"Every {subscription.billing_interval} {subscription.billing_period.value}s"
    return (
        f"{subscription.category.value}\n"
        f"{billing_description}\n"
        f"{subscription.cost:.2f} EUR\n"
        f"{subscription.payment_method.value}"
    )
