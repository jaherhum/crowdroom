"""extend_platform_connections_oauth

Revision ID: 371afbd68466
Revises: 201770290204
Create Date: 2026-05-30 02:27:47.661581

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "371afbd68466"
down_revision: Union[str, Sequence[str], None] = "201770290204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connectiontype_enum = sa.Enum(
        "CLIENT_CREDENTIALS", "AUTHORIZATION_CODE", name="connectiontype"
    )
    connectiontype_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "platform_connections",
        sa.Column(
            "connection_type",
            connectiontype_enum,
            server_default="CLIENT_CREDENTIALS",
            nullable=False,
        ),
    )
    op.add_column(
        "platform_connections",
        sa.Column(
            "access_token_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.add_column(
        "platform_connections",
        sa.Column(
            "refresh_token_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.add_column(
        "platform_connections",
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "platform_connections",
        sa.Column("scopes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.alter_column(
        "platform_connections",
        "credentials_encrypted",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "platform_connections",
        "credentials_encrypted",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("platform_connections", "scopes")
    op.drop_column("platform_connections", "token_expires_at")
    op.drop_column("platform_connections", "refresh_token_encrypted")
    op.drop_column("platform_connections", "access_token_encrypted")
    op.drop_column("platform_connections", "connection_type")

    sa.Enum(name="connectiontype").drop(op.get_bind(), checkfirst=True)
