import re
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    URLField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from subs.models.enums.billing_period import BillingPeriod
from subs.models.enums.category import Category
from subs.models.enums.payment_method import PaymentMethod
from subs.services.subscription import local_today

_CENT = Decimal("0.01")
_MAX_COST = Decimal("99999999.99")


def _strip(value: str | None) -> str:
    return value.strip() if value is not None else ""


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _coerce_active(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError


def _default_start_date() -> date:
    return local_today(current_app.config["TIMEZONE"])


def _validate_currency_precision(_form: FlaskForm, field: DecimalField) -> None:
    amount = field.data
    if amount is None:
        return

    try:
        normalized_amount = amount.quantize(_CENT)
    except InvalidOperation as error:
        raise ValidationError("Cost must be a valid decimal amount.") from error

    if amount != normalized_amount:
        raise ValidationError("Cost must have no more than two decimal places.")


class SubscriptionForm(FlaskForm):
    service = StringField(
        "Service",
        filters=[_strip],
        validators=[
            DataRequired(message="Service name is required."),
            Length(max=32, message="Service name must be at most 32 characters."),
        ],
    )
    start_date = DateField(
        "Original charge date",
        default=_default_start_date,
        validators=[InputRequired(message="Original charge date is required.")],
    )
    category = SelectField(
        "Category",
        choices=[category.value for category in Category],
        coerce=Category,
        default=Category.ENTERTAINMENT,
        validators=[InputRequired(message="Category is required.")],
    )
    billing_period = SelectField(
        "Billing period",
        choices=[period.value for period in BillingPeriod],
        coerce=BillingPeriod,
        default=BillingPeriod.MONTH,
        validators=[InputRequired(message="Billing period is required.")],
    )
    billing_interval = IntegerField(
        "Billing interval",
        default=1,
        validators=[
            InputRequired(message="Billing interval is required."),
            NumberRange(min=1, message="Billing interval must be at least 1."),
        ],
    )
    billing_date_offset = IntegerField(
        "Billing date offset",
        default=0,
        validators=[
            InputRequired(message="Billing date offset is required."),
            NumberRange(
                min=0,
                message="Billing date offset must be zero or greater.",
            ),
        ],
    )
    payment_method = SelectField(
        "Payment method",
        choices=[method.value for method in PaymentMethod],
        coerce=PaymentMethod,
        default=PaymentMethod.MBANK_MASTERCARD,
        validators=[InputRequired(message="Payment method is required.")],
    )
    cost = DecimalField(
        "Cost",
        places=2,
        render_kw={"step": "0.01"},
        validators=[
            InputRequired(message="Cost is required."),
            NumberRange(
                min=Decimal(0),
                max=_MAX_COST,
                message="Cost must be between 0 and 99,999,999.99.",
            ),
            _validate_currency_precision,
        ],
    )
    url = URLField(
        "Service URL",
        filters=[_strip_optional],
        validators=[
            Optional(),
            URL(require_tld=False, message="URL must be valid."),
            Regexp(
                r"^https?://\S+$",
                flags=re.IGNORECASE,
                message="URL must use HTTP or HTTPS.",
            ),
        ],
    )
    submit = SubmitField("Save subscription")


class UpdateSubscriptionForm(SubscriptionForm):
    active = SelectField(
        "Status",
        choices=[("true", "Active"), ("false", "Cancelled")],
        coerce=_coerce_active,
        validators=[InputRequired(message="Status is required.")],
    )
    submit = SubmitField("Save changes")
