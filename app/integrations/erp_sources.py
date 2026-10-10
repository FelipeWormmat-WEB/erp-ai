import asyncio
from dataclasses import dataclass
from typing import Protocol

from app.schemas.overview import OverviewScenario


class TransientSourceError(Exception):
    """Falha transitória que pode ser repetida com segurança."""


class ERPSource(Protocol):
    name: str

    async def fetch(
        self, scenario: OverviewScenario, attempt: int
    ) -> dict[str, int]: ...


@dataclass(frozen=True)
class MockERPSource:
    name: str
    delay_seconds: float
    payload: dict[str, int]

    async def fetch(
        self, scenario: OverviewScenario, attempt: int
    ) -> dict[str, int]:
        if scenario is OverviewScenario.ALL_FAILED:
            await asyncio.sleep(1)

        if (
            self.name == "financeiro"
            and scenario is OverviewScenario.PARTIAL_TIMEOUT
        ):
            await asyncio.sleep(1)

        if (
            self.name == "financeiro"
            and scenario is OverviewScenario.RETRY_SUCCESS
            and attempt == 1
        ):
            await asyncio.sleep(0.05)
            raise TransientSourceError("falha transitória simulada")

        await asyncio.sleep(self.delay_seconds)
        return self.payload.copy()


DEFAULT_ERP_SOURCES: tuple[ERPSource, ...] = (
    MockERPSource(
        name="estoque",
        delay_seconds=0.15,
        payload={"produtos": 12, "itens_baixo_estoque": 3},
    ),
    MockERPSource(
        name="financeiro",
        delay_seconds=0.25,
        payload={"titulos_pendentes": 4},
    ),
    MockERPSource(
        name="clientes",
        delay_seconds=0.35,
        payload={"clientes_ativos": 8},
    ),
)
