"""add subscription image URL

Revision ID: c41e7b9a2d6f
Revises: b0698f26ad9b
Create Date: 2026-08-30 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c41e7b9a2d6f"
down_revision: str | None = "b0698f26ad9b"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("image_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "image_url")
