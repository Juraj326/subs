from datetime import date
from decimal import Decimal

from sqlalchemy import (
    VARCHAR,
    Boolean,
    CheckConstraint,
    Date,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .enums.billing_period import BillingPeriod, billing_period_enum
from .enums.category import Category, category_enum
from .enums.payment_method import PaymentMethod, payment_method_enum


class Subscription(db.Model):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("billing_interval > 0", name="billing_interval_is_positive"),
        CheckConstraint("cost >= 0", name="cost_is_positive"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        primary_key=True,
    )

    service: Mapped[str] = mapped_column(
        VARCHAR(32),
        unique=True,
        nullable=False,
    )

    category: Mapped[Category] = mapped_column(
        category_enum,
        nullable=False,
        default=Category.ENTERTAINMENT,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )

    billing_period: Mapped[BillingPeriod] = mapped_column(
        billing_period_enum,
        nullable=False,
        default=BillingPeriod.MONTH,
    )

    billing_interval: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        payment_method_enum,
        nullable=False,
        default=PaymentMethod.MBANK_MASTERCARD,
    )

    cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
