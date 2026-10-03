"""add messages (chat_id, id) index

Revision ID: 5c1f3a7d9e20
Revises: ecff190048d9
Create Date: 2026-09-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5c1f3a7d9e20'
down_revision: Union[str, Sequence[str], None] = 'ecff190048d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_messages_chat_id_id', 'messages', ['chat_id', 'id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_messages_chat_id_id', table_name='messages')
