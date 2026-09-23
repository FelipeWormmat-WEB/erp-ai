from typing import Literal

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.db.session import get_db_session


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]


app = FastAPI(
    title="ERP Produtos e Estoque com IA",
    description="API desenvolvida para a prova prática de backend.",
    version="0.1.0",
)
app.include_router(api_router)


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
    summary="Verifica se a API consegue acessar o PostgreSQL",
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
            content={"status": "unavailable"},
        )
    return ReadinessResponse(status="ready")
