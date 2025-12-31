"""add_cascade_delete_to_group_members

Revision ID: 708235923b8a
Revises: 2b873686b7c2
Create Date: 2025-12-31 14:00:22.424319

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '708235923b8a'
down_revision: Union[str, Sequence[str], None] = '2b873686b7c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CASCADE delete to group_members foreign keys."""
    # Drop existing foreign keys
    op.drop_constraint('group_members_group_id_fkey', 'group_members', type_='foreignkey')
    op.drop_constraint('group_members_user_id_fkey', 'group_members', type_='foreignkey')

    # Recreate with ON DELETE CASCADE
    op.create_foreign_key(
        'group_members_group_id_fkey',
        'group_members', 'groups',
        ['group_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'group_members_user_id_fkey',
        'group_members', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove CASCADE delete from group_members foreign keys."""
    # Drop CASCADE foreign keys
    op.drop_constraint('group_members_group_id_fkey', 'group_members', type_='foreignkey')
    op.drop_constraint('group_members_user_id_fkey', 'group_members', type_='foreignkey')

    # Recreate without CASCADE
    op.create_foreign_key(
        'group_members_group_id_fkey',
        'group_members', 'groups',
        ['group_id'], ['id']
    )
    op.create_foreign_key(
        'group_members_user_id_fkey',
        'group_members', 'users',
        ['user_id'], ['id']
    )
