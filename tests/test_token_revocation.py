import uuid
from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import ConnectionError

from app.integrations.token_revocation import TokenRevocationStore


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.unavailable = False

    async def set(self, key: str, value: str, ex: int) -> None:
        if self.unavailable:
            raise ConnectionError("indisponivel")
        self.values[key] = value

    async def exists(self, key: str) -> int:
        if self.unavailable:
            raise ConnectionError("indisponivel")
        return 1 if key in self.values else 0


@pytest.mark.asyncio
async def test_token_revocation_store_records_and_checks_jti(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    store = TokenRevocationStore()
    monkeypatch.setattr("app.integrations.token_revocation.redis_client", fake_redis)
    jwt_id = str(uuid.uuid4())

    assert not await store.is_revoked(jwt_id)

    await store.revoke(jwt_id, datetime.now(UTC) + timedelta(minutes=5))

    assert await store.is_revoked(jwt_id)


@pytest.mark.asyncio
async def test_token_revocation_check_fails_open_when_redis_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    fake_redis.unavailable = True
    store = TokenRevocationStore()
    monkeypatch.setattr("app.integrations.token_revocation.redis_client", fake_redis)

    assert not await store.is_revoked(str(uuid.uuid4()))
