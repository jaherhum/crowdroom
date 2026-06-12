"""add_unique_constraint_on_session_group_position

Revision ID: 8ed135868344
Revises: f89181446f4d
Create Date: 2026-05-08 19:30:17.753295

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ed135868344"
down_revision: Union[str, Sequence[str], None] = "f89181446f4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_session_group_position", ["session_id", "group", "position"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("queue_items", schema=None) as batch_op:
        batch_op.drop_constraint("uq_session_group_position", type_="unique")
