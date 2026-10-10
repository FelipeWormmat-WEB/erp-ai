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


async def test_authenticated_product_crud_and_filters() -> None:
    assert BASE_URL is not None
    username = os.environ["SEED_USERNAME"]
    password = os.environ["SEED_PASSWORD"]
    product_id: str | None = None

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        invalid_login = await client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": "senha-incorreta"},
        )
        assert invalid_login.status_code == 401

        login = await client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        unauthorized = await client.get("/api/v1/products")
        assert unauthorized.status_code == 401

        invalid_product = await client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "nome": "12345",
                "preco": "-0.01",
                "quantidade_em_estoque": -1,
            },
        )
        assert invalid_product.status_code == 422

        try:
            created = await client.post(
                "/api/v1/products",
                headers=headers,
                json={
                    "nome": f"Produto integração {uuid.uuid4().hex[:8]}",
                    "preco": "79.90",
                    "quantidade_em_estoque": 9,
                },
            )
            assert created.status_code == 201, created.text
            assert created.headers["location"].startswith("/api/v1/products/")
            product = created.json()
            product_id = product["id"]
            assert product["preco"] == "79.90"

            fetched = await client.get(
                f"/api/v1/products/{product_id}", headers=headers
            )
            assert fetched.status_code == 200
            assert fetched.headers["x-cache"] == "MISS"

            cached = await client.get(
                f"/api/v1/products/{product_id}", headers=headers
            )
            assert cached.status_code == 200
            assert cached.headers["x-cache"] == "HIT"

            filtered = await client.get(
                "/api/v1/products",
                headers=headers,
                params={
                    "nome": "produto INTEGRAÇÃO",
                    "estoque_abaixo_de": 10,
                    "preco_max": "80.00",
                },
            )
            assert filtered.status_code == 200, filtered.text
            assert any(item["id"] == product_id for item in filtered.json()["items"])

            empty_patch = await client.patch(
                f"/api/v1/products/{product_id}", headers=headers, json={}
            )
            assert empty_patch.status_code == 422

            patched = await client.patch(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={"quantidade_em_estoque": 12},
            )
            assert patched.status_code == 200, patched.text
            assert patched.json()["quantidade_em_estoque"] == 12

            after_patch = await client.get(
                f"/api/v1/products/{product_id}", headers=headers
            )
            assert after_patch.status_code == 200
            assert after_patch.headers["x-cache"] == "MISS"
            assert after_patch.json()["quantidade_em_estoque"] == 12

            replaced = await client.put(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={
                    "nome": "Produto substituído",
                    "preco": "81.00",
                    "quantidade_em_estoque": 4,
                },
            )
            assert replaced.status_code == 200, replaced.text
            assert replaced.json()["nome"] == "Produto substituído"

            deleted = await client.delete(
                f"/api/v1/products/{product_id}", headers=headers
            )
            assert deleted.status_code == 204, deleted.text
            product_id = None

            missing = await client.get(
                f"/api/v1/products/{product['id']}", headers=headers
            )
            assert missing.status_code == 404
        finally:
            if product_id is not None:
                await client.delete(f"/api/v1/products/{product_id}", headers=headers)
