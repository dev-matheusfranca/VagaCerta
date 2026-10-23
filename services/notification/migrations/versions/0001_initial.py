"""initial schema

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table("processed_events", sa.Column("id", sa.Uuid(), primary_key=True))
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True)),
        sa.Column("reminded_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_bookings_pending_reminders",
        "bookings",
        ["remind_at"],
        postgresql_where=sa.text("reminded_at IS NULL AND cancelled_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("processed_events")
