import asyncio
import logging
from datetime import UTC, datetime

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.integrations.redis import redis_client


logger = logging.getLogger(__name__)


class TokenRevocationStore:
    @staticmethod
    def key(jwt_id: str) -> str:
        return f"erp:revoked-token:v1:{jwt_id}"

    async def revoke(self, jwt_id: str, expires_at: datetime) -> None:
        settings = get_settings()
        ttl_seconds = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
        try:
            async with asyncio.timeout(settings.redis_timeout_seconds):
                await redis_client.set(self.key(jwt_id), "1", ex=ttl_seconds)
        except (RedisError, TimeoutError):
            logger.warning("Falha ao registrar revogacao de token no Redis")
            raise

    async def is_revoked(self, jwt_id: str) -> bool:
        settings = get_settings()
        try:
            async with asyncio.timeout(settings.redis_timeout_seconds):
                return await redis_client.exists(self.key(jwt_id)) == 1
        except (RedisError, TimeoutError):
            logger.warning("Redis indisponivel durante checagem de revogacao")
            return False


token_revocation_store = TokenRevocationStore()
