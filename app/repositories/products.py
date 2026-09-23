import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.products import ProductFilters


class ProductRepository:
    async def get_by_id(
        self, session: AsyncSession, product_id: uuid.UUID
    ) -> Product | None:
        return await session.get(Product, product_id)

    async def add(self, session: AsyncSession, product: Product) -> None:
        session.add(product)
        await session.flush()

    async def delete(self, session: AsyncSession, product: Product) -> None:
        await session.delete(product)

    def _apply_filters(
        self, statement: Select, filters: ProductFilters
    ) -> Select:
        if filters.nome is not None:
            statement = statement.where(
                Product.nome.icontains(filters.nome, autoescape=True)
            )
        if filters.preco_min is not None:
            statement = statement.where(Product.preco >= filters.preco_min)
        if filters.preco_max is not None:
            statement = statement.where(Product.preco <= filters.preco_max)
        if filters.estoque_abaixo_de is not None:
            statement = statement.where(
                Product.quantidade_em_estoque < filters.estoque_abaixo_de
            )
        if filters.somente_sem_estoque:
            statement = statement.where(Product.quantidade_em_estoque == 0)
        return statement

    async def list(
        self, session: AsyncSession, filters: ProductFilters
    ) -> tuple[Sequence[Product], int]:
        count_statement = self._apply_filters(
            select(func.count()).select_from(Product), filters
        )
        total = (await session.execute(count_statement)).scalar_one()

        statement = self._apply_filters(select(Product), filters)
        statement = (
            statement.order_by(Product.data_criacao.desc(), Product.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        items = (await session.execute(statement)).scalars().all()
        return items, total


product_repository = ProductRepository()
