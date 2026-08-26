"""harden subscription constraints

Revision ID: 8c0a4d7e2f91
Revises: 5fd5fc3d1d38
Create Date: 2026-08-26 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c0a4d7e2f91"
down_revision: str | None = "5fd5fc3d1d38"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column(
        "subscriptions",
        "start_date",
        existing_type=sa.Date(),
        server_default=None,
        existing_nullable=False,
    )
    op.create_check_constraint(
        "billing_date_offset_is_nonnegative",
        "subscriptions",
        "billing_date_offset >= 0",
    )
    op.create_check_constraint(
        "cancelled_end_date_is_not_before_start_date",
        "subscriptions",
        "active OR end_date >= start_date",
    )


def downgrade() -> None:
    op.drop_constraint(
        "cancelled_end_date_is_not_before_start_date",
        "subscriptions",
        type_="check",
    )
    op.drop_constraint(
        "billing_date_offset_is_nonnegative",
        "subscriptions",
        type_="check",
    )
    op.alter_column(
        "subscriptions",
        "start_date",
        existing_type=sa.Date(),
        server_default=sa.text("CURRENT_DATE"),
        existing_nullable=False,
    )
