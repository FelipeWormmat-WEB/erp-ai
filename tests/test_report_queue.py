import uuid

import pytest

from app.services.reports import ReportQueueUnavailableError, stock_report_service


class FakeReportRepository:
    async def add(self, session: object, report: object) -> None:
        report.id = uuid.uuid4()


class FakeSession:
    async def commit(self) -> None:
        pass

    async def refresh(self, report: object) -> None:
        pass


class QueueThatDoesNotAcceptJob:
    async def enqueue_job(self, *args: object, **kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_report_request_preserves_report_id_when_enqueue_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_queue_pool() -> QueueThatDoesNotAcceptJob:
        return QueueThatDoesNotAcceptJob()

    monkeypatch.setattr(
        "app.services.reports.stock_report_repository",
        FakeReportRepository(),
    )
    monkeypatch.setattr("app.services.reports.get_queue_pool", fake_get_queue_pool)

    with pytest.raises(ReportQueueUnavailableError) as exc_info:
        await stock_report_service.request(
            FakeSession(),  # type: ignore[arg-type]
            uuid.uuid4(),
            10,
        )

    assert isinstance(exc_info.value.report_id, uuid.UUID)
