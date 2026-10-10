import uuid

import pytest
from fastapi import HTTPException

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.models.user import User


class FakeUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user

    async def get_by_id(self, session: object, user_id: uuid.UUID) -> User | None:
        return self.user


class FakeRevocationStore:
    def __init__(self, revoked: bool = False) -> None:
        self.revoked = revoked

    async def is_revoked(self, jwt_id: str) -> bool:
        return self.revoked


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    token, _ = create_access_token(user_id)
    inactive_user = User(
        id=user_id,
        username="inactive",
        password_hash="hash",
        is_active=False,
    )
    monkeypatch.setattr(
        "app.api.dependencies.user_repository",
        FakeUserRepository(inactive_user),
    )
    monkeypatch.setattr(
        "app.api.dependencies.token_revocation_store",
        FakeRevocationStore(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, object())  # type: ignore[arg-type]

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_unknown_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token, _ = create_access_token(uuid.uuid4())
    monkeypatch.setattr(
        "app.api.dependencies.user_repository",
        FakeUserRepository(None),
    )
    monkeypatch.setattr(
        "app.api.dependencies.token_revocation_store",
        FakeRevocationStore(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, object())  # type: ignore[arg-type]

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    token, _ = create_access_token(user_id)
    active_user = User(
        id=user_id,
        username="active",
        password_hash="hash",
        is_active=True,
    )
    monkeypatch.setattr(
        "app.api.dependencies.user_repository",
        FakeUserRepository(active_user),
    )
    monkeypatch.setattr(
        "app.api.dependencies.token_revocation_store",
        FakeRevocationStore(revoked=True),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token, object())  # type: ignore[arg-type]

    assert exc_info.value.status_code == 401
