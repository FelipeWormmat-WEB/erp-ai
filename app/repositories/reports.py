import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_report import StockReport


class StockReportRepository:
    async def add(self, session: AsyncSession, report: StockReport) -> None:
        session.add(report)
        await session.flush()

    async def get_for_user(
        self,
        session: AsyncSession,
        report_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockReport | None:
        result = await session.execute(
            select(StockReport).where(
                StockReport.id == report_id,
                StockReport.requested_by == user_id,
            )
        )
        return result.scalar_one_or_none()


stock_report_repository = StockReportRepository()
