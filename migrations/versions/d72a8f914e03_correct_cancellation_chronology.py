"""Account for signed access offsets in cancellation chronology.

Downgrading can fail for valid negative-offset expirations before start_date.
No historical dates are rewritten.
"""

from alembic import op

revision = "d72a8f914e03"
down_revision = "c41e7b9a2d6f"
branch_labels = None
depends_on = None


def _replace(expression: str) -> None:
    name = "cancelled_end_date_is_not_before_start_date"
    op.drop_constraint(name, "subscriptions", type_="check")
    op.create_check_constraint(name, "subscriptions", expression)


def upgrade() -> None:
    _replace("active OR end_date >= start_date + billing_date_offset")


def downgrade() -> None:
    _replace("active OR end_date >= start_date")
