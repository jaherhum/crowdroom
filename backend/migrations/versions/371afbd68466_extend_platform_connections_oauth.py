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

    with op.batch_alter_table("platform_connections", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "connection_type",
                sa.Enum(
                    "CLIENT_CREDENTIALS",
                    "AUTHORIZATION_CODE",
                    name="connectiontype",
                    create_type=False,
                ),
                server_default="CLIENT_CREDENTIALS",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "access_token_encrypted",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "refresh_token_encrypted",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("token_expires_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("scopes", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.alter_column(
            "credentials_encrypted",
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("platform_connections", schema=None) as batch_op:
        batch_op.alter_column(
            "credentials_encrypted",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.drop_column("scopes")
        batch_op.drop_column("token_expires_at")
        batch_op.drop_column("refresh_token_encrypted")
        batch_op.drop_column("access_token_encrypted")
        batch_op.drop_column("connection_type")

    sa.Enum(name="connectiontype").drop(op.get_bind(), checkfirst=True)
