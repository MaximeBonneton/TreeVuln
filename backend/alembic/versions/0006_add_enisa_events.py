"""add enisa_events table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-22
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enisa_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tree_id", sa.Integer(),
            sa.ForeignKey("trees.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("cve_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="candidate"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrective_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("early_warning_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_report_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("early_warning_submitted_by", sa.String(100), nullable=True),
        sa.Column("notification_submitted_by", sa.String(100), nullable=True),
        sa.Column("final_report_submitted_by", sa.String(100), nullable=True),
        sa.Column("affected_assets", JSONB(), nullable=False, server_default="[]"),
        sa.Column("evaluation_context", JSONB(), nullable=False, server_default="{}"),
        sa.Column("drafts", JSONB(), nullable=False, server_default="{}"),
        sa.Column("reminders_sent", JSONB(), nullable=False, server_default="{}"),
        sa.Column("confirmed_by", sa.String(100), nullable=True),
        sa.Column("dismissed_by", sa.String(100), nullable=True),
        sa.Column("dismiss_reason", sa.Text(), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("redetection_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tree_id", "cve_id", name="uq_enisa_events_tree_cve"),
    )
    op.create_index(
        "idx_enisa_events_tree_status", "enisa_events", ["tree_id", "status"]
    )


def downgrade() -> None:
    op.drop_table("enisa_events")
