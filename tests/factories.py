from datetime import date
from decimal import Decimal

from subs.forms.subscription import SubscriptionInput
from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.models.subscription import Subscription


def subscription_input() -> SubscriptionInput:
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
        "image_url": "https://cdn.example.com/netflix.png",
    }


def make_subscription(
    *,
    id: int = 1,
    active: bool = True,
    end_date: date | None = None,
    service: str = "Netflix",
    start_date: date = date(2026, 1, 31),
    category: Category = Category.ENTERTAINMENT,
    billing_period: BillingPeriod = BillingPeriod.MONTH,
    billing_interval: int = 1,
    billing_date_offset: int = 2,
    payment_method: PaymentMethod = PaymentMethod.MBANK_MASTERCARD,
    cost: Decimal = Decimal("12.90"),
    url: str | None = "https://www.netflix.com/account",
    image_url: str | None = "https://cdn.example.com/netflix.png",
) -> Subscription:
    subscription = Subscription(
        service=service,
        start_date=start_date,
        category=category,
        billing_period=billing_period,
        billing_interval=billing_interval,
        billing_date_offset=billing_date_offset,
        payment_method=payment_method,
        cost=cost,
        url=url,
        image_url=image_url,
        active=active,
        end_date=end_date,
    )
    subscription.id = id
    return subscription
