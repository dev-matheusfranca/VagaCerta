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
    op.create_table(
        "entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("professional_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("customer_name", sa.String(120), nullable=False),
        sa.Column("customer_email", sa.String(254), nullable=False),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_entries_one_per_day",
        "entries",
        ["customer_email", "professional_id", "service_id", "day"],
        unique=True,
        postgresql_where=sa.text("status IN ('waiting', 'offered')"),
    )
    op.create_index("ix_entries_queue", "entries", ["professional_id", "status", "created_at"])
    op.create_table(
        "offers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entry_id", sa.Uuid(), sa.ForeignKey("entries.id"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index(
        "ix_offers_pending",
        "offers",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_outbox_pending", "outbox", ["id"], postgresql_where=sa.text("published_at IS NULL")
    )
    op.create_table("processed_events", sa.Column("id", sa.Uuid(), primary_key=True))


def downgrade() -> None:
    for table in ("processed_events", "outbox", "offers", "entries"):
        op.drop_table(table)
