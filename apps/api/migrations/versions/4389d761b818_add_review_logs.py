"""add review logs

Revision ID: 4389d761b818
Revises: 23c4002b5a2a
Create Date: 2026-11-08 20:09:51.391631

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4389d761b818"
down_revision: str | Sequence[str] | None = "23c4002b5a2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    _ = op.create_table(
        "review_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fsrs_state", sa.SmallInteger(), nullable=False),
        sa.Column("fsrs_step", sa.SmallInteger(), nullable=True),
        sa.Column("stability", sa.Float(), nullable=True),
        sa.Column("difficulty", sa.Float(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["card_id"], ["cards.id"], ondelete="CASCADE", name="review_logs_card_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="CASCADE", name="review_logs_owner_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_logs"),
    )
    op.create_index(op.f("ix_review_logs_card_id"), "review_logs", ["card_id"], unique=False)
    op.create_index(
        "ix_review_logs_owner_reviewed", "review_logs", ["owner_id", "reviewed_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_review_logs_owner_reviewed", table_name="review_logs")
    op.drop_index(op.f("ix_review_logs_card_id"), table_name="review_logs")
    op.drop_table("review_logs")
