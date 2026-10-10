import uuid
from datetime import UTC, datetime

import pytest
from redis.exceptions import ConnectionError

from app.integrations.product_cache import ProductCache
from app.schemas.products import ProductRead


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.unavailable = False

    async def get(self, key: str) -> str | None:
        if self.unavailable:
            raise ConnectionError("indisponível")
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        if self.unavailable:
            raise ConnectionError("indisponível")
        self.values[key] = value

    async def delete(self, key: str) -> None:
        if self.unavailable:
            raise ConnectionError("indisponível")
        self.values.pop(key, None)


def sample_product() -> ProductRead:
    now = datetime.now(UTC)
    return ProductRead(
        id=uuid.uuid4(),
        nome="Produto em cache",
        preco="12.50",
        quantidade_em_estoque=4,
        data_criacao=now,
        data_atualizacao=now,
    )


@pytest.mark.asyncio
async def test_cache_miss_hit_and_invalidation() -> None:
    fake_redis = FakeRedis()
    cache = ProductCache(client=fake_redis)  # type: ignore[arg-type]
    product = sample_product()

    missing, status = await cache.get(product.id)
    assert missing is None
    assert status == "MISS"

    await cache.set(product)
    cached, status = await cache.get(product.id)
    assert cached == product
    assert status == "HIT"

    await cache.invalidate(product.id)
    missing_again, status = await cache.get(product.id)
    assert missing_again is None
    assert status == "MISS"


@pytest.mark.asyncio
async def test_cache_failure_uses_bypass() -> None:
    fake_redis = FakeRedis()
    fake_redis.unavailable = True
    cache = ProductCache(client=fake_redis)  # type: ignore[arg-type]

    cached, status = await cache.get(uuid.uuid4())

    assert cached is None
    assert status == "BYPASS"
