from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.tree import Tree


class Asset(Base):
    """
    Référentiel des assets pour la contextualisation.
    Permet d'enrichir les vulnérabilités avec des métadonnées d'asset (criticité, tags, etc.)
    Chaque asset appartient à un arbre spécifique (contexte isolé).
    """

    __tablename__ = "assets"
    __table_args__ = (
        # Contrainte unique sur (tree_id, asset_id)
        UniqueConstraint("tree_id", "asset_id", name="assets_tree_asset_unique"),
        # Index pour la recherche par arbre et asset_id
        Index("idx_assets_tree_asset_id", "tree_id", "asset_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # FK vers l'arbre propriétaire
    tree_id: Mapped[int] = mapped_column(
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Identifiant unique de l'asset dans le contexte de l'arbre
    asset_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Nom lisible de l'asset
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Criticité de l'asset (Low, Medium, High, Critical)
    criticality: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium")

    # Tags additionnels (ex: {"environment": "production", "owner": "team-a"})
    tags: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Métadonnées libres pour enrichissement
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
