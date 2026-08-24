from enum import Enum as PyEnum

from sqlalchemy.dialects.postgresql import ENUM as PgEnum


class Category(str, PyEnum):
    ESSENTIAL = "Essential"
    ENTERTAINMENT = "Entertainment"
    SCHOOL = "School"


category_enum = PgEnum(
    Category,
    name="category",
    values_callable=lambda enum_class: [val.value for val in enum_class],
)
