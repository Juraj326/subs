"""Rename School to Professional without rewriting subscription records."""

from alembic import op

revision = "e83b9a025f14"
down_revision = "d72a8f914e03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE category RENAME VALUE 'School' TO 'Professional'")


def downgrade() -> None:
    op.execute("ALTER TYPE category RENAME VALUE 'Professional' TO 'School'")
