"""initial schema

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None

COUNTERS = (
    "bookings",
    "cancellations",
    "revenue_cents",
    "offers",
    "offers_claimed",
    "offers_expired",
    "recovered_revenue_cents",
)


def upgrade() -> None:
    op.create_table(
        "daily_stats",
        sa.Column("business_id", sa.Uuid(), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        *(sa.Column(name, sa.Integer(), nullable=False, server_default="0") for name in COUNTERS),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
    )
    op.create_table("processed_events", sa.Column("id", sa.Uuid(), primary_key=True))


def downgrade() -> None:
    for table in ("processed_events", "bookings", "daily_stats"):
        op.drop_table(table)
