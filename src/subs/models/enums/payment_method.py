from enum import Enum as PyEnum

from sqlalchemy.dialects.postgresql import ENUM as PgEnum


class PaymentMethod(str, PyEnum):
    MBANK_MASTERCARD = "mBank MasterCard"
    MBANK_VISA = "mBank VISA"


payment_method_enum = PgEnum(
    PaymentMethod,
    name="payment_method",
    values_callable=lambda enum_class: [val.value for val in enum_class],
)
