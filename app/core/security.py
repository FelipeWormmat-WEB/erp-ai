import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings


password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class TokenClaims:
    subject: uuid.UUID
    jwt_id: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    return decode_access_token_claims(token).subject


def decode_access_token_claims(token: str) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "jti", "iat", "exp"]},
        )
        return TokenClaims(
            subject=uuid.UUID(payload["sub"]),
            jwt_id=str(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Token invalido") from exc
