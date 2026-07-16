from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.tree import Tree


class Asset(Base):
    """
    Asset reference for contextualization.
    Allows enriching vulnerabilities with asset metadata (criticality, tags, etc.)
    Each asset belongs to a specific tree (isolated context).
    """

    __tablename__ = "assets"
    __table_args__ = (
        # Contrainte d'unicité sur (tree_id, asset_id). L'index unique qu'elle
        # crée sert déjà les recherches par (tree_id, asset_id) : pas besoin
        # d'un index séparé idx_assets_tree_asset_id (redondant, retiré).
        UniqueConstraint("tree_id", "asset_id", name="assets_tree_asset_unique"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # FK to the owning tree
    tree_id: Mapped[int] = mapped_column(
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Unique asset identifier within the tree context
    asset_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Human-readable asset name
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Asset criticality (Low, Medium, High, Critical)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium")

    # Tags additionnels (ex: {"environment": "production", "owner": "team-a"})
    tags: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Free-form metadata for enrichment
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

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
    tree: Mapped["Tree"] = relationship("Tree", back_populates="assets")

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, tree_id={self.tree_id}, asset_id='{self.asset_id}', criticality='{self.criticality}')>"
