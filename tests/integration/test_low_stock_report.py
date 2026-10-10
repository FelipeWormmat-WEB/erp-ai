import asyncio
import os
import uuid

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


async def test_low_stock_report_runs_in_worker_and_persists_result() -> None:
    assert BASE_URL is not None
    product_id: str | None = None

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        login = await client.post(
            "/api/v1/auth/token",
            data={
                "username": os.environ["SEED_USERNAME"],
                "password": os.environ["SEED_PASSWORD"],
            },
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        try:
            created = await client.post(
                "/api/v1/products",
                headers=headers,
                json={
                    "nome": f"Produto relatório {uuid.uuid4().hex[:8]}",
                    "preco": "15.00",
                    "quantidade_em_estoque": 2,
                },
            )
            assert created.status_code == 201, created.text
            product_id = created.json()["id"]

            requested = await client.post(
                "/api/v1/reports/low-stock",
                headers=headers,
                json={"threshold": 10},
            )
            assert requested.status_code == 202, requested.text
            report_id = requested.json()["report_id"]

            report = None
            for _ in range(20):
                response = await client.get(
                    f"/api/v1/reports/{report_id}", headers=headers
                )
                assert response.status_code == 200, response.text
                report = response.json()
                if report["status"] != "pending":
                    break
                await asyncio.sleep(0.25)

            assert report is not None
            assert report["status"] == "completed"
            assert report["result"]["threshold"] == 10
            assert any(
                item["id"] == product_id for item in report["result"]["items"]
            )
        finally:
            if product_id is not None:
                await client.delete(f"/api/v1/products/{product_id}", headers=headers)
