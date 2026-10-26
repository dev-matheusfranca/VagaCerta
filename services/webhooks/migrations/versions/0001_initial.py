"""subscriptions and deliveries

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
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("events", JSONB(), nullable=False),
        sa.Column("secret", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "subscription_id",
            sa.Uuid(),
            sa.ForeignKey("subscriptions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_status_code", sa.Integer()),
        sa.Column("last_error", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subscription_id", "event_id"),
    )


def downgrade() -> None:
    op.drop_table("deliveries")
    op.drop_table("subscriptions")
