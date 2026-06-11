"""extend_invite_token_length

Revision ID: 8a2f1c9b4d12
Revises: de876a4aa743
Create Date: 2026-06-11 12:00:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a2f1c9b4d12"
down_revision: Union[str, Sequence[str], None] = "de876a4aa743"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen room_invites.token to 64 chars to fit long QR-issued tokens."""
    with op.batch_alter_table("room_invites") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sqlmodel.sql.sqltypes.AutoString(length=12),
            type_=sqlmodel.sql.sqltypes.AutoString(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Narrow room_invites.token back to 12 chars."""
    with op.batch_alter_table("room_invites") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sqlmodel.sql.sqltypes.AutoString(length=64),
            type_=sqlmodel.sql.sqltypes.AutoString(length=12),
            existing_nullable=False,
        )
