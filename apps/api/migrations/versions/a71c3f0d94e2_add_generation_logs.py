"""add generation logs

Revision ID: a71c3f0d94e2
Revises: 4389d761b818
Create Date: 2026-11-12 10:24:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a71c3f0d94e2"
down_revision: str | Sequence[str] | None = "4389d761b818"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "generation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="CASCADE", name="generation_logs_owner_id_fkey"
        ),
        # SET NULL, not CASCADE: deleting a deck must not erase the quota history.
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="SET NULL",
            name="generation_logs_source_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generation_logs"),
    )
    op.create_index(
        op.f("ix_generation_logs_source_id"), "generation_logs", ["source_id"], unique=False
    )
    op.create_index(
        "ix_generation_logs_owner_created",
        "generation_logs",
        ["owner_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_generation_logs_owner_created", table_name="generation_logs")
    op.drop_index(op.f("ix_generation_logs_source_id"), table_name="generation_logs")
    op.drop_table("generation_logs")
