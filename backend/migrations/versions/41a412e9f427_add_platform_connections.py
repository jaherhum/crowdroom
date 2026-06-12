"""add_platform_connections

Revision ID: 41a412e9f427
Revises: 8ed135868344
Create Date: 2026-05-19 19:17:28.656476

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "41a412e9f427"
down_revision: Union[str, Sequence[str], None] = "8ed135868344"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "platform_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("SPOTIFY", "TIDAL", name="streamingplatforms"),
            nullable=False,
        ),
        sa.Column(
            "credentials_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "platform", name="uq_user_platform"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("platform_connections")
