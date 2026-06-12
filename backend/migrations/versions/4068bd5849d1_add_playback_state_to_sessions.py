"""add_playback_state_to_sessions

Revision ID: 4068bd5849d1
Revises: 371afbd68466
Create Date: 2026-05-30 13:07:29.748719

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4068bd5849d1"
down_revision: Union[str, Sequence[str], None] = "371afbd68466"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    itemstatus_enum = sa.Enum(
        "QUEUED",
        "NOW_PLAYING",
        "PLAYING",
        "PAUSED",
        "STOPPED",
        "BUFFERING",
        "ERROR",
        "FINISHED",
        name="itemstatus",
    )
    itemstatus_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "sessions",
        sa.Column(
            "playback_status",
            sa.Enum(
                "QUEUED",
                "NOW_PLAYING",
                "PLAYING",
                "PAUSED",
                "STOPPED",
                "BUFFERING",
                "ERROR",
                "FINISHED",
                name="itemstatus",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "sessions", sa.Column("playback_position_ms", sa.Integer(), nullable=True)
    )
    op.add_column(
        "sessions", sa.Column("playback_started_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "sessions",
        sa.Column(
            "current_device_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sessions", "current_device_id")
    op.drop_column("sessions", "playback_started_at")
    op.drop_column("sessions", "playback_position_ms")
    op.drop_column("sessions", "playback_status")
    sa.Enum(name="itemstatus").drop(op.get_bind(), checkfirst=True)
