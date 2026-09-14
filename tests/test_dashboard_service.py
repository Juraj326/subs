from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest
from factories import make_subscription

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.services.dashboard import build_dashboard_data, normalize_cost


@pytest.mark.parametrize(
    ("period", "interval", "cost", "expected_yearly"),
    [
        (BillingPeriod.DAY, 2, Decimal(10), Decimal(1825)),
        (BillingPeriod.WEEK, 2, Decimal(10), Decimal(260)),
        (BillingPeriod.MONTH, 3, Decimal(10), Decimal(40)),
        (BillingPeriod.YEAR, 2, Decimal(120), Decimal(60)),
    ],
)
def test_normalized_cost_for_each_period_and_interval(
    period: BillingPeriod, interval: int, cost: Decimal, expected_yearly: Decimal
) -> None:
    normalized = normalize_cost(cost, period, interval)

    assert normalized.yearly == expected_yearly
    assert normalized.monthly == Fraction(expected_yearly) / 12


def test_totals_and_categories_include_only_active_costs_without_early_rounding() -> None:
    daily = make_subscription(
        id=1,
        service="Daily",
        category=Category.ESSENTIAL,
        billing_period=BillingPeriod.DAY,
        billing_interval=3,
        cost=Decimal("0.01"),
    )
    yearly = make_subscription(
        id=2,
        service="Yearly",
        category=Category.PROFESSIONAL,
        billing_period=BillingPeriod.YEAR,
        billing_interval=2,
        cost=Decimal("120.00"),
    )
    cancelled = make_subscription(
        id=3,
        service="Cancelled",
        category=Category.PROFESSIONAL,
        active=False,
        end_date=date(2026, 7, 1),
        cost=Decimal("999.99"),
    )

    dashboard = build_dashboard_data([yearly, cancelled, daily], date(2026, 8, 30))
    daily_yearly = Fraction(73, 60)
    yearly_yearly = Fraction(60)

    assert dashboard.active_count == 2
    assert dashboard.yearly_spend == daily_yearly + yearly_yearly
    assert dashboard.monthly_spend == Fraction(3673, 720)
    assert {
        group.category: (group.monthly_cost, group.yearly_cost, [item.service for item in group.subscriptions])
        for group in dashboard.category_spending
    } == {
        Category.PROFESSIONAL: (Fraction(5), yearly_yearly, ["Yearly"]),
        Category.ESSENTIAL: (Fraction(73, 720), daily_yearly, ["Daily"]),
    }


def test_empty_dashboard_has_zero_spending() -> None:
    dashboard = build_dashboard_data([], date(2026, 8, 30))

    assert dashboard.active_count == 0
    assert dashboard.monthly_spend == dashboard.yearly_spend == Decimal(0)
    assert not dashboard.category_spending
