"""
Main entry point for the TreeVuln API.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api import api_router
from app.config import settings
from app.crypto import set_encryption_key
from app.database import async_session_maker, engine
from app.models import Asset, IngestEndpoint, IngestLog, Tree, TreeVersion, Webhook, WebhookLog  # noqa: F401
from app.models.user import EncryptionKey

logger = logging.getLogger(__name__)


def _log_db_encryption_key_notice() -> None:
    """
    Signale l'absence de SECRET_KEY (S-18) : la clé de chiffrement vit
    alors en base, à côté des données qu'elle protège.

    En production (DEBUG=false), c'est une erreur de configuration : un
    dump de la base suffit à déchiffrer tous les secrets stockés (secrets
    webhooks, clés API d'ingestion). Le démarrage n'est pas bloqué
    (décision d154bfc : ne pas casser les déploiements d'évaluation),
    mais l'erreur doit être explicite dans les logs.
    """
    generate_hint = (
        "Generate one with: python3 -c "
        '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )
    if settings.debug:
        logger.warning(
            "⚠ SECRET_KEY is not set — encryption key is stored in the database. "
            "This is acceptable for development only. %s",
            generate_hint,
        )
    else:
        logger.error(
            "✖ SECRET_KEY is not set while DEBUG=false: the encryption key is "
            "stored in the database NEXT TO the data it protects — a database "
            "dump exposes every webhook secret and ingest API key. Set "
            "SECRET_KEY in your .env file for production. %s",
            generate_hint,
        )


async def run_migrations() -> None:
    """
    Applique les migrations Alembic au démarrage (B-14, remplace create_all).

    Cas particulier des bases legacy (créées par init_db.sql ou par
    l'ancien create_all, sans historique Alembic) : le schéma existe déjà,
    donc `upgrade head` échouerait sur la baseline (tables déjà présentes).
    On détecte ce cas (table trees présente, alembic_version absente) et on
    stampe la baseline 0001 avant d'appliquer les migrations suivantes.

    Les commandes Alembic sont synchrones (env.py utilise asyncio.run) :
    elles doivent s'exécuter hors de la boucle d'événements, d'où
    asyncio.to_thread.
    """
    from alembic import command
    from alembic.config import Config

    async with engine.connect() as conn:
        has_alembic = (
            await conn.execute(text("SELECT to_regclass('public.alembic_version')"))
        ).scalar() is not None
        has_trees = (
            await conn.execute(text("SELECT to_regclass('public.trees')"))
        ).scalar() is not None

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    if has_trees and not has_alembic:
        logger.info(
            "Base existante sans historique Alembic détectée : stamp de la baseline 0001."
        )
        await asyncio.to_thread(command.stamp, cfg, "0001")
    await asyncio.to_thread(command.upgrade, cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    # Startup
    # B-14 : le schéma est géré par Alembic (baseline + migrations).
    await run_migrations()

    # Initialize encryption key
    # Priority: SECRET_KEY env var > existing DB key > auto-generate (with warning)
    if settings.secret_key:
        set_encryption_key(settings.secret_key)
        logger.info("Encryption key loaded from SECRET_KEY environment variable.")
    else:
        async with async_session_maker() as session:
            result = await session.execute(select(EncryptionKey).where(EncryptionKey.id == 1))
            enc_key = result.scalar_one_or_none()

            if enc_key:
                set_encryption_key(enc_key.key_value)
            else:
                key_value = Fernet.generate_key().decode()
                enc_key_row = EncryptionKey(id=1, key_value=key_value)
                session.add(enc_key_row)
                await session.commit()
                set_encryption_key(key_value)

            _log_db_encryption_key_notice()

    # Enterprise initialization (license detection + modules)
    from app.enterprise import init_enterprise
    init_enterprise()

    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="""
    API for vulnerability prioritization based on SSVC decision trees.

    ## Features

    - **Tree**: Decision tree management (CRUD + versioning)
    - **Evaluate**: Vulnerability evaluation (single and batch)
    - **Assets**: Asset reference management for contextualization
    """,
    version="0.1.0",
    lifespan=lifespan,
    # Disable Swagger/OpenAPI in production
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# API Routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Health endpoint for Docker/K8s healthchecks."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """API root."""
    return {"name": settings.app_name}
