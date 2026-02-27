"""
Dépendances communes pour les routes API.
"""

import hmac
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.asset_service import AssetService
from app.services.ingest_service import IngestService
from app.services.tree_service import TreeService
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

# --- Authentication ---

_admin_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def require_admin(
    request: Request,
    authorization: str | None = Security(_admin_key_header),
) -> None:
    """Vérifie le Bearer token OU le cookie de session pour les endpoints de gestion.

    Ordre de vérification :
    1. Header Authorization (Bearer token) — pour API / curl / scripts
    2. Cookie de session signé HMAC — pour le frontend (pas de clé dans le JS)

    Si ADMIN_API_KEY n'est pas configurée, l'authentification est désactivée
    (mode debug uniquement). En production, une clé doit être définie.
    """
    if not settings.admin_api_key:
        if settings.debug:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration serveur incomplète : ADMIN_API_KEY non définie",
        )

    # 1. Vérification Bearer token (API)
    if authorization:
        token = authorization
        if token.lower().startswith("bearer "):
            token = token[7:]
        if hmac.compare_digest(token, settings.admin_api_key):
            return

    # 2. Vérification cookie de session (frontend)
    from app.api.routes.auth import SESSION_COOKIE_NAME, validate_session_token

    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and validate_session_token(session_token, settings.admin_api_key):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (Bearer token ou session cookie)",
    )


RequireAdmin = Depends(require_admin)

# Type alias pour les dépendances
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_tree_service(db: DBSession) -> AsyncGenerator[TreeService, None]:
    """Fournit une instance du service Tree."""
    yield TreeService(db)


async def get_asset_service(db: DBSession) -> AsyncGenerator[AssetService, None]:
    """Fournit une instance du service Asset."""
    yield AssetService(db)


async def get_webhook_service(db: DBSession) -> AsyncGenerator[WebhookService, None]:
    """Fournit une instance du service Webhook."""
    yield WebhookService(db)


async def get_ingest_service(db: DBSession) -> AsyncGenerator[IngestService, None]:
    """Fournit une instance du service Ingest."""
    yield IngestService(db)


TreeServiceDep = Annotated[TreeService, Depends(get_tree_service)]
AssetServiceDep = Annotated[AssetService, Depends(get_asset_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]


# --- Upload helpers ---

from app.filename_validation import sanitize_filename  # noqa: F401 — re-export


async def read_upload_with_limit(file: "UploadFile") -> bytes:
    """Lit un fichier uploadé avec vérification de la taille.

    Raises:
        HTTPException 413 si le fichier dépasse max_upload_size.
    """
    from fastapi import UploadFile as _UploadFile  # noqa: F811

    # Vérifie la taille déclarée dans le header Content-Length si disponible
    if hasattr(file, "size") and file.size and file.size > settings.max_upload_size:
        max_mb = settings.max_upload_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Taille maximum : {max_mb} Mo",
        )

    # Lecture par chunks pour éviter de charger un fichier géant d'un coup
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1 MB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Fichier trop volumineux. Taille maximum : {max_mb} Mo",
            )
        chunks.append(chunk)

    return b"".join(chunks)
