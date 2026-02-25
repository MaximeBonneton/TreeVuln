"""
Routes d'authentification par session (cookie HttpOnly signé HMAC).

Remplace le pattern VITE_ADMIN_API_KEY dans le bundle JS frontend.
Le Bearer token reste supporté pour la compatibilité API (curl, scripts).
"""

import base64
import hashlib
import hmac
import json
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.config import settings

router = APIRouter()

SESSION_COOKIE_NAME = "treevuln_session"
SESSION_MAX_AGE = 86400  # 24 heures


class LoginRequest(BaseModel):
    api_key: str


def create_session_token(admin_key: str) -> str:
    """Crée un token de session signé HMAC-SHA256."""
    payload = json.dumps({
        "iat": int(time.time()),
        "exp": int(time.time()) + SESSION_MAX_AGE,
    })
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    signature = hmac.new(
        admin_key.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def validate_session_token(token: str, admin_key: str) -> bool:
    """Valide un token de session (signature HMAC + expiration)."""
    try:
        payload_b64, signature = token.rsplit(".", 1)
        expected = hmac.new(
            admin_key.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload["exp"] > time.time()
    except Exception:
        return False


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    """Authentification par clé d'administration. Retourne un cookie de session."""
    if not settings.admin_api_key:
        if settings.debug:
            return {"authenticated": True}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY non configurée",
        )

    if not hmac.compare_digest(data.api_key, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'administration invalide",
        )

    token = create_session_token(settings.admin_api_key)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return {"authenticated": True}


@router.post("/logout")
async def logout(response: Response):
    """Déconnexion : supprime le cookie de session."""
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}


@router.get("/check")
async def check_auth(request: Request):
    """Vérifie si la session est valide (appelé par le frontend au chargement)."""
    if not settings.admin_api_key:
        return {"authenticated": bool(settings.debug)}

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return {"authenticated": False}
    return {"authenticated": validate_session_token(token, settings.admin_api_key)}
