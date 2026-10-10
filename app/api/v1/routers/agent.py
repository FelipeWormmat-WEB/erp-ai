import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.services.agent import agent_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agente"])


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    payload: AgentQueryRequest,
    session: DatabaseSession,
    _: CurrentUser,
) -> AgentQueryResponse:
    try:
        return await agent_service.query(session, payload)
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.exception("Falha ao consultar produtos pelo agente")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consulta temporariamente indisponível",
        ) from exc

