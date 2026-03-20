"""Service de gestion des utilisateurs : CRUD, hashing, sessions."""
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_DURATION = timedelta(hours=24)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_any_user(self) -> bool:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar_one() > 0

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_users(self) -> list[User]:
        result = await self.db.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())

    async def create_user(
        self, username: str, password: str, role: str,
        email: str | None = None, must_change_pwd: bool = True,
    ) -> User:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            email=email,
            must_change_pwd=must_change_pwd,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_admin(self, username: str, password: str) -> User:
        """Crée le premier admin (setup initial, pas de changement de mdp forcé)."""
        return await self.create_user(username, password, "admin", must_change_pwd=False)

    async def update_user(
        self, user: User, role: str | None = None,
        is_active: bool | None = None, email: str | None = ...,
    ) -> User:
        if role is not None and role != user.role:
            user.role = role
            await self.invalidate_sessions(user.id)
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            if not is_active:
                await self.invalidate_sessions(user.id)
        if email is not ...:
            user.email = email
        user.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return user

    async def delete_user(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()

    async def change_password(
        self, user: User, new_password: str, current_session_token: str | None = None,
    ) -> None:
        """Change le mot de passe et invalide toutes les sessions sauf la courante."""
        user.password_hash = hash_password(new_password)
        user.must_change_pwd = False
        user.updated_at = datetime.now(timezone.utc)
        stmt = delete(UserSession).where(UserSession.user_id == user.id)
        if current_session_token:
            stmt = stmt.where(UserSession.token != current_session_token)
        await self.db.execute(stmt)
        await self.db.flush()

    async def reset_password(self, user: User, new_password: str) -> None:
        """Reset le mot de passe par un admin (force le changement au prochain login)."""
        user.password_hash = hash_password(new_password)
        user.must_change_pwd = True
        user.updated_at = datetime.now(timezone.utc)
        await self.invalidate_sessions(user.id)
        await self.db.flush()

    async def count_admins(self) -> int:
        result = await self.db.execute(
            select(func.count(User.id)).where(User.role == "admin", User.is_active == True)
        )
        return result.scalar_one()

    # --- Sessions ---

    async def create_session(self, user: User) -> str:
        """Crée une session et nettoie les sessions expirées."""
        token = secrets.token_urlsafe(48)
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + SESSION_DURATION,
        )
        self.db.add(session)
        # Nettoyage des sessions expirées (tous utilisateurs)
        await self.db.execute(
            delete(UserSession).where(UserSession.expires_at < datetime.now(timezone.utc))
        )
        await self.db.flush()
        return token

    async def get_session_user(self, token: str) -> User | None:
        """Récupère l'utilisateur associé à un token de session valide."""
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.token == token,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            return None
        user = await self.get_by_id(session.user_id)
        if user and user.is_active:
            return user
        return None

    async def delete_session(self, token: str) -> None:
        await self.db.execute(delete(UserSession).where(UserSession.token == token))
        await self.db.flush()

    async def invalidate_sessions(self, user_id: UUID) -> None:
        """Supprime toutes les sessions d'un utilisateur."""
        await self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await self.db.flush()
