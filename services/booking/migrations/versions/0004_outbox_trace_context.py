"""trace context stored with outbox events

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("trace_context", JSONB(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("outbox", "trace_context")
