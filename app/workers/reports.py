import logging
import uuid
from datetime import UTC, datetime

from arq import Retry
from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.product import Product
from app.models.stock_report import StockReport


logger = logging.getLogger(__name__)


async def generate_low_stock_report(ctx: dict, report_id: str) -> dict | None:
    attempt = int(ctx.get("job_try", 1))
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                report = (
                    await session.execute(
                        select(StockReport)
                        .where(StockReport.id == uuid.UUID(report_id))
                        .with_for_update()
                    )
                ).scalar_one_or_none()

                if report is None:
                    logger.warning("Relatório não encontrado pelo worker")
                    return None
                if report.status == "completed":
                    return report.result
                if report.status == "failed":
                    return None

                products = (
                    (
                        await session.execute(
                            select(Product)
                            .where(
                                Product.quantidade_em_estoque < report.threshold
                            )
                            .order_by(
                                Product.quantidade_em_estoque.asc(),
                                Product.id.asc(),
                            )
                            .limit(1001)
                        )
                    )
                    .scalars()
                    .all()
                )
                selected_products = products[:1000]
                generated_at = datetime.now(UTC)
                result = {
                    "threshold": report.threshold,
                    "generated_at": generated_at.isoformat(),
                    "returned_count": len(selected_products),
                    "has_more": len(products) > 1000,
                    "items": [
                        {
                            "id": str(product.id),
                            "nome": product.nome,
                            "preco": format(product.preco, ".2f"),
                            "quantidade_em_estoque": product.quantidade_em_estoque,
                        }
                        for product in selected_products
                    ],
                }
                report.result = result
                report.status = "completed"
                report.completed_at = generated_at
                return result
    except Exception as exc:
        logger.exception(
            "Falha ao gerar relatório de estoque baixo",
            extra={"report_id": report_id, "attempt": attempt},
        )
        if attempt < 3:
            raise Retry(defer=1 if attempt == 1 else 3) from exc
        await mark_report_failed(report_id)
        raise


async def mark_report_failed(report_id: str) -> None:
    try:
        async with AsyncSessionFactory() as session:
            report = await session.get(StockReport, uuid.UUID(report_id))
            if report is not None and report.status == "pending":
                report.status = "failed"
                report.error_code = "REPORT_PROCESSING_FAILED"
                report.completed_at = datetime.now(UTC)
                await session.commit()
    except Exception:
        logger.exception(
            "Não foi possível persistir a falha do relatório",
            extra={"report_id": report_id},
        )
