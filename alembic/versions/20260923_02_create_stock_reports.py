"""create stock reports

Revision ID: 20260923_02
Revises: 20260922_01
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260923_02"
down_revision: str | None = "20260922_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name=op.f("ck_stock_reports_valid_status"),
        ),
        sa.CheckConstraint(
            "threshold >= 1", name=op.f("ck_stock_reports_threshold_positive")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.id"],
            name=op.f("fk_stock_reports_requested_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_reports")),
    )
    op.create_index(
        op.f("ix_stock_reports_created_at"),
        "stock_reports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stock_reports_requested_by"),
        "stock_reports",
        ["requested_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stock_reports_status"),
        "stock_reports",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_reports_status"), table_name="stock_reports")
    op.drop_index(
        op.f("ix_stock_reports_requested_by"), table_name="stock_reports"
    )
    op.drop_index(op.f("ix_stock_reports_created_at"), table_name="stock_reports")
    op.drop_table("stock_reports")
