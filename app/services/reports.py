import asyncio
import uuid

from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.queue import get_queue_pool
from app.models.stock_report import StockReport
from app.repositories.reports import stock_report_repository


class StockReportNotFoundError(Exception):
    pass


class ReportQueueUnavailableError(Exception):
    def __init__(self, report_id: uuid.UUID) -> None:
        self.report_id = report_id
        super().__init__("Fila de relatórios indisponível")


class StockReportService:
    async def request(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        threshold: int,
    ) -> StockReport:
        report = StockReport(requested_by=user_id, threshold=threshold)
        await stock_report_repository.add(session, report)
        await session.commit()
        await session.refresh(report)

        try:
            async with asyncio.timeout(1):
                queue = await get_queue_pool()
                job = await queue.enqueue_job(
                    "generate_low_stock_report",
                    str(report.id),
                    _job_id=f"low-stock:{report.id}",
                )
            if job is None:
                raise ReportQueueUnavailableError(report.id)
        except (RedisError, OSError, TimeoutError) as exc:
            raise ReportQueueUnavailableError(report.id) from exc

        return report

    async def get(
        self,
        session: AsyncSession,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockReport:
        report = await stock_report_repository.get_for_user(
            session, report_id, user_id
        )
        if report is None:
            raise StockReportNotFoundError
        return report


stock_report_service = StockReportService()
