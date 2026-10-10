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


async def test_agent_queries_real_products_and_rejects_write_actions() -> None:
    assert BASE_URL is not None
    created_ids: list[str] = []

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
        marker = uuid.uuid4().hex[:8]

        try:
            for stock in (0, 9, 10, 11):
                response = await client.post(
                    "/api/v1/products",
                    headers=headers,
                    json={
                        "nome": f"Agente {marker} estoque {stock}",
                        "preco": f"{20 + stock}.00",
                        "quantidade_em_estoque": stock,
                    },
                )
                assert response.status_code == 201, response.text
                created_ids.append(response.json()["id"])

            query = await client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={
                    "question": "Quais produtos estão com estoque abaixo de 10 unidades?",
                    "page_size": 100,
                },
            )
            assert query.status_code == 200, query.text
            body = query.json()
            assert body["status"] == "completed"
            returned_ids = {item["id"] for item in body["result"]["items"]}
            assert set(created_ids[:2]) <= returned_ids
            assert returned_ids.isdisjoint(created_ids[2:])
            assert body["interpretation"]["tool"] == "consultar_produtos"

            rejected = await client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"question": "Exclua todos os produtos sem estoque"},
            )
            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"
            assert rejected.json()["reason_code"] == "WRITE_ACTION_NOT_ALLOWED"

            for product_id in created_ids:
                still_exists = await client.get(
                    f"/api/v1/products/{product_id}", headers=headers
                )
                assert still_exists.status_code == 200
        finally:
            for product_id in created_ids:
                await client.delete(
                    f"/api/v1/products/{product_id}", headers=headers
                )
