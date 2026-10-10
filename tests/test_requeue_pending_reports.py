import pytest

from app.scripts import requeue_pending_reports as script


class EmptyResult:
    def scalars(self) -> "EmptyResult":
        return self

    def all(self) -> list[object]:
        return []


class FakeSession:
    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def execute(self, statement: object) -> EmptyResult:
        return EmptyResult()


class FakeSessionFactory:
    def __call__(self) -> FakeSession:
        return FakeSession()


@pytest.mark.asyncio
async def test_requeue_pending_reports_returns_zero_without_old_pending_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_if_queue_is_created(*args: object, **kwargs: object) -> None:
        raise AssertionError("fila nao deve ser aberta sem relatorios pendentes")

    monkeypatch.setattr(script, "AsyncSessionFactory", FakeSessionFactory())
    monkeypatch.setattr(script, "create_pool", fail_if_queue_is_created)

    total = await script.requeue_pending_reports()

    assert total == 0
