import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("preco >= 0", name="preco_non_negative"),
        CheckConstraint(
            "quantidade_em_estoque >= 0", name="quantidade_non_negative"
        ),
        CheckConstraint("length(trim(nome)) >= 2", name="nome_min_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120))
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2), index=True)
    quantidade_em_estoque: Mapped[int] = mapped_column(Integer, index=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
