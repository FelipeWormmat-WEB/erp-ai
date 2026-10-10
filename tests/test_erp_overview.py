import asyncio
from dataclasses import dataclass

import pytest

from app.schemas.overview import OverviewScenario
from app.services.erp_overview import ERPOverviewService


@dataclass
class CoordinatedSource:
    name: str
    started: set[str]
    all_started: asyncio.Event

    async def fetch(
        self, scenario: OverviewScenario, attempt: int
    ) -> dict[str, int]:
        self.started.add(self.name)
        if len(self.started) == 3:
            self.all_started.set()
        await asyncio.wait_for(self.all_started.wait(), timeout=0.2)
        return {"value": 1}


@dataclass
class ImmediateSource:
    name: str

    async def fetch(
        self, scenario: OverviewScenario, attempt: int
    ) -> dict[str, int]:
        return {"value": 1}


@dataclass
class SlowSource:
    name: str

    async def fetch(
        self, scenario: OverviewScenario, attempt: int
    ) -> dict[str, int]:
        await asyncio.sleep(0.05)
        return {"value": 1}


@pytest.mark.asyncio
async def test_sources_start_before_any_source_finishes() -> None:
    started: set[str] = set()
    all_started = asyncio.Event()
    sources = tuple(
        CoordinatedSource(name, started, all_started)
        for name in ("estoque", "financeiro", "clientes")
    )
    service = ERPOverviewService(sources=sources, timeout_seconds=0.5)

    result = await service.execute(OverviewScenario.SUCCESS)

    assert started == {"estoque", "financeiro", "clientes"}
    assert result.status == "complete"


@pytest.mark.asyncio
async def test_transient_failure_is_recovered_by_single_retry() -> None:
    service = ERPOverviewService(retry_delay_seconds=0)

    result = await service.execute(OverviewScenario.RETRY_SUCCESS)

    assert result.status == "complete"
    assert result.sources.financeiro.status == "ok"
    assert result.sources.financeiro.attempts == 2


@pytest.mark.asyncio
async def test_timeout_keeps_healthy_source_results() -> None:
    sources = (
        ImmediateSource("estoque"),
        SlowSource("financeiro"),
        ImmediateSource("clientes"),
    )
    service = ERPOverviewService(
        sources=sources,
        timeout_seconds=0.01,
        retry_delay_seconds=0,
    )

    result = await service.execute(OverviewScenario.SUCCESS)

    assert result.status == "partial"
    assert result.sources.estoque.status == "ok"
    assert result.sources.clientes.status == "ok"
    assert result.sources.financeiro.status == "timeout"
    assert result.sources.financeiro.attempts == 2
    assert result.sources.financeiro.error_code == "SOURCE_TIMEOUT"
