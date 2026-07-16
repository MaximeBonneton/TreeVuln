"""widen encrypted secret columns to TEXT

Constats #1 et #9 de la revue de code du 2026-07-16 : webhooks.secret et
ingest_endpoints.api_key stockent des valeurs CHIFFRÉES (préfixe "enc:" +
token Fernet) dont la longueur dépasse 255 caractères dès que le plaintext
est un peu long. Les bases créées par init_db.sql (ou par l'ancien
create_all) ont ces colonnes en VARCHAR(255) -> StringDataRightTruncation
(500) à l'écriture. VARCHAR -> TEXT est un simple changement de métadonnées
sous PostgreSQL (pas de réécriture de table).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "webhooks",
        "secret",
        type_=sa.Text(),
        existing_type=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "ingest_endpoints",
        "api_key",
        type_=sa.Text(),
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "ingest_endpoints",
        "api_key",
        type_=sa.String(length=255),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "webhooks",
        "secret",
        type_=sa.String(length=255),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
