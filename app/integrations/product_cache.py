import asyncio
import logging
import uuid
from typing import Literal

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.integrations.redis import redis_client
from app.schemas.products import ProductRead


logger = logging.getLogger(__name__)
CacheStatus = Literal["HIT", "MISS", "BYPASS"]


class ProductCache:
    def __init__(self, client: Redis = redis_client) -> None:
        settings = get_settings()
        self.client = client
        self.ttl_seconds = settings.cache_ttl_seconds
        self.timeout_seconds = settings.redis_timeout_seconds

    @staticmethod
    def key(product_id: uuid.UUID) -> str:
        return f"erp:product:v1:{product_id}"

    async def get(
        self, product_id: uuid.UUID
    ) -> tuple[ProductRead | None, CacheStatus]:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                cached = await self.client.get(self.key(product_id))
        except (RedisError, TimeoutError):
            logger.warning("Cache Redis indisponível durante leitura de produto")
            return None, "BYPASS"

        if cached is None:
            return None, "MISS"

        try:
            return ProductRead.model_validate_json(cached), "HIT"
        except ValidationError:
            logger.warning("Entrada inválida encontrada no cache de produto")
            await self.invalidate(product_id)
            return None, "MISS"

    async def set(self, product: ProductRead) -> None:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await self.client.set(
                    self.key(product.id),
                    product.model_dump_json(),
                    ex=self.ttl_seconds,
                )
        except (RedisError, TimeoutError):
            logger.warning("Falha ao preencher cache de produto")

    async def invalidate(self, product_id: uuid.UUID) -> None:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                await self.client.delete(self.key(product_id))
        except (RedisError, TimeoutError):
            logger.warning("Falha ao invalidar cache de produto")


product_cache = ProductCache()
