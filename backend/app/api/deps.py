"""
Common dependencies for API routes.
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
from app.services.sbom_service import SbomService
from app.services.settings_service import SettingsService
from app.services.tree_service import TreeService
from app.services.user_service import UserService
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

# --- Authentication ---


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Verify that a valid session exists and inject the user."""
    from app.config import settings as _settings
    token = request.cookies.get(_settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    service = UserService(db)
    user = await service.get_session_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    # Restricted session (must_change_pwd): only certain endpoints are allowed
    allowed_paths = ("/api/v1/auth/change-password", "/api/v1/auth/logout")
    if user.must_change_pwd and request.url.path not in allowed_paths:
        raise HTTPException(status_code=403, detail="Password change required")

    request.state.user = user
    request.state.session_token = token
    return user


RequireAuth = Annotated[User, Depends(require_auth)]


def require_role(role: str):
    """Dependency factory that verifies the user's role."""
    async def _check(user: RequireAuth):
        if user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return Depends(_check)


# Type aliases for dependencies
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_tree_service(db: DBSession) -> AsyncGenerator[TreeService, None]:
    """Provide a Tree service instance."""
    yield TreeService(db)


async def get_asset_service(db: DBSession) -> AsyncGenerator[AssetService, None]:
    """Provide an Asset service instance."""
    yield AssetService(db)


async def get_webhook_service(db: DBSession) -> AsyncGenerator[WebhookService, None]:
    """Provide a Webhook service instance."""
    yield WebhookService(db)


async def get_ingest_service(db: DBSession) -> AsyncGenerator[IngestService, None]:
    """Provide an Ingest service instance."""
    yield IngestService(db)


async def get_settings_service(db: DBSession) -> AsyncGenerator[SettingsService, None]:
    """Provide a Settings service instance."""
    yield SettingsService(db)


async def get_sbom_service(db: DBSession) -> AsyncGenerator[SbomService, None]:
    """Provide a SBOM service instance."""
    yield SbomService(db)


TreeServiceDep = Annotated[TreeService, Depends(get_tree_service)]
AssetServiceDep = Annotated[AssetService, Depends(get_asset_service)]
WebhookServiceDep = Annotated[WebhookService, Depends(get_webhook_service)]
IngestServiceDep = Annotated[IngestService, Depends(get_ingest_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
SbomServiceDep = Annotated[SbomService, Depends(get_sbom_service)]


# --- Upload helpers ---

from app.filename_validation import sanitize_filename  # noqa: F401 — re-export
from app.config import settings  # noqa: E402


async def read_upload_with_limit(file: "UploadFile") -> bytes:
    """Read an uploaded file with size verification.

    Raises:
        HTTPException 413 if the file exceeds max_upload_size.
    """
    from fastapi import UploadFile as _UploadFile  # noqa: F811

    # Check the declared size in the Content-Length header if available
    if hasattr(file, "size") and file.size and file.size > settings.max_upload_size:
        max_mb = settings.max_upload_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {max_mb} MB",
        )

    # Read in chunks to avoid loading a large file all at once
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
                detail=f"File too large. Maximum size: {max_mb} MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)
