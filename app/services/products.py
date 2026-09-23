import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.products import product_repository
from app.schemas.products import (
    ProductCreate,
    ProductFilters,
    ProductPage,
    ProductPatch,
    ProductPut,
    ProductRead,
)


class ProductNotFoundError(Exception):
    pass


class ProductService:
    async def create(
        self, session: AsyncSession, payload: ProductCreate
    ) -> Product:
        product = Product(**payload.model_dump())
        await product_repository.add(session, product)
        await session.commit()
        await session.refresh(product)
        return product

    async def get(self, session: AsyncSession, product_id: uuid.UUID) -> Product:
        product = await product_repository.get_by_id(session, product_id)
        if product is None:
            raise ProductNotFoundError
        return product

    async def list(
        self, session: AsyncSession, filters: ProductFilters
    ) -> ProductPage:
        items, total = await product_repository.list(session, filters)
        total_pages = (total + filters.page_size - 1) // filters.page_size
        return ProductPage(
            items=[ProductRead.model_validate(item) for item in items],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=total_pages,
        )

    async def update(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        payload: ProductPut | ProductPatch,
    ) -> Product:
        product = await self.get(session, product_id)
        values = payload.model_dump(exclude_unset=isinstance(payload, ProductPatch))
        for field, value in values.items():
            setattr(product, field, value)
        product.data_atualizacao = datetime.now(UTC)
        await session.commit()
        await session.refresh(product)
        return product

    async def delete(self, session: AsyncSession, product_id: uuid.UUID) -> None:
        product = await self.get(session, product_id)
        await product_repository.delete(session, product)
        await session.commit()


product_service = ProductService()
