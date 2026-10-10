import asyncio
from datetime import UTC, datetime, timedelta

from arq.connections import RedisSettings, create_pool
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.models.stock_report import StockReport


async def requeue_pending_reports(older_than_seconds: int = 120) -> int:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
    enqueued = 0

    async with AsyncSessionFactory() as session:
        reports = (
            (
                await session.execute(
                    select(StockReport)
                    .where(
                        StockReport.status == "pending",
                        StockReport.created_at < cutoff,
                    )
                    .order_by(StockReport.created_at.asc())
                )
            )
            .scalars()
            .all()
        )

    if not reports:
        return 0

    queue = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        for report in reports:
            job = await queue.enqueue_job(
                "generate_low_stock_report",
                str(report.id),
                _job_id=(
                    f"low-stock-recovery:{report.id}:"
                    f"{datetime.now(UTC).timestamp()}"
                ),
            )
            if job is not None:
                enqueued += 1
    finally:
        await queue.aclose()

    return enqueued


async def main() -> None:
    total = await requeue_pending_reports()
    print(f"Relatorios pendentes reenfileirados: {total}")


if __name__ == "__main__":
    asyncio.run(main())
