import asyncio

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings


_queue_pool: ArqRedis | None = None
_queue_pool_lock = asyncio.Lock()


async def get_queue_pool() -> ArqRedis:
    global _queue_pool
    if _queue_pool is None:
        async with _queue_pool_lock:
            if _queue_pool is None:
                settings = get_settings()
                _queue_pool = await create_pool(
                    RedisSettings.from_dsn(settings.redis_url)
                )
    return _queue_pool


async def close_queue_pool() -> None:
    global _queue_pool
    if _queue_pool is not None:
        await _queue_pool.aclose()
        _queue_pool = None
