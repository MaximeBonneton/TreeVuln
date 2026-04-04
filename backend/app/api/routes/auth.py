"""Authentication routes: setup, login, logout, check, change-password."""
import time
from collections import defaultdict

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

# --- Login brute force protection ---
# In-memory tracker: {username: (fail_count, last_fail_timestamp)}
_login_failures: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 300  # 5 minutes


def _check_login_rate(username: str) -> None:
    """Raise 429 if the account is temporarily locked after too many failures."""
    fail_count, last_fail = _login_failures[username]
    if fail_count >= _MAX_FAILURES:
        elapsed = time.monotonic() - last_fail
        if elapsed < _LOCKOUT_SECONDS:
            remaining = int(_LOCKOUT_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Try again in {remaining}s.",
            )
        # Lockout expired, reset
        _login_failures[username] = (0, 0.0)


def _record_login_failure(username: str) -> None:
    fail_count, _ = _login_failures[username]
    _login_failures[username] = (fail_count + 1, time.monotonic())


def _clear_login_failures(username: str) -> None:
    _login_failures.pop(username, None)


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
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    _check_login_rate(data.username)

    service = UserService(db)
    user = await service.get_by_username(data.username)

    # Always run bcrypt to prevent timing-based user enumeration
    if not user or not user.is_active:
        verify_password(data.password, _DUMMY_HASH)
        _record_login_failure(data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        _record_login_failure(data.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_login_failures(data.username)
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
