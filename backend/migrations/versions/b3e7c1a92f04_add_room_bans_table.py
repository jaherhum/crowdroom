"""add room_bans table

Revision ID: b3e7c1a92f04
Revises: 8a2f1c9b4d12
Create Date: 2026-06-12 18:42:07.114503

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e7c1a92f04"
down_revision: Union[str, Sequence[str], None] = "8a2f1c9b4d12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "room_bans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_room_ban"),
    )
    op.create_index(
        op.f("ix_room_bans_room_id"), "room_bans", ["room_id"], unique=False
    )
    op.create_index(
        op.f("ix_room_bans_user_id"), "room_bans", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_room_bans_user_id"), table_name="room_bans")
    op.drop_index(op.f("ix_room_bans_room_id"), table_name="room_bans")
    op.drop_table("room_bans")
