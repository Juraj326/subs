"""allow negative billing date offsets

Revision ID: b0698f26ad9b
Revises: 8c0a4d7e2f91
Create Date: 2026-08-30 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0698f26ad9b"
down_revision: str | None = "8c0a4d7e2f91"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "billing_date_offset_is_nonnegative",
        "subscriptions",
        type_="check",
    )


def downgrade() -> None:
    op.create_check_constraint(
        "billing_date_offset_is_nonnegative",
        "subscriptions",
        "billing_date_offset >= 0",
    )
