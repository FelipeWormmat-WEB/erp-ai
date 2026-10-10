import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.product import Product
from app.schemas.products import ProductRead
from app.services.products import product_service


class BypassCache:
    async def get(self, product_id: uuid.UUID) -> tuple[ProductRead | None, str]:
        return None, "BYPASS"

    async def set(self, product: ProductRead) -> None:
        raise AssertionError("BYPASS nao deve preencher cache")


class FakeProductRepository:
    def __init__(self, product: Product) -> None:
        self.product = product

    async def get_by_id(self, session: object, product_id: uuid.UUID) -> Product | None:
        return self.product


@pytest.mark.asyncio
async def test_product_detail_uses_database_when_cache_bypasses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_id = uuid.uuid4()
    now = datetime.now(UTC)
    product = Product(
        id=product_id,
        nome="Produto sem cache",
        preco=Decimal("19.90"),
        quantidade_em_estoque=3,
        data_criacao=now,
        data_atualizacao=now,
    )
    monkeypatch.setattr("app.services.products.product_cache", BypassCache())
    monkeypatch.setattr(
        "app.services.products.product_repository",
        FakeProductRepository(product),
    )

    product_read, cache_status = await product_service.get_detail(
        object(), product_id  # type: ignore[arg-type]
    )

    assert cache_status == "BYPASS"
    assert product_read.id == product_id
    assert product_read.nome == "Produto sem cache"
