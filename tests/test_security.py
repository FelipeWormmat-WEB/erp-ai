import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_is_hashed_and_verified() -> None:
    password = "senha-segura"
    encoded = hash_password(password)

    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("senha-incorreta", encoded)


def test_access_token_round_trip_and_tampering() -> None:
    user_id = uuid.uuid4()
    token, expires_in = create_access_token(user_id)

    assert expires_in == 1800
    assert decode_access_token(token) == user_id

    with pytest.raises(ValueError, match="Token inválido"):
        decode_access_token(f"{token}invalid")


def test_expired_access_token_is_rejected() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="Token inválido"):
        decode_access_token(token)
