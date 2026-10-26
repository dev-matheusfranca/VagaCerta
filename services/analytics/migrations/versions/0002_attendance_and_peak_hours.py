"""attendance, occupancy and peak hours

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def column(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), nullable=False, server_default="0")


def upgrade() -> None:
    for name in ("completed", "no_shows", "booked_minutes"):
        op.add_column("daily_stats", column(name))
    for name in ("minutes", "weekday", "hour"):
        op.add_column("bookings", column(name))
    op.create_table(
        "hourly_stats",
        sa.Column("business_id", sa.Uuid(), primary_key=True),
        sa.Column("weekday", sa.Integer(), primary_key=True),
        sa.Column("hour", sa.Integer(), primary_key=True),
        column("bookings"),
    )


def downgrade() -> None:
    op.drop_table("hourly_stats")
    for name in ("minutes", "weekday", "hour"):
        op.drop_column("bookings", name)
    for name in ("completed", "no_shows", "booked_minutes"):
        op.drop_column("daily_stats", name)
