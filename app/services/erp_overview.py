import asyncio
import logging

from app.integrations.erp_sources import (
    DEFAULT_ERP_SOURCES,
    ERPSource,
    TransientSourceError,
)
from app.schemas.overview import (
    OverviewResponse,
    OverviewScenario,
    OverviewSources,
    SourceResult,
)


logger = logging.getLogger(__name__)


class ERPOverviewService:
    def __init__(
        self,
        sources: tuple[ERPSource, ...] = DEFAULT_ERP_SOURCES,
        timeout_seconds: float = 0.6,
        retry_delay_seconds: float = 0.1,
    ) -> None:
        self.sources = sources
        self.timeout_seconds = timeout_seconds
        self.retry_delay_seconds = retry_delay_seconds

    async def execute(self, scenario: OverviewScenario) -> OverviewResponse:
        results = await asyncio.gather(
            *(self._fetch_with_retry(source, scenario) for source in self.sources)
        )
        results_by_name = dict(zip((source.name for source in self.sources), results))

        successful_sources = sum(
            result.status == "ok" for result in results_by_name.values()
        )
        if successful_sources == len(results_by_name):
            overview_status = "complete"
        elif successful_sources > 0:
            overview_status = "partial"
        else:
            overview_status = "unavailable"

        return OverviewResponse(
            status=overview_status,
            sources=OverviewSources(
                estoque=results_by_name["estoque"],
                financeiro=results_by_name["financeiro"],
                clientes=results_by_name["clientes"],
            ),
        )

    async def _fetch_with_retry(
        self, source: ERPSource, scenario: OverviewScenario
    ) -> SourceResult:
        last_status = "error"
        last_error_code = "SOURCE_UNAVAILABLE"

        for attempt in range(1, 3):
            try:
                data = await asyncio.wait_for(
                    source.fetch(scenario, attempt),
                    timeout=self.timeout_seconds,
                )
                return SourceResult(status="ok", attempts=attempt, data=data)
            except TimeoutError:
                last_status = "timeout"
                last_error_code = "SOURCE_TIMEOUT"
            except TransientSourceError:
                last_status = "error"
                last_error_code = "SOURCE_UNAVAILABLE"
            except Exception:
                logger.exception(
                    "Falha inesperada ao consultar fonte do ERP",
                    extra={"source": source.name, "attempt": attempt},
                )
                return SourceResult(
                    status="error",
                    attempts=attempt,
                    error_code="SOURCE_UNAVAILABLE",
                )

            if attempt == 1:
                await asyncio.sleep(self.retry_delay_seconds)

        return SourceResult(
            status=last_status,
            attempts=2,
            error_code=last_error_code,
        )


erp_overview_service = ERPOverviewService()
