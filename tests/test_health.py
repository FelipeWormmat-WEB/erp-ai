from fastapi.testclient import TestClient
from uuid import UUID

from app.main import app


client = TestClient(app)


def test_live_health_returns_ok() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["x-request-id"])


def test_valid_request_id_is_preserved() -> None:
    request_id = "4cce533d-4b9f-4aa1-b0fd-2e62c03e3815"

    response = client.get("/health/live", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id


def test_invalid_request_id_is_replaced() -> None:
    response = client.get(
        "/health/live", headers={"X-Request-ID": "not-a-safe-request-id"}
    )

    assert response.status_code == 200
    generated = response.headers["x-request-id"]
    UUID(generated)
    assert generated != "not-a-safe-request-id"
