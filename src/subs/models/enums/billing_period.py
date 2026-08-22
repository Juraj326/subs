from enum import Enum as PyEnum

from sqlalchemy.dialects.postgresql import ENUM as PgEnum


class BillingPeriod(str, PyEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


billing_period_enum = PgEnum(
    BillingPeriod,
    name="billing_period",
    values_callable=lambda enum_class: [val.value for val in enum_class],
)
