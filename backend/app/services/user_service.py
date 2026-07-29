"""User management service: CRUD, hashing, sessions."""
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserSession

# Durée d'une session serveur, dérivée de la même config que le max_age du
# cookie (settings.session_max_age) pour éviter deux sources divergentes :
# une expiration BDD et une expiration cookie qui pourraient différer.
SESSION_DURATION = timedelta(seconds=settings.session_max_age)


# bcrypt ignore tout au-delà de 72 octets ; on tronque explicitement pour
# conserver le comportement de passlib (troncature silencieuse) et éviter
# une ValueError des versions récentes de bcrypt sur les entrées longues.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    truncated = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(truncated, hashed.encode("ascii"))
    except ValueError:
        # Hash corrompu, vide ou dans un format inconnu : refus sans exception
        return False


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
        """Create the first admin (initial setup, no forced password change)."""
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
        """Change the password and invalidate all sessions except the current one."""
        user.password_hash = hash_password(new_password)
        user.must_change_pwd = False
        user.updated_at = datetime.now(timezone.utc)
        stmt = delete(UserSession).where(UserSession.user_id == user.id)
        if current_session_token:
            stmt = stmt.where(UserSession.token != current_session_token)
        await self.db.execute(stmt)
        await self.db.flush()

    async def reset_password(self, user: User, new_password: str) -> None:
        """Reset password by an admin (forces change at next login)."""
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
        """Create a session and clean up expired sessions."""
        token = secrets.token_urlsafe(48)
        session = UserSession(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + SESSION_DURATION,
        )
        self.db.add(session)
        # Clean up expired sessions (all users)
        await self.db.execute(
            delete(UserSession).where(UserSession.expires_at < datetime.now(timezone.utc))
        )
        await self.db.flush()
        return token

    async def get_session_user(self, token: str) -> User | None:
        """Retrieve the user associated with a valid session token."""
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
        """Delete all sessions for a user."""
        await self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))
        await self.db.flush()
