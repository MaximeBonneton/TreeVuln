"""
Main entry point for the TreeVuln API.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import api_router
from app.config import settings
from app.crypto import derive_key_from_admin_key, set_encryption_key
from app.database import async_session_maker, engine
from app.models import Asset, IngestEndpoint, IngestLog, Tree, TreeVersion, Webhook, WebhookLog  # noqa: F401
from app.models.user import EncryptionKey

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    # Startup
    # Note: In production, use Alembic for migrations
    from app.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize encryption key from DB (singleton id=1)
    async with async_session_maker() as session:
        result = await session.execute(select(EncryptionKey).where(EncryptionKey.id == 1))
        enc_key = result.scalar_one_or_none()

        if enc_key:
            set_encryption_key(enc_key.key_value)
        else:
            legacy_key = os.environ.get("ADMIN_API_KEY", "")
            if legacy_key:
                key_value = derive_key_from_admin_key(legacy_key)
                logger.info("Migration: ADMIN_API_KEY detected, deriving encryption key. "
                            "You can remove ADMIN_API_KEY from .env.")
            else:
                key_value = Fernet.generate_key().decode()
                logger.info("New encryption key generated.")

            enc_key_row = EncryptionKey(id=1, key_value=key_value)
            session.add(enc_key_row)
            await session.commit()
            set_encryption_key(key_value)

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
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """API root."""
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
