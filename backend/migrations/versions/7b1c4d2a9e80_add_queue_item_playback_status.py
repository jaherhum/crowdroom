"""add_queue_item_playback_status

Revision ID: 7b1c4d2a9e80
Revises: 5d065dfc5bca
Create Date: 2026-06-12 13:55:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b1c4d2a9e80"
down_revision: Union[str, Sequence[str], None] = "5d065dfc5bca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ITEMSTATUS_VALUES = (
    "QUEUED",
    "NOW_PLAYING",
    "PLAYING",
    "PAUSED",
    "STOPPED",
    "BUFFERING",
    "ERROR",
    "FINISHED",
)


def upgrade() -> None:
    """Add queue_items.playback_status using existing itemstatus enum."""
    bind = op.get_bind()
    sa.Enum(*_ITEMSTATUS_VALUES, name="itemstatus").create(bind, checkfirst=True)

    enum_type = sa.Enum(*_ITEMSTATUS_VALUES, name="itemstatus", create_type=False)
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "playback_status",
                enum_type,
                nullable=False,
                server_default="QUEUED",
            )
        )


def downgrade() -> None:
    """Drop queue_items.playback_status."""
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.drop_column("playback_status")
