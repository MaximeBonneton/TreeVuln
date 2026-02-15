from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.webhook import Webhook


class Tree(Base):
    """
    Modèle représentant un arbre de décision.
    Support multi-arbres avec contextes isolés (assets propres à chaque arbre).
    """

    __tablename__ = "trees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Main Tree")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Structure de l'arbre en JSON
    # Format: { "nodes": [...], "edges": [...], "metadata": {...} }
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Multi-arbres: gestion du défaut et API
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    api_slug: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relations
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="tree",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    webhooks: Mapped[list["Webhook"]] = relationship(
        "Webhook",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Tree(id={self.id}, name='{self.name}', is_default={self.is_default})>"
