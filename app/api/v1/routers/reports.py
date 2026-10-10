import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.reports import (
    LowStockReportRequest,
    ReportAccepted,
    StockReportRead,
)
from app.services.reports import (
    ReportQueueUnavailableError,
    StockReportNotFoundError,
    stock_report_service,
)


router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.post(
    "/low-stock",
    response_model=ReportAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Relatório persistido, mas fila indisponível"
        }
    },
)
async def request_low_stock_report(
    payload: LowStockReportRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ReportAccepted | JSONResponse:
    try:
        report = await stock_report_service.request(
            session,
            current_user.id,
            payload.threshold,
        )
    except ReportQueueUnavailableError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "REPORT_QUEUE_UNAVAILABLE",
                    "message": "Relatório salvo, mas a fila está indisponível",
                    "report_id": str(exc.report_id),
                }
            },
        )

    return ReportAccepted(
        report_id=report.id,
        status_url=f"/api/v1/reports/{report.id}",
    )


@router.get("/{report_id}", response_model=StockReportRead)
async def get_report(
    report_id: uuid.UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> StockReportRead:
    try:
        report = await stock_report_service.get(
            session, report_id, current_user.id
        )
    except StockReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relatório não encontrado",
        ) from exc
    return StockReportRead.model_validate(report)
