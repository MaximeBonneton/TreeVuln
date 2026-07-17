"""Ajoute les tables sboms et sbom_components (Phase 2 : ingestion SBOM).

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sboms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("spec_version", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("component_count", sa.Integer(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_table(
        "sbom_components",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sbom_id", sa.Integer(), nullable=False),
        sa.Column("purl", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("version", sa.String(length=255), nullable=True),
        sa.Column("component_type", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["sbom_id"], ["sboms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sbom_components_purl", "sbom_components", ["sbom_id", "purl"])
    op.create_index("idx_sbom_components_name", "sbom_components", ["sbom_id", "name"])


def downgrade() -> None:
    op.drop_table("sbom_components")
    op.drop_table("sboms")
