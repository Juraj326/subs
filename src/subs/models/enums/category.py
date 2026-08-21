from enum import Enum as PyEnum

from sqlalchemy.dialects.postgresql import ENUM as PgEnum


class Category(str, PyEnum):
    ESSENTIAL = "essential"
    ENTERTAINMENT = "entertainment"
    SCHOOL = "school"


category_enum = PgEnum(
    Category,
    name="category",
    create_type=False,
    values_callable=lambda enum_class: [val.value for val in enum_class],
)
