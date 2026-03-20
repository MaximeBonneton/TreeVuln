"""Routes de gestion des utilisateurs (admin uniquement)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireAuth, require_role
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate, ResetPasswordRequest
from app.services.user_service import UserService

router = APIRouter()


def _to_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id), username=user.username, email=user.email,
        role=user.role, is_active=user.is_active, must_change_pwd=user.must_change_pwd,
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(_=require_role("admin"), db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    users = await service.list_users()
    return [_to_response(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreate, _=require_role("admin"), db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    existing = await service.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = await service.create_user(data.username, data.password, data.role, data.email)
    await db.commit()
    return _to_response(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, data: UserUpdate,
    current_user: RequireAuth, _=require_role("admin"),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Protections
    if user.id == current_user.id:
        if data.role is not None and data.role != current_user.role:
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        if data.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    if data.role is not None and data.role != "admin" and user.role == "admin":
        if await service.count_admins() <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")

    if data.is_active is False and user.role == "admin":
        if await service.count_admins() <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last admin")

    await service.update_user(
        user,
        role=data.role,
        is_active=data.is_active,
        email=data.email if data.email is not None else ...,
    )
    await db.commit()
    return _to_response(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID, current_user: RequireAuth,
    _=require_role("admin"), db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.role == "admin" and await service.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    await service.delete_user(user)
    await db.commit()


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: UUID, data: ResetPasswordRequest,
    _=require_role("admin"), db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await service.reset_password(user, data.new_password)
    await db.commit()
    return {"ok": True}
