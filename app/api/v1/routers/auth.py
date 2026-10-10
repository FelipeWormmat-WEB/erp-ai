from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import CurrentUser, DatabaseSession, oauth2_scheme
from app.core.security import (
    create_access_token,
    decode_access_token_claims,
    verify_password,
)
from app.integrations.token_revocation import token_revocation_store
from app.repositories.users import user_repository
from app.schemas.auth import TokenResponse
from app.services.rate_limit import login_rate_limiter


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/token", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DatabaseSession,
    request: Request,
) -> TokenResponse:
    client_host = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_host}:{form.username.casefold()}"
    if not login_rate_limiter.hit(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
        )

    user = await user_repository.get_by_username(session, form.username)
    if (
        user is None
        or not user.is_active
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_rate_limiter.reset(rate_limit_key)
    access_token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    _: CurrentUser,
) -> None:
    claims = decode_access_token_claims(token)
    await token_revocation_store.revoke(claims.jwt_id, claims.expires_at)
