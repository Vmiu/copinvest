"""add document metadata fields to document_registry

Revision ID: c7d3e4f5a6b8
Revises: b9c4d2e1f3a7
Create Date: 2026-05-11
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "c7d3e4f5a6b8"
down_revision: Union[str, Sequence[str], None] = "b9c4d2e1f3a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("document_registry", sa.Column("document_type", sa.String(50), nullable=True))
    op.add_column("document_registry", sa.Column("language", sa.String(10), nullable=True))
    op.add_column("document_registry", sa.Column("jurisdiction", sa.String(50), nullable=True))
    op.add_column("document_registry", sa.Column("product_codes", sa.Text, nullable=True))
    op.add_column("document_registry", sa.Column("parent_doc_title", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("document_registry", "parent_doc_title")
    op.drop_column("document_registry", "product_codes")
    op.drop_column("document_registry", "jurisdiction")
    op.drop_column("document_registry", "language")
    op.drop_column("document_registry", "document_type")
