"""
Environnement de migration Alembic (mode async).

L'URL de connexion est lue depuis la configuration applicative
(app.config.settings.database_url, variable DATABASE_URL) : une seule
source de vérité entre l'application et les migrations.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Importe tous les modèles pour peupler Base.metadata (l'autogénération
# et la comparaison de schéma en dépendent).
import app.models  # noqa: F401
from app.config import settings
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Les migrations gèrent le schéma : elles utilisent l'URL privilégiée si
# fournie (migration_database_url), sinon l'URL applicative (dev mono-rôle).
config.set_main_option(
    "sqlalchemy.url", settings.migration_database_url or settings.database_url
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Migrations en mode offline : génère le SQL sans connexion."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crée un engine async et exécute les migrations via run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Migrations en mode online.

    asyncio.run exige l'absence de boucle d'événements dans le thread
    courant : l'appel depuis le lifespan FastAPI passe par
    asyncio.to_thread (cf. app/main.py).
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
