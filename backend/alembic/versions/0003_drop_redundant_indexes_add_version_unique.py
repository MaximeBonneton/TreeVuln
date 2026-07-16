"""drop redundant indexes and enforce version uniqueness

WS6 (nettoyage) :
- idx_assets_tree_asset_id est redondant avec l'index de la contrainte
  unique assets_tree_asset_unique (mêmes colonnes tree_id, asset_id) ;
- idx_webhooks_tree_id (présent uniquement dans les bases legacy créées
  par init_db.sql) est couvert par le préfixe gauche de l'index composite
  idx_webhooks_tree_active(tree_id, is_active) ;
- unicité (tree_id, version_number) sur tree_versions : empêche deux
  versions du même arbre de partager un numéro (version_number = max+1,
  non atomique).

Toutes les opérations sont idempotentes (IF EXISTS / IF NOT EXISTS) pour
rester sûres aussi bien sur une base Alembic pure que sur une base legacy
fraîchement créée par init_db.sql puis stampée à 0001.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_assets_tree_asset_id")
    op.execute("DROP INDEX IF EXISTS idx_webhooks_tree_id")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tree_versions_tree_version "
        "ON tree_versions (tree_id, version_number)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_tree_versions_tree_version")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_webhooks_tree_id ON webhooks (tree_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assets_tree_asset_id "
        "ON assets (tree_id, asset_id)"
    )
