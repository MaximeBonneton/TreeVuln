"""SBOM ingéré par asset (Phase 2 CRA) : un document par asset, remplacé
à chaque import, et ses composants normalisés pour le matching purl/nom."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sbom(Base):
    __tablename__ = "sboms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Un SBOM max par asset ; supprimé avec l'asset
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # cyclonedx | spdx
    spec_version: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    component_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    components: Mapped[list["SbomComponent"]] = relationship(
        back_populates="sbom", cascade="all, delete-orphan"
    )


class SbomComponent(Base):
    __tablename__ = "sbom_components"
    __table_args__ = (
        Index("idx_sbom_components_purl", "sbom_id", "purl"),
        Index("idx_sbom_components_name", "sbom_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sbom_id: Mapped[int] = mapped_column(
        ForeignKey("sboms.id", ondelete="CASCADE"), nullable=False
    )
    # purl tel quel (non décomposé) ; certains composants n'en ont pas
    purl: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    component_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    sbom: Mapped["Sbom"] = relationship(back_populates="components")
