from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Webhook(Base):
    """
    Webhook sortant configuré pour un arbre.
    Envoie des notifications HTTP POST lors d'événements (évaluations).
    """

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("idx_webhooks_tree_active", "tree_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tree_id: Mapped[int] = mapped_column(
        ForeignKey("trees.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    events: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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
        return f"<Webhook(id={self.id}, name='{self.name}', url='{self.url}')>"


class WebhookLog(Base):
    """
    Log d'envoi d'un webhook.
    """

    __tablename__ = "webhook_logs"
    __table_args__ = (
        Index("idx_webhook_logs_created", "webhook_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    webhook_id: Mapped[int] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    response_body: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WebhookLog(id={self.id}, webhook_id={self.webhook_id}, success={self.success})>"
