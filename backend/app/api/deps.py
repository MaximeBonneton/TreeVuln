"""
Dépendances communes pour les routes API.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.asset_service import AssetService
from app.services.ingest_service import IngestService
from app.services.tree_service import TreeService
from app.services.user_service import UserService
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

# --- Authentication ---

SESSION_COOKIE_NAME = "treevuln_session"


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Vérifie qu'une session valide existe et injecte l'utilisateur."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    service = UserService(db)
    user = await service.get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Session restreinte (must_change_pwd) : seuls certains endpoints sont autorisés
    allowed_paths = ("/api/v1/auth/change-password", "/api/v1/auth/logout")
    if user.must_change_pwd and request.url.path not in allowed_paths:
        raise HTTPException(status_code=403, detail="Password change required")

    request.state.user = user
    request.state.session_token = token
    return user


RequireAuth = Annotated[User, Depends(require_auth)]


def require_role(role: str):
    """Fabrique de dépendance qui vérifie le rôle de l'utilisateur."""
    async def _check(user: RequireAuth):
        if user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return Depends(_check)


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
from app.config import settings  # noqa: E402


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
