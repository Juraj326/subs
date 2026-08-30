from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from flask import Flask
from werkzeug.datastructures import MultiDict

from subs.forms.subscription import SubscriptionForm, UpdateSubscriptionForm
from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod


def _valid_form_data() -> dict[str, str]:
    return {
        "service": "Netflix",
        "start_date": "2026-01-31",
        "category": Category.ENTERTAINMENT.value,
        "billing_period": BillingPeriod.MONTH.value,
        "billing_interval": "1",
        "billing_date_offset": "2",
        "payment_method": PaymentMethod.MBANK_MASTERCARD.value,
        "cost": "12.90",
        "url": "https://www.netflix.com/account",
    }


def _form(data: dict[str, str]) -> SubscriptionForm:
    return SubscriptionForm(formdata=MultiDict(data))


def test_valid_form_normalizes_and_converts_fields(app: Flask) -> None:
    data = _valid_form_data()
    data.update(
        service="  Netflix  ",
        url="  https://www.netflix.com/account  ",
    )

    form = _form(data)

    assert form.validate()
    assert form.errors == {}
    assert form.service.data == "Netflix"
    assert form.start_date.data == date(2026, 1, 31)
    assert form.category.data is Category.ENTERTAINMENT
    assert form.billing_period.data is BillingPeriod.MONTH
    assert form.billing_interval.data == 1
    assert form.billing_date_offset.data == 2
    assert form.payment_method.data is PaymentMethod.MBANK_MASTERCARD
    assert form.cost.data == Decimal("12.90")
    assert form.url.data == "https://www.netflix.com/account"


def test_zero_cost_and_offset_are_valid(app: Flask) -> None:
    data = _valid_form_data()
    data.update(cost="0", billing_date_offset="0")

    form = _form(data)

    assert form.validate()
    assert form.cost.data == Decimal(0)
    assert form.billing_date_offset.data == 0


def test_negative_billing_date_offset_is_valid(app: Flask) -> None:
    data = _valid_form_data()
    data["billing_date_offset"] = "-5"

    form = _form(data)

    assert form.validate()
    assert form.billing_date_offset.data == -5


def test_blank_optional_url_becomes_none(app: Flask) -> None:
    data = _valid_form_data()
    data["url"] = "   "

    form = _form(data)

    assert form.validate()
    assert form.url.data is None


@pytest.mark.parametrize(
    ("submitted_value", "expected_value"),
    [("true", True), ("false", False)],
)
def test_update_form_converts_status_to_boolean(
    submitted_value: str,
    expected_value: bool,
    app: Flask,
) -> None:
    data = _valid_form_data()
    data["active"] = submitted_value

    form = UpdateSubscriptionForm(formdata=MultiDict(data))

    assert form.validate()
    assert form.active.data is expected_value


def test_update_form_rejects_unknown_status(app: Flask) -> None:
    data = _valid_form_data()
    data["active"] = "paused"

    form = UpdateSubscriptionForm(formdata=MultiDict(data))

    assert not form.validate()
    assert "active" in form.errors


def test_update_form_uses_existing_subscription_status(app: Flask) -> None:
    subscription = SimpleNamespace(
        service="Netflix",
        start_date=date(2026, 1, 31),
        category=Category.ENTERTAINMENT,
        active=False,
        billing_period=BillingPeriod.MONTH,
        billing_interval=1,
        billing_date_offset=2,
        payment_method=PaymentMethod.MBANK_MASTERCARD,
        cost=Decimal("12.90"),
        url=None,
    )

    form = UpdateSubscriptionForm(obj=subscription)

    assert form.active.data is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("service", "   "),
        ("service", "x" * 33),
        ("start_date", ""),
        ("start_date", "not-a-date"),
        ("category", "Not a category"),
        ("billing_period", "decade"),
        ("billing_interval", "0"),
        ("billing_interval", "not-a-number"),
        ("billing_date_offset", "not-a-number"),
        ("payment_method", "Cash"),
        ("cost", "-0.01"),
        ("cost", "1.001"),
        ("cost", "NaN"),
        ("cost", "100000000.00"),
        ("cost", "not-a-number"),
        ("url", "ftp://example.com"),
        ("url", "https:///missing-host"),
        ("url", "https://example.com/a path"),
    ],
)
def test_invalid_field_is_rejected(field: str, value: str, app: Flask) -> None:
    data = _valid_form_data()
    data[field] = value

    form = _form(data)

    assert not form.validate()
    assert field in form.errors
