"""Authentication routes: setup, login, logout, check, change-password."""
import time

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.user import (
    AuthStatus, ChangePasswordRequest, LoginRequest, SetupRequest, UserInfo,
)
from app.services.user_service import UserService, hash_password, verify_password
from app.api.deps import RequireAuth

# Pre-computed dummy hash to normalize timing when user is not found
_DUMMY_HASH = hash_password("dummy-timing-normalization")

SESSION_MAX_AGE = settings.session_max_age

router = APIRouter()

# --- Login brute force protection (S-14) ---
# Suivi en mémoire par (ip, username) : {(ip, username): (fail_count, last_fail)}.
# Limites connues et assumées (documentées par l'audit S-14) :
# - état par worker (uvicorn --workers N => N compteurs indépendants : le
#   verrouillage effectif est jusqu'à N fois plus lâche) ; un stockage en
#   base serait nécessaire pour un verrou global strict ;
# - derrière le nginx du docker-compose, request.client.host est l'adresse
#   du proxy : la clé devient de fait (proxy, username), équivalente au
#   verrou par username d'origine. X-Forwarded-For n'est volontairement
#   PAS utilisé : une valeur forgée par requête contournerait tout le
#   verrouillage en cas d'exposition directe du backend.
_login_failures: dict[tuple[str, str], tuple[int, float]] = {}
_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 300  # 5 minutes
# Borne dure du nombre d'entrées suivies : combinée à la purge des entrées
# expirées, elle garantit une mémoire bornée même sous un flot de
# usernames/IP aléatoires.
_MAX_TRACKED_KEYS = 10_000


def _client_ip(request: Request) -> str:
    """Adresse IP du client TCP (le proxy nginx en déploiement standard)."""
    return request.client.host if request.client else "unknown"


def _purge_expired(now: float) -> None:
    """Supprime les entrées dont le dernier échec est plus vieux que le lockout."""
    expired = [
        key
        for key, (_, last_fail) in _login_failures.items()
        if now - last_fail >= _LOCKOUT_SECONDS
    ]
    for key in expired:
        del _login_failures[key]


def _check_login_rate(ip: str, username: str) -> None:
    """Raise 429 if (ip, username) is temporarily locked after too many failures.

    Consultation pure : ne crée jamais d'entrée (l'ancien defaultdict
    créait une entrée par username testé, mémoire non bornée).
    """
    entry = _login_failures.get((ip, username))
    if entry is None:
        return
    fail_count, last_fail = entry
    if fail_count >= _MAX_FAILURES:
        elapsed = time.monotonic() - last_fail
        if elapsed < _LOCKOUT_SECONDS:
            remaining = int(_LOCKOUT_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Try again in {remaining}s.",
            )
        # Lockout expiré : l'entrée ne sert plus à rien
        del _login_failures[(ip, username)]


def _record_login_failure(ip: str, username: str) -> None:
    now = time.monotonic()
    _purge_expired(now)
    key = (ip, username)
    if key not in _login_failures and len(_login_failures) >= _MAX_TRACKED_KEYS:
        # Borne dure atteinte avec des entrées toutes actives : éjecte la
        # plus ancienne (la plus proche de l'expiration).
        oldest = min(_login_failures, key=lambda k: _login_failures[k][1])
        del _login_failures[oldest]
    fail_count = _login_failures.get(key, (0, 0.0))[0]
    _login_failures[key] = (fail_count + 1, now)


def _clear_login_failures(ip: str, username: str) -> None:
    _login_failures.pop((ip, username), None)


# --- Helpers ---


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _user_info(user) -> UserInfo:
    return UserInfo(id=str(user.id), username=user.username, role=user.role)


# --- Routes ---


@router.get("/check")
async def check_auth(request: Request, db: AsyncSession = Depends(get_db)) -> AuthStatus:
    service = UserService(db)

    if not await service.has_any_user():
        return AuthStatus(status="setup_required")

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return AuthStatus(status="unauthenticated")

    user = await service.get_session_user(token)
    if not user:
        return AuthStatus(status="unauthenticated")

    if user.must_change_pwd:
        return AuthStatus(status="must_change_password")

    return AuthStatus(status="authenticated", user=_user_info(user))


@router.post("/setup")
async def setup(data: SetupRequest, response: Response, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    if await service.has_any_user():
        raise HTTPException(status_code=403, detail="Setup already completed")

    user = await service.create_admin(data.username, data.password)
    token = await service.create_session(user)
    await db.commit()
    _set_session_cookie(response, token)
    return AuthStatus(status="authenticated", user=_user_info(user))


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    ip = _client_ip(request)
    _check_login_rate(ip, data.username)

    service = UserService(db)
    user = await service.get_by_username(data.username)

    # Always run bcrypt to prevent timing-based user enumeration
    if not user or not user.is_active:
        verify_password(data.password, _DUMMY_HASH)
        _record_login_failure(ip, data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        _record_login_failure(ip, data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_login_failures(ip, data.username)
    token = await service.create_session(user)
    await db.commit()
    _set_session_cookie(response, token)

    if user.must_change_pwd:
        return AuthStatus(status="must_change_password")

    return AuthStatus(status="authenticated", user=_user_info(user))


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        service = UserService(db)
        await service.delete_session(token)
        await db.commit()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"ok": True}


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    user: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    service = UserService(db)
    session_token = request.state.session_token
    await service.change_password(user, data.new_password, current_session_token=session_token)
    await db.commit()
    return {"ok": True}
