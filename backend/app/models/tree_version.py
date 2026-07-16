from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TreeVersion(Base):
    """
    Tree version history.
    Each save creates a new version with a complete snapshot.
    """

    __tablename__ = "tree_versions"
    __table_args__ = (
        # Unicité du numéro de version au sein d'un arbre : évite deux versions
        # portant le même numéro en cas d'écritures concurrentes (version_number
        # est calculé par max+1, non atomique).
        Index(
            "uq_tree_versions_tree_version",
            "tree_id",
            "version_number",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Complete structure snapshot at the time of save
    structure_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Optional comment to document changes
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Version creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TreeVersion(id={self.id}, tree_id={self.tree_id}, v={self.version_number})>"
