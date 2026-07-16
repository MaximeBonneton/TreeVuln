from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.webhook import Webhook


class Tree(Base):
    """
    Model representing a decision tree.
    Multi-tree support with isolated contexts (assets specific to each tree).
    """

    __tablename__ = "trees"
    __table_args__ = (
        # Index unique partiel : garantit qu'un seul arbre peut avoir is_default=True
        # au niveau BDD (protège contre les races entre deux set_default_tree concurrents).
        Index(
            "idx_trees_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Main Tree")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Tree structure in JSON
    # Format: { "nodes": [...], "edges": [...], "metadata": {...} }
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Multi-tree: default and API management
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
