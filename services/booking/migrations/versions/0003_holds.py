"""temporary holds for waitlist offers

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column("bookings", sa.Column("hold_expires_at", sa.DateTime(timezone=True)))
    op.drop_constraint("bookings_no_overlap", "bookings")
    # Uma reserva temporária ocupa o horário como um agendamento confirmado.
    op.execute(
        """
        ALTER TABLE bookings ADD CONSTRAINT bookings_no_overlap
        EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
        WHERE (status IN ('confirmed', 'held'))
        """
    )


def downgrade() -> None:
    op.drop_constraint("bookings_no_overlap", "bookings")
    op.execute(
        """
        ALTER TABLE bookings ADD CONSTRAINT bookings_no_overlap
        EXCLUDE USING gist (professional_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
        WHERE (status = 'confirmed')
        """
    )
    op.drop_column("bookings", "hold_expires_at")
