"""add_room_code_to_rooms

Revision ID: ccfb5828f7e5
Revises: a231a99ac728
Create Date: 2026-05-24 18:50:49.201617

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

from backend.core.room_code import generate_room_code

# revision identifiers, used by Alembic.
revision: str = "ccfb5828f7e5"
down_revision: Union[str, Sequence[str], None] = "a231a99ac728"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Phase 1: Add column as nullable
    op.add_column(
        "rooms",
        sa.Column(
            "room_code", sqlmodel.sql.sqltypes.AutoString(length=6), nullable=True
        ),
    )

    # Phase 2: Backfill existing rows with unique codes
    connection = op.get_bind()
    rooms = connection.execute(sa.text("SELECT id FROM rooms WHERE room_code IS NULL"))
    for row in rooms:
        while True:
            code = generate_room_code()
            conflict = connection.execute(
                sa.text("SELECT 1 FROM rooms WHERE room_code = :code"),
                {"code": code},
            ).first()
            if not conflict:
                connection.execute(
                    sa.text("UPDATE rooms SET room_code = :code WHERE id = :id"),
                    {"code": code, "id": row.id},
                )
                break

    # Phase 3: Set NOT NULL and add unique index
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.alter_column("room_code", nullable=False)
        batch_op.create_index(
            batch_op.f("ix_rooms_room_code"), ["room_code"], unique=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_rooms_room_code"))
        batch_op.drop_column("room_code")
