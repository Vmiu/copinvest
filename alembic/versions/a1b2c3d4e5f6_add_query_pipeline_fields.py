"""add query pipeline fields

Revision ID: a1b2c3d4e5f6
Revises: 23b31f0ac9b4
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '23b31f0ac9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('audit_log', sa.Column('rewritten_query', sa.Text(), nullable=True))
    op.add_column('audit_log', sa.Column('chunks_passed_rerank', sa.Integer(), nullable=True))
    op.add_column('audit_log', sa.Column('not_found', sa.Boolean(), nullable=True))
    op.add_column('sessions', sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sessions', 'last_activity')
    op.drop_column('audit_log', 'not_found')
    op.drop_column('audit_log', 'chunks_passed_rerank')
    op.drop_column('audit_log', 'rewritten_query')
