"""shrink_streaming_platforms_enum_to_spotify

Revision ID: 5d065dfc5bca
Revises: b3e7c1a92f04
Create Date: 2026-06-12 11:01:55.592733

"""
from typing import Sequence, Union

from alembic import op

revision: str = "5d065dfc5bca"
down_revision: Union[str, Sequence[str], None] = "b3e7c1a92f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ENUM_COLUMNS = (
    ("sessions", "current_platform"),
    ("songs", "platform"),
    ("platform_connections", "platform"),
)


def upgrade() -> None:
    """Drop TIDAL from streamingplatforms enum.

    Postgres has no DROP VALUE, so rename old type, create new one,
    cast each column, then drop old. SQLite stores enums as strings
    so no DDL is needed.
    """
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE streamingplatforms RENAME TO streamingplatforms_old")
    op.execute("CREATE TYPE streamingplatforms AS ENUM ('SPOTIFY')")
    for table, column in _ENUM_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE streamingplatforms USING {column}::text::streamingplatforms"
        )
    op.execute("DROP TYPE streamingplatforms_old")


def downgrade() -> None:
    """Re-add TIDAL to streamingplatforms enum."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("ALTER TYPE streamingplatforms RENAME TO streamingplatforms_old")
    op.execute("CREATE TYPE streamingplatforms AS ENUM ('SPOTIFY', 'TIDAL')")
    for table, column in _ENUM_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE streamingplatforms USING {column}::text::streamingplatforms"
        )
    op.execute("DROP TYPE streamingplatforms_old")
