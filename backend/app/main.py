"""
Main entry point for the TreeVuln API.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import api_router
from app.config import settings
from app.crypto import set_encryption_key
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

            logger.warning(
                "⚠ SECRET_KEY is not set — encryption key is stored in the database. "
                "This is fine for evaluation, but for production set SECRET_KEY in your .env file. "
                "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

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
