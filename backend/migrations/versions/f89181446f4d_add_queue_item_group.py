"""add_queue_item_group

Revision ID: f89181446f4d
Revises: cbd98fc7226e
Create Date: 2026-05-04 21:29:49.531351

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f89181446f4d"
down_revision: Union[str, Sequence[str], None] = "cbd98fc7226e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "group", sa.String(length=20), nullable=False, server_default="playlist"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.drop_column("group")
