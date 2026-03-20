"""Routes d'authentification : setup, login, logout, check, change-password."""
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.user import (
    AuthStatus, ChangePasswordRequest, LoginRequest, SetupRequest, UserInfo,
)
from app.services.user_service import UserService, verify_password
from app.api.deps import RequireAuth

SESSION_COOKIE_NAME = "treevuln_session"
SESSION_MAX_AGE = 86400  # 24h

router = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=SESSION_MAX_AGE,
        path="/",
    )


def _user_info(user) -> UserInfo:
    return UserInfo(id=str(user.id), username=user.username, role=user.role)


@router.get("/check")
async def check_auth(request: Request, db: AsyncSession = Depends(get_db)) -> AuthStatus:
    service = UserService(db)

    if not await service.has_any_user():
        return AuthStatus(status="setup_required")

    token = request.cookies.get(SESSION_COOKIE_NAME)
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
    service = UserService(db)
    user = await service.get_by_username(data.username)

    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = await service.create_session(user)
    await db.commit()
    _set_session_cookie(response, token)

    if user.must_change_pwd:
        return AuthStatus(status="must_change_password")

    return AuthStatus(status="authenticated", user=_user_info(user))


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        service = UserService(db)
        await service.delete_session(token)
        await db.commit()
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
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
