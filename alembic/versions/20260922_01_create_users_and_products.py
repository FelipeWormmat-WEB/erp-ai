"""create users and products

Revision ID: 20260922_01
Revises:
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260922_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("preco", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantidade_em_estoque", sa.Integer(), nullable=False),
        sa.Column(
            "data_criacao",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "data_atualizacao",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(nome)) >= 2", name=op.f("ck_products_nome_min_length")
        ),
        sa.CheckConstraint(
            "preco >= 0", name=op.f("ck_products_preco_non_negative")
        ),
        sa.CheckConstraint(
            "quantidade_em_estoque >= 0",
            name=op.f("ck_products_quantidade_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_preco"), "products", ["preco"], unique=False)
    op.create_index(
        op.f("ix_products_quantidade_em_estoque"),
        "products",
        ["quantidade_em_estoque"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_products_quantidade_em_estoque"), table_name="products")
    op.drop_index(op.f("ix_products_preco"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
