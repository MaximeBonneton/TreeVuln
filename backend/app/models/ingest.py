from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IngestEndpoint(Base):
    """
    Endpoint d'ingestion pour recevoir des vulnérabilités depuis des sources externes.
    Chaque endpoint est lié à un arbre et possède sa propre clé API et mapping de champs.
    """

    __tablename__ = "ingest_endpoints"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[int] = mapped_column(
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_evaluate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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

    def __repr__(self) -> str:
        return f"<IngestEndpoint(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class IngestLog(Base):
    """
    Log de réception d'un webhook entrant.
    """

    __tablename__ = "ingest_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    endpoint_id: Mapped[int] = mapped_column(
        ForeignKey("ingest_endpoints.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    payload_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vuln_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<IngestLog(id={self.id}, endpoint_id={self.endpoint_id}, vuln_count={self.vuln_count})>"
