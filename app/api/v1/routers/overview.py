from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.schemas.overview import OverviewResponse, OverviewScenario
from app.services.erp_overview import erp_overview_service


router = APIRouter(prefix="/erp", tags=["Visão geral do ERP"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Todas as fontes ficaram indisponíveis"
        }
    },
)
async def get_erp_overview(
    _: CurrentUser,
    scenario: Annotated[OverviewScenario, Query()] = OverviewScenario.SUCCESS,
) -> OverviewResponse | JSONResponse:
    settings = get_settings()
    if scenario is not OverviewScenario.SUCCESS and not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cenários de falha estão disponíveis apenas em DEMO_MODE",
        )

    result = await erp_overview_service.execute(scenario)
    if result.status == "unavailable":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result.model_dump(mode="json"),
        )
    return result
