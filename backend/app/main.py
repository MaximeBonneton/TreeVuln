"""
Point d'entrée principal de l'API TreeVuln.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings
from app.database import engine
from app.models import Asset, IngestEndpoint, IngestLog, Tree, TreeVersion, Webhook, WebhookLog  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    # Startup
    if not settings.admin_api_key:
        if settings.debug:
            logger.warning(
                "ADMIN_API_KEY non configurée — les endpoints de gestion sont "
                "accessibles sans authentification (mode debug)."
            )
        else:
            raise RuntimeError(
                "ADMIN_API_KEY doit être configurée en production. "
                'Générer avec : python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
                "Définir DEBUG=true pour désactiver ce contrôle en développement."
            )
    # Note: En production, utiliser Alembic pour les migrations
    from app.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="""
    API pour la priorisation de vulnérabilités basée sur des arbres de décision SSVC.

    ## Fonctionnalités

    - **Tree**: Gestion de l'arbre de décision (CRUD + versioning)
    - **Evaluate**: Évaluation des vulnérabilités (unitaire et batch)
    - **Assets**: Gestion du référentiel d'assets pour la contextualisation
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Routes API
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Endpoint de santé pour les healthchecks Docker/K8s."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """Racine de l'API."""
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
