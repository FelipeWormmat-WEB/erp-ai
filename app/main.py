import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import request_logger
from app.db.session import engine, get_db_session
from app.integrations.queue import close_queue_pool
from app.integrations.redis import close_redis_client, redis_client


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    postgres: Literal["ok"]
    redis: Literal["ok", "unavailable"]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_queue_pool()
    await close_redis_client()
    await engine.dispose()


app = FastAPI(
    title="ERP Produtos e Estoque com IA",
    description="API desenvolvida para a prova prática de backend.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router)


def resolve_request_id(value: str | None) -> str:
    if value is not None:
        try:
            return str(uuid.UUID(value))
        except ValueError:
            pass
    return str(uuid.uuid4())


@app.middleware("http")
async def request_context(request: Request, call_next) -> Response:
    request_id = resolve_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    started_at = time.perf_counter()
    response: Response
    error: Exception | None = None

    try:
        response = await call_next(request)
    except Exception as exc:
        error = exc
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno", "request_id": request_id},
        )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    log_context = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }
    if error is None:
        request_logger.info("request_completed", extra=log_context)
    else:
        request_logger.error(
            "request_failed", extra=log_context, exc_info=error
        )
    return response


@app.get(
    "/health/live",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Verifica se o processo da API está respondendo",
)
async def live_health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Verifica PostgreSQL e informa o estado do Redis",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Banco indisponível"}},
)
async def ready_health(
    session: AsyncSession = Depends(get_db_session),
) -> ReadinessResponse | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "postgres": "unavailable"},
        )

    settings = get_settings()
    redis_status = "ok"
    try:
        async with asyncio.timeout(settings.redis_timeout_seconds):
            await redis_client.ping()
    except (RedisError, TimeoutError):
        redis_status = "unavailable"

    return ReadinessResponse(
        status="ready",
        postgres="ok",
        redis=redis_status,
    )
