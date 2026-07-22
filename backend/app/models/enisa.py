"""Événements de notification ENISA (Phase 3 CRA) : un événement par
(arbre, CVE), cycle candidate -> confirmed -> closed (ou dismissed).
Les échéances 24h/72h/14j ne sont jamais stockées — calculées par
app.engine.enisa depuis confirmed_at / corrective_available_at."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnisaEvent(Base):
    __tablename__ = "enisa_events"
    __table_args__ = (
        UniqueConstraint("tree_id", "cve_id", name="uq_enisa_events_tree_cve"),
        Index("idx_enisa_events_tree_status", "tree_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[int] = mapped_column(
        ForeignKey("trees.id", ondelete="CASCADE"), nullable=False
    )
    cve_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # candidate | confirmed | dismissed | closed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")

    # Chrono — detected_at immuable, confirmed_at = prise de connaissance
    # (ancre 24h/72h), corrective_available_at = ancre du 14j
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    corrective_available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Jalons soumis manuellement (plateforme ENISA externe)
    early_warning_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notification_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_report_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    early_warning_submitted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notification_submitted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_report_submitted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Contexte snapshoté et brouillons
    affected_assets: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evaluation_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    drafts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Seuils de rappel déjà notifiés, ex. {"early_warning": ["T-12h"]}
    reminders_sent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Traçabilité
    confirmed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dismissed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dismiss_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    redetection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
