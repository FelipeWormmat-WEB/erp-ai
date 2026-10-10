from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token_claims
from app.db.session import get_db_session
from app.integrations.token_revocation import token_revocation_store
from app.models.user import User
from app.repositories.users import user_repository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: DatabaseSession,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_access_token_claims(token)
    except ValueError as exc:
        raise credentials_error from exc

    if await token_revocation_store.is_revoked(claims.jwt_id):
        raise credentials_error

    user = await user_repository.get_by_id(session, claims.subject)
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
