"""rename compliance to admin in userrole enum

Revision ID: b9c4d2e1f3a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11

WARNING: downgrade() is NOT safely reversible. Any user created as 'admin'
after this migration was applied will be relabeled 'compliance' on rollback,
regardless of whether they were originally a compliance user.
"""
from typing import Sequence, Union
from alembic import op

revision: str = "b9c4d2e1f3a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'admin'")
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'compliance'")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR")
        op.execute("DROP TYPE userrole")
        op.execute("CREATE TYPE userrole AS ENUM ('adviser', 'senior_adviser', 'admin')")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
    else:
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'compliance'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR")
        op.execute("DROP TYPE userrole")
        op.execute("CREATE TYPE userrole AS ENUM ('adviser', 'senior_adviser', 'compliance')")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
        op.execute("UPDATE users SET role = 'compliance' WHERE role = 'admin'")
    else:
        op.execute("UPDATE users SET role = 'compliance' WHERE role = 'admin'")
