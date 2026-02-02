from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TreeVersion(Base):
    """
    Historique des versions d'un arbre.
    Chaque sauvegarde crée une nouvelle version avec un snapshot complet.
    """

    __tablename__ = "tree_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Snapshot complet de la structure au moment de la sauvegarde
    structure_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Commentaire optionnel pour documenter les changements
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamp de création de la version
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TreeVersion(id={self.id}, tree_id={self.tree_id}, v={self.version_number})>"
