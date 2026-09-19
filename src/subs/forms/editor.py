"""Server-owned values for the subscription editor's form controls."""

from typing import TypedDict

from subs.forms.subscription import UpdateSubscriptionForm
from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.models.subscription import Subscription

CANCELLED_PROTECTED_FIELDS = (
    "category",
    "start_date",
    "billing_period",
    "billing_interval",
    "billing_date_offset",
    "payment_method",
    "cost",
)


class EditorValues(TypedDict):
    service: str
    start_date: str
    category: str
    active: str
    billing_period: str
    billing_interval: str
    billing_date_offset: str
    payment_method: str
    cost: str
    url: str
    image_url: str


class EditorSubscriptionPayload(TypedDict):
    id: int
    values: EditorValues
    endDate: str
    editorUrl: str
    updateUrl: str
    removeUrl: str


def editor_values(subscription: Subscription | None = None) -> EditorValues:
    form = UpdateSubscriptionForm(formdata=None, obj=subscription)
    return {
        "service": form.service.data or "",
        "start_date": form.start_date.data.strftime(form.start_date.format[0]) if form.start_date.data else "",
        "category": _required_selection(form.category.data, Category, "category").value,
        "active": "true" if _required_selection(form.active.data, bool, "active") else "false",
        "billing_period": _required_selection(form.billing_period.data, BillingPeriod, "billing_period").value,
        "billing_interval": str(form.billing_interval.data) if form.billing_interval.data is not None else "",
        "billing_date_offset": str(form.billing_date_offset.data) if form.billing_date_offset.data is not None else "",
        "payment_method": _required_selection(form.payment_method.data, PaymentMethod, "payment_method").value,
        "cost": f"{form.cost.data:.2f}" if form.cost.data is not None else "",
        "url": form.url.data or "",
        "image_url": form.image_url.data or "",
    }


def _required_selection[T](value: object, selection_type: type[T], name: str) -> T:
    if not isinstance(value, selection_type):
        raise TypeError(f"Missing required editor selection: {name}")
    return value
