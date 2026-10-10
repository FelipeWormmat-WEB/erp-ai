import os

import httpx
import pytest


BASE_URL = os.getenv("INTEGRATION_BASE_URL")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        BASE_URL is None,
        reason="defina INTEGRATION_BASE_URL para executar contra a API real",
    ),
]


async def authenticate(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/token",
        data={
            "username": os.environ["SEED_USERNAME"],
            "password": os.environ["SEED_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.parametrize(
    ("scenario", "expected_code", "expected_status", "finance_status", "attempts"),
    [
        ("success", 200, "complete", "ok", 1),
        ("retry_success", 200, "complete", "ok", 2),
        ("partial_timeout", 200, "partial", "timeout", 2),
        ("all_failed", 503, "unavailable", "timeout", 2),
    ],
)
async def test_overview_scenarios(
    scenario: str,
    expected_code: int,
    expected_status: str,
    finance_status: str,
    attempts: int,
) -> None:
    assert BASE_URL is not None
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as client:
        headers = await authenticate(client)
        response = await client.get(
            "/api/v1/erp/overview",
            headers=headers,
            params={"scenario": scenario},
        )

    assert response.status_code == expected_code, response.text
    body = response.json()
    assert body["mode"] == "mock"
    assert body["status"] == expected_status
    assert body["sources"]["financeiro"]["status"] == finance_status
    assert body["sources"]["financeiro"]["attempts"] == attempts


async def test_overview_requires_authentication() -> None:
    assert BASE_URL is not None
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5) as client:
        response = await client.get("/api/v1/erp/overview")

    assert response.status_code == 401
