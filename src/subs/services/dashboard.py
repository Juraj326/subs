from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.subscription import Subscription
from subs.services.subscription import get_next_access_date


@dataclass(frozen=True)
class NormalizedCost:
    monthly: Fraction
    yearly: Fraction


@dataclass(frozen=True)
class SubscriptionRow:
    subscription: Subscription
    next_access_date: date | None
    monthly_cost: Fraction
    yearly_cost: Fraction


@dataclass(frozen=True)
class SubscriptionSpending:
    service: str
    monthly_cost: Fraction
    yearly_cost: Fraction


@dataclass(frozen=True)
class CategorySpending:
    category: Category
    monthly_cost: Fraction
    yearly_cost: Fraction
    subscriptions: tuple[SubscriptionSpending, ...]


@dataclass(frozen=True)
class DashboardData:
    rows: tuple[SubscriptionRow, ...]
    monthly_spend: Fraction
    yearly_spend: Fraction
    active_count: int
    category_spending: tuple[CategorySpending, ...]


def normalize_cost(
    cost: Decimal,
    billing_period: BillingPeriod,
    billing_interval: int,
) -> NormalizedCost:
    if billing_interval < 1:
        raise ValueError("billing_interval must be at least 1")

    rate = Fraction(cost) / billing_interval
    if billing_period is BillingPeriod.DAY:
        yearly = rate * 365
    elif billing_period is BillingPeriod.WEEK:
        yearly = rate * 52
    elif billing_period is BillingPeriod.MONTH:
        yearly = rate * 12
    else:
        yearly = rate

    return NormalizedCost(monthly=yearly / 12, yearly=yearly)


def build_dashboard_data(
    subscriptions: Iterable[Subscription],
    as_of: date,
) -> DashboardData:
    ordered_subscriptions = sorted(subscriptions, key=lambda item: item.service.casefold())
    rows: list[SubscriptionRow] = []
    yearly_spend = Fraction(0)
    active_count = 0
    category_yearly_totals = {category: Fraction(0) for category in Category}
    category_subscriptions: dict[Category, list[SubscriptionSpending]] = {category: [] for category in Category}

    for subscription in ordered_subscriptions:
        normalized = normalize_cost(
            subscription.cost,
            subscription.billing_period,
            subscription.billing_interval,
        )
        next_access_date = None

        if subscription.active:
            next_access_date = get_next_access_date(
                subscription.start_date,
                subscription.billing_period,
                subscription.billing_interval,
                subscription.billing_date_offset,
                as_of,
            )
            active_count += 1
            yearly_spend += normalized.yearly
            category_yearly_totals[subscription.category] += normalized.yearly
            category_subscriptions[subscription.category].append(
                SubscriptionSpending(
                    service=subscription.service,
                    monthly_cost=normalized.monthly,
                    yearly_cost=normalized.yearly,
                )
            )

        rows.append(
            SubscriptionRow(
                subscription=subscription,
                next_access_date=next_access_date,
                monthly_cost=normalized.monthly,
                yearly_cost=normalized.yearly,
            )
        )

    category_spending = tuple(
        CategorySpending(
            category=category,
            monthly_cost=yearly_cost / 12,
            yearly_cost=yearly_cost,
            subscriptions=tuple(category_subscriptions[category]),
        )
        for category, yearly_cost in sorted(category_yearly_totals.items(), key=lambda item: (-item[1], item[0].value))
        if yearly_cost > 0
    )

    return DashboardData(
        rows=tuple(rows),
        monthly_spend=yearly_spend / 12,
        yearly_spend=yearly_spend,
        active_count=active_count,
        category_spending=category_spending,
    )
